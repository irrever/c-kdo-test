#!/usr/bin/env python3
"""Pronostics et arrivées de toutes les courses d'une journée, pour l'onglet Recherche de la page du jour.

Une course a son pronostic si elle n'était pas encore partie quand la journée a été calculée (la veille, au
téléchargement du quinté de demain). Le quinté du jour reprend le pronostic de son journal, pour rester identique
à sa page. Une course déjà partie n'a que son arrivée : un pronostic recalculé après le départ n'en serait pas un.
Les données vont dans quinte/journal/AAAA-MM-JJ-journee.json ; les arrivées y sont mises à jour au fil de la journée.

Chaque course pas encore partie est aussi versée au registre des pronostics (quinte/registre.py), avec le détail
de chaque cheval. C'est ce registre qui sert aux analyses (quinte/analyse_registre.py).

Usage :
    python3 quinte/journee.py AAAA-MM-JJ             # calcule la journée, et verse les courses au registre
    python3 quinte/journee.py AAAA-MM-JJ --registre  # verse seulement les courses pas encore parties au registre
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
import registre  # noqa: E402

JOURNAL = os.path.join(HERE, "journal")
PARIS = ZoneInfo("Europe/Paris")
SIMULATIONS = 20_000  # le quinté garde ses 200 000 simulations, dans son journal
REUNIONS_MAX = 12


def fichier(date):
    return os.path.join(JOURNAL, "%s-journee.json" % date)


def _partants(course):
    return [p for p in course.get("partants", []) if p.get("statut_part") != "NP"]


def _places(course):
    """Place de chaque partant classé : numéro -> place."""
    out = {}
    for p in course.get("partants", []):
        rang = p.get("num_place_arrivee")
        if p.get("statut_part") == "DP" and rang and str(rang).strip().isdigit():
            out[p["num_partant"]] = int(str(rang).strip())
    return out


def _arrivee(course):
    """Numéros des cinq premiers à l'arrivée, ou [] si la course n'est pas terminée."""
    if course.get("type_statut_course_id") != "finished":
        return []
    places = _places(course)
    return sorted(places, key=lambda n: places[n])[:5]


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


def _calcul(course):
    """Analyse d'une course pas encore partie : notes par cheval, et probabilités (20 000 simulations)."""
    lignes = ae.analyser(course)
    probs = ae.probabilites(ae.simuler(lignes, n=SIMULATIONS), lignes)
    return lignes, probs


def _pronostic_de(lignes, probs):
    """Pronostic affiché : les cinq premiers, et les huit premiers avec leurs probabilités."""
    return {
        "ordre": [l["numero"] for l in lignes[:5]],
        "top": [{"numero": l["numero"], "nom": l["nom"], "note": round(100 * l["score"]),
                 "p_victoire": round(probs["victoire"][l["numero"]], 4),
                 "p_top3": round(probs["top3"][l["numero"]], 4)} for l in lignes[:8]],
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
    """Toutes les courses de la journée (réunions R1 à R12, telles que les liste Equidia), et les lignes
    du registre pour les courses pas encore parties."""
    resultat, lignes_registre = [], []
    calcule_le = dt.datetime.now(PARIS).isoformat(timespec="seconds")
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
                if entree["statut"] == "before":
                    lignes, probs = _calcul(course)
                    lignes_registre += registre.lignes_de_course(
                        date, r, c, course, lignes, probs, ae.cotes_de(course), calcule_le)
                    pronostic = _pronostic_journal(date, r, c) or _pronostic_de(lignes, probs)
                else:
                    pronostic = _pronostic_journal(date, r, c)  # quinté déjà parti : son pronostic figé
                if pronostic:
                    entree.update(pronostic)
            except Exception as e:  # une course défaillante ne bloque pas la journée
                print("course ignorée R%dC%d : %s" % (r, c, e))
                continue
            resultat.append(entree)
    resultat.sort(key=lambda x: (x["r"], x["c"]))
    return resultat, lignes_registre


def _depart(date, heure):
    return dt.datetime.fromisoformat("%sT%s" % (date, heure)).replace(tzinfo=PARIS)


def rafraichir_arrivees(date, maintenant):
    """Met à jour les courses parties mais pas encore terminées, dans la journée et dans le registre.
    Renvoie True si la journée a changé."""
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
            if statut == "finished":
                registre.mettre_a_jour_arrivees(date, x["r"], x["c"], _places(course))
    if change:
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=1)
    return change


def charger(date, calculer=False):
    """Courses de la journée : lues dans le fichier, ou calculées si calculer est vrai (sinon None)."""
    chemin = fichier(date)
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)["courses"]
    if not calculer:
        return None
    courses, lignes = analyser_journee(date)
    os.makedirs(JOURNAL, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump({"date": date, "calcule_le": dt.datetime.now().isoformat(timespec="seconds"),
                   "courses": courses}, f, ensure_ascii=False, indent=1)
    print("registre : %d lignes ajoutées" % registre.ajouter(lignes))
    return courses


def enregistrer_registre(date):
    """Verse au registre les courses de la journée pas encore parties, sans toucher au fichier de la journée."""
    _, lignes = analyser_journee(date)
    return registre.ajouter(lignes)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or len(args) > 2 or (len(args) == 2 and args[1] != "--registre"):
        raise SystemExit(__doc__)
    date = args[0]
    if len(args) == 2:
        print("registre : %d lignes ajoutées pour %s" % (enregistrer_registre(date), date))
    else:
        cs = charger(date, calculer=True)
        print("courses de la journée :", len(cs), "· avec pronostic :", sum(1 for x in cs if x["ordre"]))
