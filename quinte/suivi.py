#!/usr/bin/env python3
"""Journal de suivi : enregistre les pronostics avant la course, puis compare aux arrivées.

Usage :
    python3 quinte/suivi.py pronostic AAAA-MM-JJ    # le matin, avant la course
    python3 quinte/suivi.py resultat AAAA-MM-JJ     # le soir, après l'arrivée
    python3 quinte/suivi.py bilan                   # score cumulé contre le hasard
    python3 quinte/suivi.py cheval NOM              # historique d'un cheval
    python3 quinte/suivi.py chevaux                 # statistiques par cheval

Fichiers :
    quinte/journal/AAAA-MM-JJ.json   pronostic figé avant la course
    quinte/journal/bilan.csv          une ligne par course terminée, avec les mesures
"""
import csv
import datetime as dt
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import equidia as eq  # noqa: E402
import analyse_equidia as ae  # noqa: E402

JOURNAL = os.path.join(HERE, "journal")
BILAN = os.path.join(JOURNAL, "bilan.csv")
CHAMPS_BILAN = ["date", "hippodrome", "partants", "ordre_predit", "ordre_reel", "vainqueur_predit",
                "p_vainqueur_reel", "log_loss_gagnant", "brier_top3", "rappel_top3_predit",
                "pronostic_fige", "retroactif"]


def _fichier_pronostic(date):
    return os.path.join(JOURNAL, "%s.json" % date)


def enregistrer_pronostic(date, retroactif=False):
    """Calcule et fige les pronostics de la course Quinté+ de la date."""
    os.makedirs(JOURNAL, exist_ok=True)
    chemin = _fichier_pronostic(date)
    if os.path.exists(chemin):
        return chemin  # déjà figé : on ne le modifie jamais
    import rapport  # noqa: F401  (vérifie que le module de rapport est disponible)
    q = eq.quinte_du_jour(date)
    if not q:
        raise SystemExit("Pas de Quinté+ trouvé pour %s." % date)
    r, c = q
    page = eq.get_html("%s/courses/%s/R%d/C%d" % (eq.BASE, date, r, c))
    tmp = os.path.join(eq.CACHE, "journal-%s.html" % date)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(page)
    course = ae.charger_etat(tmp)
    lignes = ae.analyser(course)
    ordres = ae.simuler(lignes)
    prob = ae.probabilites(ordres, lignes)
    combis = ae.combinaisons_en_box(ordres, lignes)
    donnees = {
        "date": date,
        "retroactif": retroactif,
        "fige_le": dt.datetime.now().isoformat(timespec="seconds"),
        "hippodrome": course["reunion"]["hippodrome"]["name"],
        "course": "R%dC%d" % (r, c),
        "modele": {"sensibilite_K": ae.SENSIBILITE, "poids": ae.POIDS, "simulations": ae.SIMULATIONS},
        "chevaux": [{"numero": l["numero"], "nom": l["nom"], "score": l["score"],
                     "p_victoire": prob["victoire"][l["numero"]], "p_top3": prob["top3"][l["numero"]],
                     "p_top5": prob["top5"][l["numero"]]} for l in lignes],
        "ordre_predit": [l["numero"] for l in lignes[:5]],
        "combinaisons": combis,
    }
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)
    print("pronostic figé :", chemin)
    return chemin


