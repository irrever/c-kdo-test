#!/usr/bin/env python3
"""Pronostics et arrivées de toutes les courses d'une journée, pour l'onglet Recherche de la page du jour.

Une course a son pronostic si elle n'était pas encore partie quand la journée a été calculée (la veille, au
téléchargement du quinté de demain). Le quinté du jour reprend le pronostic de son journal, pour rester identique
à sa page. Une course déjà partie n'a que son arrivée : un pronostic recalculé après le départ n'en serait pas un.
Les données vont dans quinte/journal/AAAA-MM-JJ-journee.json ; les arrivées y sont mises à jour au fil de la journée.

Usage : python3 quinte/journee.py AAAA-MM-JJ
"""
import datetime as dt
import json
import os
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import equidia as eq  # noqa: E402
import analyse_equidia as ae  # noqa: E402

JOURNAL = os.path.join(HERE, "journal")
PARIS = ZoneInfo("Europe/Paris")
SIMULATIONS = 20_000  # le quinté garde ses 200 000 simulations, dans son journal
REUNIONS_MAX = 12


def fichier(date):
    return os.path.join(JOURNAL, "%s-journee.json" % date)


def _partants(course):
    return [p for p in course.get("partants", []) if p.get("statut_part") != "NP"]


def _arrivee(course):
    """Numéros des cinq premiers à l'arrivée, ou [] si la course n'est pas terminée."""
    if course.get("type_statut_course_id") != "finished":
        return []
    arr = []
    for p in course.get("partants", []):
        rang = p.get("num_place_arrivee")
        if p.get("statut_part") == "DP" and rang and str(rang).strip().isdigit():
            arr.append((int(str(rang).strip()), p["num_partant"]))
    return [n for _, n in sorted(arr)][:5]


def _entree(course, r, c):
    """Ce qui est affiché pour une course : ses données et son arrivée. Le pronostic s'y ajoute."""
    reunion = course.get("reunion") or {}
    return {
        "r": r,
        "c": c,
        "hippodrome": (reunion.get("hippodrome") or {}).get("name") or "",
        "libelle": course.get("libcourt_prix_course") or "",
        "heure": course.get("heure_depart_course") or "",
        "distance": course.get("distance"),
        "discipline": course.get("discipline") or "",
        "statut": course.get("type_statut_course_id") or "",
        "partants": len(_partants(course)),
        "noms": {str(p["num_partant"]): (p.get("cheval") or {}).get("nom_cheval", "") for p in _partants(course)},
        "arrivee": _arrivee(course),
        "ordre": [],
        "top": [],
    }


def _pronostic_calcule(course):
    """Pronostic d'une course pas encore partie, à partir de ses données actuelles."""
    lignes = ae.analyser(course)
    prob = ae.probabilites(ae.simuler(lignes, n=SIMULATIONS), lignes)
    return {
        "ordre": [l["numero"] for l in lignes[:5]],
        "top": [{"numero": l["numero"], "nom": l["nom"], "note": round(100 * l["score"]),
                 "p_victoire": round(prob["victoire"][l["numero"]], 4),
                 "p_top3": round(prob["top3"][l["numero"]], 4)} for l in lignes[:8]],
    }


def _pronostic_journal(date, r, c):
    """Pronostic du quinté du jour, tel que son journal le garde (avec les cotes s'il est final)."""
    import suivi
    chemin = suivi._fichier_pronostic(date)
    if not os.path.exists(chemin):
        return None
    with open(chemin, encoding="utf-8") as f:
        d = json.load(f)
    if d.get("course") != "R%dC%d" % (r, c) or "chevaux" not in d:
        return None
    par_numero = {x["numero"]: x for x in d["chevaux"]}
    rang = list(d["ordre_predit"]) + [x["numero"] for x in d["chevaux"] if x["numero"] not in d["ordre_predit"]]
    return {
        "ordre": list(d["ordre_predit"]),
        "top": [{"numero": n, "nom": par_numero[n]["nom"], "note": round(100 * par_numero[n]["score"]),
                 "p_victoire": round(par_numero[n]["p_victoire"], 4),
                 "p_top3": round(par_numero[n]["p_top3"], 4)} for n in rang[:8]],
    }


def analyser_journee(date):
    """Toutes les courses de la journée (réunions R1 à R12, telles que les liste Equidia)."""
    resultat = []
    for r in range(1, REUNIONS_MAX + 1):
        try:
            statuts = eq.statuts_reunion(date, r)
        except Exception as e:
            print("réunion R%d ignorée : %s" % (r, e))
            continue
        if not statuts:
            break
        for st in statuts:
            c = st.get("num_course_pmu")
            if not c:
                continue
            try:
                course = eq.course(date, r, c, fresh=True)
            except Exception as e:
                print("course ignorée R%dC%d : %s" % (r, c, e))
                continue
            if not course:
                continue
            try:
                entree = _entree(course, r, c)
                pronostic = _pronostic_journal(date, r, c)
                if pronostic is None and entree["statut"] == "before":
                    pronostic = _pronostic_calcule(course)
                if pronostic:
                    entree.update(pronostic)
            except Exception as e:  # une course défaillante ne bloque pas la journée
                print("course ignorée R%dC%d : %s" % (r, c, e))
                continue
            resultat.append(entree)
    resultat.sort(key=lambda x: (x["r"], x["c"]))
    return resultat


def _depart(date, heure):
    return dt.datetime.fromisoformat("%sT%s" % (date, heure)).replace(tzinfo=PARIS)


def rafraichir_arrivees(date, maintenant):
    """Met à jour les courses parties mais pas encore terminées. Renvoie True si quelque chose a changé."""
    chemin = fichier(date)
    if not os.path.exists(chemin):
        return False
    with open(chemin, encoding="utf-8") as f:
        donnees = json.load(f)
    change = False
    for x in donnees["courses"]:
        if x["statut"] == "finished" or not x["heure"]:
            continue
        if maintenant < _depart(date, x["heure"]):
            continue
        try:
            course = eq.course(date, x["r"], x["c"], fresh=True)
        except Exception as e:
            print("arrivée non mise à jour R%dC%d : %s" % (x["r"], x["c"], e))
            continue
        if not course:
            continue
        statut = course.get("type_statut_course_id") or ""
        arr = _arrivee(course)
        if statut != x["statut"] or arr != x["arrivee"]:
            x["statut"] = statut
            x["arrivee"] = arr
            change = True
    if change:
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=1)
    return change


def charger(date, calculer=False):
    """Courses de la journée : lues dans le fichier, ou calculées si calculer est vrai, sinon None."""
    chemin = fichier(date)
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)["courses"]
    if not calculer:
        return None
    courses = analyser_journee(date)
    os.makedirs(JOURNAL, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump({"date": date, "calcule_le": dt.datetime.now().isoformat(timespec="seconds"),
                   "courses": courses}, f, ensure_ascii=False, indent=1)
    return courses


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    cs = charger(sys.argv[1], calculer=True)
    print("courses de la journée :", len(cs), "· avec pronostic :", sum(1 for x in cs if x["ordre"]))
