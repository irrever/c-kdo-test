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
    python3 quinte/journee.py AAAA-MM-JJ --completer # ajoute à la journée les réunions publiées depuis son calcul
    python3 quinte/journee.py AAAA-MM-JJ --cotes     # relève les cotes des courses sans pronostic qui partent dans l'heure
    python3 quinte/journee.py AAAA-MM-JJ --rattraper # relit les courses terminées : cotes de départ manquantes, rapports
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


def _liste_cotes(course, cotes):
    """Cotes relevées, dans l'ordre des numéros : [{numero, nom, cote}]."""
    noms = {p["num_partant"]: (p.get("cheval") or {}).get("nom_cheval", "") for p in _partants(course)}
    return [{"numero": n, "nom": noms.get(n, ""), "cote": cotes[n]} for n in sorted(cotes) if cotes[n]]


def _sans_pronostic(course, cotes, releve):
    """Course où le modèle ne peut rien départager : pas d'ordre ni de pourcentages. La page affiche à la place
    les conditions de la course et les cotes du marché, à titre d'information."""
    return {"sans_donnees": True, "ordre": [], "top": [],
            "conditions": course.get("conditions_txt_course") or "",
            "cotes": _liste_cotes(course, cotes or {}), "cotes_releve": releve}


def analyser_journee(date, ignorer=frozenset()):
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
        if not statuts:  # réunion pas encore publiée : on passe à la suivante, une réunion vide ne stoppe pas tout
            continue
        for st in statuts:
            c = st.get("num_course_pmu")
            if not c or (r, c) in ignorer:
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
                    cotes = ae.cotes_de(course)
                    sans = ae.sans_donnees(lignes)
                    lignes_registre += registre.lignes_de_course(
                        date, r, c, course, lignes, probs, cotes, calcule_le, sans_donnees=sans)
                    if sans:  # le modèle ne départage rien : pas de pronostic, les cotes à titre d'information
                        entree.update(_sans_pronostic(course, cotes, calcule_le))
                        pronostic = None
                    else:
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


def capturer_cotes_proches(date, maintenant, fenetre_minutes=60):
    """Relève les cotes des courses qui partent dans l'heure, et les inscrit au registre. Ce sont les dernières
    cotes avant le départ : chaque passage remplace les précédentes. Renvoie le nombre de courses relevées."""
    chemin = fichier(date)
    if not os.path.exists(chemin):
        return 0
    with open(chemin, encoding="utf-8") as f:
        donnees = json.load(f)
    releves = 0
    for x in donnees["courses"]:
        if x["statut"] != "before" or not x["heure"]:
            continue
        minutes = (_depart(date, x["heure"]) - maintenant).total_seconds() / 60
        if not 0 < minutes <= fenetre_minutes:
            continue
        try:
            course = eq.course(date, x["r"], x["c"], fresh=True)
        except Exception as e:
            print("cotes non relevées R%dC%d : %s" % (x["r"], x["c"], e))
            continue
        cotes = ae.cotes_de(course) if course else None
        if cotes and registre.capturer_cotes(date, x["r"], x["c"], cotes, maintenant.strftime("%Y-%m-%dT%H:%M")):
            releves += 1
    return releves


def rafraichir_cotes_sans_donnees(date, maintenant, fenetre_minutes=60):
    """Relève de nouveau les cotes des courses sans pronostic qui partent dans l'heure : la page affiche le dernier
    relevé avant le départ. Renvoie le nombre de courses mises à jour."""
    chemin = fichier(date)
    if not os.path.exists(chemin):
        return 0
    with open(chemin, encoding="utf-8") as f:
        donnees = json.load(f)
    heure = maintenant.strftime("%Y-%m-%dT%H:%M")
    maj = 0
    for x in donnees["courses"]:
        if not x.get("sans_donnees") or x["statut"] != "before" or not x["heure"]:
            continue
        minutes = (_depart(date, x["heure"]) - maintenant).total_seconds() / 60
        if not 0 < minutes <= fenetre_minutes:
            continue
        try:
            course = eq.course(date, x["r"], x["c"], fresh=True)
        except Exception as e:
            print("cotes non relevées R%dC%d : %s" % (x["r"], x["c"], e))
            continue
        cotes = ae.cotes_de(course) if course else None
        if cotes:
            x["cotes"] = _liste_cotes(course, cotes)
            x["cotes_releve"] = heure
            maj += 1
    if maj:
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=1)
    return maj


def _pronostic_avec_cotes(course, cotes):
    """Pronostic d'une course avec les cotes du moment : le modèle mélangé au marché, la part des cotes dépendant de
    la discipline (au trot, les cotes seules). Renvoie (pronostic, part des cotes)."""
    poids = ae.poids_cotes_pour(course.get("discipline"))
    lignes = ae.melanger_cotes(ae.analyser(course), cotes, poids)
    probs = ae.probabilites(ae.simuler(lignes, n=SIMULATIONS), lignes)
    return _pronostic_de(lignes, probs), poids