def enregistrer_final(date):
    """Fige le pronostic final, avec les cotes du moment (une heure avant le départ), une seule fois.

    Le pronostic du soir reste dans le fichier, sous « pronostic_soir ». Les clés principales
    deviennent celles du pronostic final : c'est lui qui sert au bilan et à la comparaison.
    """
    chemin = _fichier_pronostic(date)
    if not os.path.exists(chemin):
        enregistrer_pronostic(date)
    d = json.load(open(chemin, encoding="utf-8"))
    if "final" in d:
        return chemin
    r, c = [int(x) for x in d["course"].replace("R", "").split("C")]
    course = eq.course(date, r, c, fresh=True)
    cotes = ae.cotes_de(course)
    if not cotes:
        raise SystemExit("Cotes indisponibles pour %s : pronostic final non figé." % date)
    lignes = ae.melanger_cotes(ae.analyser(course), cotes)
    ordres = ae.simuler(lignes)
    prob = ae.probabilites(ordres, lignes)
    combis = ae.combinaisons_en_box(ordres, lignes)
    maintenant = dt.datetime.now().isoformat(timespec="seconds")
    d["pronostic_soir"] = {k: d[k] for k in ("fige_le", "modele", "chevaux", "ordre_predit", "combinaisons")}
    d["fige_le"] = maintenant
    d["modele"] = {"sensibilite_K": ae.SENSIBILITE, "poids": ae.POIDS, "simulations": ae.SIMULATIONS,
                   "part_cotes": ae.COTES_POIDS}
    d["chevaux"] = [{"numero": l["numero"], "nom": l["nom"], "score": l["score"],
                     "proba_cotes": l["proba_cotes"], "proba_melange": l["proba_melange"],
                     "p_victoire": prob["victoire"][l["numero"]], "p_top3": prob["top3"][l["numero"]],
                     "p_top5": prob["top5"][l["numero"]]} for l in lignes]
    d["ordre_predit"] = [l["numero"] for l in lignes[:5]]
    d["combinaisons"] = combis
    d["final"] = {"fige_le": maintenant, "cotes": {str(k): v for k, v in cotes.items()}}
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print("pronostic final figé avec les cotes :", chemin)
    return chemin


def _arrivee(date, r, c):
    """Arrivée officielle : liste des numéros classés, ou None si la course n'est pas terminée."""
    course = eq.course(date, r, c, fresh=True)
    if not course or course.get("type_statut_course_id") != "finished":
        return None
    arr = []
    for p in course["partants"]:
        rang = p.get("num_place_arrivee")
        if p.get("statut_part") == "DP" and rang and str(rang).strip().isdigit():
            arr.append((int(str(rang).strip()), p["num_partant"]))
    return [n for _, n in sorted(arr)]


def enregistrer_resultat(date):
    """Compare le pronostic figé à l'arrivée officielle et ajoute une ligne au bilan."""
    chemin = _fichier_pronostic(date)
    if not os.path.exists(chemin):
        raise SystemExit("Pas de pronostic figé pour %s." % date)
    d = json.load(open(chemin, encoding="utf-8"))
    r, c = [int(x) for x in d["course"].replace("R", "").split("C")]
    if os.path.exists(BILAN) and any(x["date"] == date for x in csv.DictReader(open(BILAN, encoding="utf-8"), delimiter=";")):
        print("Résultat déjà enregistré pour %s : aucune ligne ajoutée." % date)
        return None
    reel = _arrivee(date, r, c)
    if not reel or len(reel) < 3:
        print("Course pas encore terminée ou arrivée incomplète pour %s." % date)
        return None
    probas = {x["numero"]: x for x in d["chevaux"]}
    gagnant = reel[0]
    ll = -math.log(max(probas[gagnant]["p_victoire"], 1e-6)) if gagnant in probas else None
    top3_reel = set(reel[:3])
    brier = sum((probas[n]["p_top3"] - (1.0 if n in top3_reel else 0.0)) ** 2 for n in probas) / len(probas)
    predit3 = set(sorted(probas, key=lambda n: -probas[n]["p_top3"])[:3])
    rappel = len(predit3 & top3_reel) / 3
    ligne = {
        "date": date, "hippodrome": d["hippodrome"], "partants": len(probas),
        "ordre_predit": "-".join(str(x) for x in d["ordre_predit"]),
        "ordre_reel": "-".join(str(x) for x in reel[:5]),
        "vainqueur_predit": max(probas, key=lambda n: probas[n]["p_victoire"]),
        "p_vainqueur_reel": round(probas.get(gagnant, {}).get("p_victoire", 0), 4),
        "log_loss_gagnant": round(ll, 4) if ll is not None else "",
        "brier_top3": round(brier, 4), "rappel_top3_predit": round(rappel, 3),
        "pronostic_fige": d["fige_le"], "retroactif": d["retroactif"],
    }
    _ecrire_chevaux(d, reel, date)
    existe = os.path.exists(BILAN)
    with open(BILAN, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS_BILAN, delimiter=";")
        if not existe:
            w.writeheader()
        w.writerow(ligne)
    print("bilan mis à jour :", ligne["ordre_predit"], "->", ligne["ordre_reel"])
    return ligne


