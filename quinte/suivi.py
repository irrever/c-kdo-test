#!/usr/bin/env python3
"""Journal de suivi : enregistre les pronostics avant la course, puis compare aux arrivées.

Usage :
    python3 quinte/suivi.py pronostic AAAA-MM-JJ    # le matin, avant la course
    python3 quinte/suivi.py resultat AAAA-MM-JJ     # le soir, après l'arrivée
    python3 quinte/suivi.py bilan                   # score cumulé contre le hasard

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


def _arrivee(date, r, c):
    """Arrivée officielle : liste des numéros classés, ou None si la course n'est pas terminée."""
    course = eq.course(date, r, c)
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
    existe = os.path.exists(BILAN)
    with open(BILAN, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS_BILAN, delimiter=";")
        if not existe:
            w.writeheader()
        w.writerow(ligne)
    print("bilan mis à jour :", ligne["ordre_predit"], "->", ligne["ordre_reel"])
    return ligne


def bilan():
    if not os.path.exists(BILAN):
        print("Aucune course enregistrée.")
        return
    lignes = list(csv.DictReader(open(BILAN, encoding="utf-8"), delimiter=";"))
    n = len(lignes)
    ll = [float(x["log_loss_gagnant"]) for x in lignes if x["log_loss_gagnant"]]
    br = [float(x["brier_top3"]) for x in lignes]
    rap = [float(x["rappel_top3_predit"]) for x in lignes]
    hasard = math.log(sum(int(x["partants"]) for x in lignes) / n)
    print("courses : %d (dont %d rétroactives)" % (n, sum(1 for x in lignes if x["retroactif"] == "True")))
    print("log-loss gagnant : %.3f (hasard moyen : %.3f)" % (sum(ll) / len(ll), hasard))
    print("Brier top 3      : %.4f" % (sum(br) / n))
    print("rappel top 3     : %.3f (hasard : %.3f)" % (sum(rap) / n, 3 / (sum(int(x["partants"]) for x in lignes) / n)))


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
    else:
        raise SystemExit(__doc__)