def figer_finaux(date, maintenant, fenetre_minutes=60, ignorer=frozenset()):
    """Pronostic final des courses de la journée : une heure avant le départ, dès que les cotes de tous les partants
    sont connues, le pronostic est recalculé avec elles, puis il est figé. Le quinté (ignorer) garde son propre
    pronostic final. Renvoie le nombre de courses figées."""
    chemin = fichier(date)
    if not os.path.exists(chemin):
        return 0
    with open(chemin, encoding="utf-8") as f:
        donnees = json.load(f)
    figees = 0
    for x in donnees["courses"]:
        if x.get("final") or x.get("sans_donnees") or not x.get("ordre") or x["statut"] != "before" or not x["heure"]:
            continue
        if (x["r"], x["c"]) in ignorer:
            continue
        minutes = (_depart(date, x["heure"]) - maintenant).total_seconds() / 60
        if not 0 < minutes <= fenetre_minutes:
            continue
        try:
            course = eq.course(date, x["r"], x["c"], fresh=True)
        except Exception as e:
            print("pronostic final non figé R%dC%d : %s" % (x["r"], x["c"], e))
            continue
        if not course or course.get("type_statut_course_id") != "before":
            continue
        cotes = ae.cotes_de(course)
        if not cotes:  # une cote manque : le pronostic reste celui du modèle
            continue
        pronostic, poids = _pronostic_avec_cotes(course, cotes)
        x.update(pronostic)
        x["final"] = {"fige_le": maintenant.strftime("%Y-%m-%dT%H:%M"), "part_cotes": poids}
        figees += 1
    if figees:
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=1)
    return figees


def _avec_pronostic_du_quinte(date, courses):
    """Le quinté reprend son pronostic de journal : le pronostic final dès qu'il est figé, comme sur sa page."""
    import suivi
    chemin = suivi._fichier_pronostic(date)
    if not os.path.exists(chemin):
        return courses
    with open(chemin, encoding="utf-8") as f:
        d = json.load(f)
    r, c = [int(x) for x in d["course"].replace("R", "").split("C")]
    pronostic = _pronostic_journal(date, r, c)
    for x in courses:
        if (x["r"], x["c"]) == (r, c) and pronostic:
            x.update(pronostic)
            if "final" in d:
                x["final"] = {"fige_le": d["final"]["fige_le"][:16], "part_cotes": d["final"].get("part_cotes", 0.7)}
    return courses


def charger(date, calculer=False):
    """Courses de la journée : lues dans le fichier, ou calculées si calculer est vrai (sinon None)."""
    chemin = fichier(date)
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as f:
            return _avec_pronostic_du_quinte(date, json.load(f)["courses"])
    if not calculer:
        return None
    courses, lignes = analyser_journee(date)
    os.makedirs(JOURNAL, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump({"date": date, "calcule_le": dt.datetime.now().isoformat(timespec="seconds"),
                   "courses": courses}, f, ensure_ascii=False, indent=1)
    print("registre : %d lignes ajoutées" % registre.ajouter(lignes))
    return courses


def completer(date):
    """Ajoute à la journée les courses des réunions publiées depuis son calcul. Les courses déjà présentes
    ne bougent pas : leur pronostic reste celui du calcul, même si elles sont parties depuis."""
    chemin = fichier(date)
    if not os.path.exists(chemin):
        raise SystemExit("Journée pas encore calculée pour %s." % date)
    with open(chemin, encoding="utf-8") as f:
        donnees = json.load(f)
    connues = {(x["r"], x["c"]) for x in donnees["courses"]}
    nouvelles, lignes = analyser_journee(date, ignorer=connues)
    donnees["courses"] = sorted(donnees["courses"] + nouvelles, key=lambda x: (x["r"], x["c"]))
    donnees["complete_le"] = dt.datetime.now().isoformat(timespec="seconds")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)
    print("registre : %d lignes ajoutées" % registre.ajouter(lignes))
    return len(nouvelles)


def enregistrer_registre(date):
    """Verse au registre les courses de la journée pas encore parties, sans toucher au fichier de la journée."""
    _, lignes = analyser_journee(date)
    return registre.ajouter(lignes)


def rattraper(date):
    """Courses terminées de la journée : cotes de départ relues après la course quand elles manquent, et rapports
    officiels du simple gagnant et du simple placé. Renvoie le nombre de courses relues."""
    courses = sorted({(int(x["r"]), int(x["c"])) for x in registre.lire() if x["date"] == date and x["arrivee"]})
    relues = 0
    for r, c in courses:
        try:
            course = eq.course(date, r, c, fresh=True)  # relit la page, qui contient aussi les rapports
        except Exception as e:
            print("R%dC%d non relue : %s" % (r, c, e))
            continue
        if not course or course.get("type_statut_course_id") != "finished":
            continue
        page = eq.get_html("%s/courses/%s/R%d/C%d" % (eq.BASE, date, r, c))  # la page vient d'être relue : cache
        cotes = ae.cotes_de(course)
        if cotes:
            registre.completer_cotes(date, r, c, cotes)
        registre.inscrire_rapports(date, r, c, eq.rapports_simples(page))
        relues += 1
    return relues


if __name__ == "__main__":
    args = sys.argv[1:]
    options = ("--registre", "--completer", "--cotes", "--rattraper")
    if not args or len(args) > 2 or (len(args) == 2 and args[1] not in options):
        raise SystemExit(__doc__)
    date = args[0]
    if len(args) == 2 and args[1] == "--registre":
        print("registre : %d lignes ajoutées pour %s" % (enregistrer_registre(date), date))
    elif len(args) == 2 and args[1] == "--cotes":
        print("cotes relevées pour %d course(s) sans pronostic de %s" % (
            rafraichir_cotes_sans_donnees(date, dt.datetime.now(PARIS)), date))
    elif len(args) == 2 and args[1] == "--rattraper":
        print("courses terminées relues pour %s : %d" % (date, rattraper(date)))
    elif len(args) == 2:
        print("%d courses ajoutées à la journée du %s" % (completer(date), date))
    else:
        cs = charger(date, calculer=True)
        print("courses de la journée :", len(cs), "· avec pronostic :", sum(1 for x in cs if x["ordre"]))