CHEVAUX = os.path.join(JOURNAL, "chevaux.csv")
CHAMPS_CHEVAUX = ["date", "course", "hippodrome", "numero", "nom", "score", "p_top3_predit",
                  "p_top5_predit", "place_reelle", "dans_top3", "retroactif"]


def _ecrire_chevaux(d, reel, date):
    """Ajoute une ligne par cheval analysé : prédiction figée et place réelle."""
    rang = {n: i + 1 for i, n in enumerate(reel)}
    existe = os.path.exists(CHEVAUX)
    with open(CHEVAUX, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS_CHEVAUX, delimiter=";")
        if not existe:
            w.writeheader()
        for c in d["chevaux"]:
            place = rang.get(c["numero"], "")
            w.writerow({"date": date, "course": d["course"], "hippodrome": d["hippodrome"],
                        "numero": c["numero"], "nom": c["nom"], "score": round(c["score"], 4),
                        "p_top3_predit": round(c["p_top3"], 4), "p_top5_predit": round(c["p_top5"], 4),
                        "place_reelle": place, "dans_top3": (place != "" and place <= 3),
                        "retroactif": d["retroactif"]})


def historique_cheval(nom):
    """Toutes les courses analysées pour un cheval, avec la prédiction et la place réelle."""
    if not os.path.exists(CHEVAUX):
        print("Aucun cheval suivi pour l'instant.")
        return
    lignes = [x for x in csv.DictReader(open(CHEVAUX, encoding="utf-8"), delimiter=";")
              if nom.upper() in x["nom"].upper()]
    if not lignes:
        print("Aucune course enregistrée pour « %s »." % nom)
        return
    for x in lignes:
        print("%s %s n°%s %s : prédit top 3 %s, place réelle %s%s" % (
            x["date"], x["course"], x["numero"], x["nom"], x["p_top3_predit"],
            x["place_reelle"] or "non classé", " (test rétroactif)" if x["retroactif"] == "True" else ""))


def stats_chevaux():
    """Statistiques par cheval, courses réelles seulement (hors tests rétroactifs)."""
    if not os.path.exists(CHEVAUX):
        print("Aucun cheval suivi pour l'instant.")
        return
    par = {}
    for x in csv.DictReader(open(CHEVAUX, encoding="utf-8"), delimiter=";"):
        if x["retroactif"] == "True":
            continue
        par.setdefault(x["nom"], []).append(x)
    print("%-22s %6s %12s %12s %12s" % ("Cheval", "Courses", "Place moy.", "Top 3 réel", "Top 3 prédit"))
    for nom, lst in sorted(par.items(), key=lambda kv: -len(kv[1])):
        classes = [int(x["place_reelle"]) for x in lst if x["place_reelle"]]
        top3_reel = sum(1 for x in lst if x["dans_top3"] == "True") / len(lst)
        top3_pred = sum(float(x["p_top3_predit"]) for x in lst) / len(lst)
        place_moy = sum(classes) / len(classes) if classes else float("nan")
        print("%-22s %6d %12.1f %11.0f%% %11.0f%%" % (nom[:22], len(lst), place_moy, 100 * top3_reel, 100 * top3_pred))


def comparaison_reelle():
    """Perte du vainqueur sur les courses réelles déjà arrivées, par méthode (plus bas = mieux).

    Méthodes : modèle (pronostic du soir, sans cotes), cotes seules, mélange (pronostic final, 70 % de cotes).
    Renvoie (lignes course par course, moyennes par méthode avec le nombre de courses connues).
    """
    if not os.path.exists(BILAN):
        return [], {}

    def proba(liste, gagnant, cle):
        for c in liste:
            if c["numero"] == gagnant and c.get(cle) is not None:
                return c[cle]
        return None

    def perte(p):
        return -math.log(max(p, 1e-9)) if p is not None else None

    lignes = []
    for x in csv.DictReader(open(BILAN, encoding="utf-8"), delimiter=";"):
        if x["retroactif"] == "True" or not x["ordre_reel"]:
            continue
        chemin = _fichier_pronostic(x["date"])
        if not os.path.exists(chemin):
            continue
        j = json.load(open(chemin, encoding="utf-8"))
        gagnant = int(x["ordre_reel"].split("-")[0])
        soir = (j.get("pronostic_soir") or {}).get("chevaux") or j.get("chevaux") or []
        final = j.get("chevaux") if "final" in j else []
        lignes.append({
            "date": x["date"], "hippodrome": x["hippodrome"], "gagnant": gagnant,
            "partants": int(x["partants"]),
            "modele": perte(proba(soir, gagnant, "p_victoire")),
            "cotes": perte(proba(final, gagnant, "proba_cotes")),
            "melange": perte(proba(final, gagnant, "proba_melange")),
        })
    moyennes = {}
    for cle in ["modele", "cotes", "melange"]:
        valeurs = [l[cle] for l in lignes if l[cle] is not None]
        moyennes[cle] = (sum(valeurs) / len(valeurs) if valeurs else None, len(valeurs))
    hasard = [math.log(l["partants"]) for l in lignes]
    moyennes["hasard"] = (sum(hasard) / len(hasard) if hasard else None, len(hasard))
    return lignes, moyennes


def _afficher_comparaison():
    """Tableau course par course, puis moyennes : modèle, cotes seules, mélange, hasard."""
    lignes, moyennes = comparaison_reelle()
    if not lignes:
        return

    def f(v):
        return "%.3f" % v if v is not None else "—"

    print()
    print("%-11s %-18s %-8s %-8s %-8s %-8s" % ("date", "hippodrome", "gagnant", "modèle", "cotes", "mélange"))
    for l in lignes:
        print("%-11s %-18s %-8s %-8s %-8s %-8s" % (l["date"], l["hippodrome"][:18], l["gagnant"],
                                                   f(l["modele"]), f(l["cotes"]), f(l["melange"])))
    print()
    noms = [("modele", "modèle"), ("cotes", "cotes seules"), ("melange", "mélange (70 % cotes)"), ("hasard", "hasard")]
    for cle, nom in noms:
        v, n = moyennes[cle]
        print("perte moyenne du vainqueur, %-22s : %s (%d course%s)" % (nom, f(v), n, "" if n == 1 else "s"))


def bilan():
    if not os.path.exists(BILAN):
        print("Aucune course enregistrée.")
        return
    toutes = list(csv.DictReader(open(BILAN, encoding="utf-8"), delimiter=";"))
    lignes = [x for x in toutes if x["retroactif"] != "True"]
    retro = [x for x in toutes if x["retroactif"] == "True"]
    n = len(lignes)
    if n == 0:
        print("Aucune course réelle enregistrée (seulement des tests rétroactifs).")
        return
    ll = [float(x["log_loss_gagnant"]) for x in lignes if x["log_loss_gagnant"]]
    br = [float(x["brier_top3"]) for x in lignes]
    rap = [float(x["rappel_top3_predit"]) for x in lignes]
    hasard = math.log(sum(int(x["partants"]) for x in lignes) / n)
    print("courses réelles (avant course) : %d" % n)
    print("tests rétroactifs (séparés, non inclus) : %d" % len(retro))
    print("log-loss gagnant : %.3f (hasard moyen : %.3f)" % (sum(ll) / len(ll), hasard))
    print("Brier top 3      : %.4f" % (sum(br) / n))
    print("rappel top 3     : %.3f (hasard : %.3f)" % (sum(rap) / n, 3 / (sum(int(x["partants"]) for x in lignes) / n)))
    _afficher_comparaison()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    if cmd == "pronostic":
        enregistrer_pronostic(sys.argv[2], retroactif="--retro" in sys.argv)
    elif cmd == "resultat":
        enregistrer_resultat(sys.argv[2])
    elif cmd == "bilan":
        bilan()
    elif cmd == "cheval":
        historique_cheval(sys.argv[2])
    elif cmd == "chevaux":
        stats_chevaux()
    else:
        raise SystemExit(__doc__)
