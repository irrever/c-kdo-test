#!/usr/bin/env python3
"""Mesure de chaque quinté, inscrite chaque soir dans le bilan.

Pour chaque quinté : le rang médian de ses cinq arrivants dans notre classement, et la
couverture de chaque boîte de k chevaux (k de 5 à 9). Une boîte couvre le quinté si ses cinq arrivants sont dans les
k premiers de notre classement : c'est la seule condition pour gagner un quinté désordre.

Une ligne par quinté dans quinte/journal/mesure-quintes.csv. Une même date n'est inscrite qu'une fois.
"""
import csv
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import registre  # noqa: E402

CHEMIN = os.path.join(HERE, "journal", "mesure-quintes.csv")
CHAMPS = ["date", "course", "hippodrome", "partants", "arrivee", "rang_median_notre",
          "couv_5", "couv_6", "couv_7", "couv_8", "couv_9", "boite_complete"]
KS = range(5, 10)


def mesure_course(lignes):
    """Mesure d'une course à partir de ses lignes du registre. Seuls comptent les partants qui ont couru : un
    non-partant ne classe pas le quinté et n'a pas sa place dans notre classement."""
    coureurs = registre.coureurs(lignes)
    arrivants = sorted((l for l in coureurs if l["arrivee"]), key=lambda l: int(float(l["arrivee"])))
    cinq = [l["numero"] for l in arrivants[:5]]
    notre = [l["numero"] for l in sorted(coureurs, key=lambda l: (-float(l["score"]), int(l["numero"])))]
    rang_notre = {n: i + 1 for i, n in enumerate(notre)}
    couv = {k: sum(1 for n in cinq if n in notre[:k]) for k in KS}
    return {
        "arrivee": "-".join(cinq),
        "partants": len(coureurs),
        "rang_median_notre": statistics.median([rang_notre[n] for n in cinq]) if len(cinq) == 5 else "",
        "couv": couv,
        "boite_complete": next((k for k in KS if couv[k] == 5), ""),
    }


def _lire():
    if not os.path.exists(CHEMIN):
        return []
    with open(CHEMIN, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _ecrire(lignes):
    os.makedirs(os.path.dirname(CHEMIN), exist_ok=True)
    with open(CHEMIN, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(lignes, key=lambda x: x["date"]))


def enregistrer(date, lignes=None):
    """Mesure le quinté du jour et l'inscrit (une seule ligne par date). None s'il n'a pas encore d'arrivée."""
    import suivi
    chemin = suivi._fichier_pronostic(date)
    if not os.path.exists(chemin):
        return None
    with open(chemin, encoding="utf-8") as f:
        r, c = [int(x) for x in json.load(f)["course"].replace("R", "").split("C")]
    lignes = registre.lire() if lignes is None else lignes
    rows = [l for l in lignes if l["date"] == date and l["r"] == str(r) and l["c"] == str(c)]
    if not rows or not any(l["arrivee"] for l in rows) or not registre.statut_connu(rows):
        return None  # pas encore d'arrivée, ou statut d'un partant non relevé
    m = mesure_course(rows)
    ligne = {"date": date, "course": "R%dC%d" % (r, c), "hippodrome": rows[0]["hippodrome"],
             "partants": m["partants"], "arrivee": m["arrivee"],
             "rang_median_notre": m["rang_median_notre"],
             "couv_5": m["couv"][5], "couv_6": m["couv"][6], "couv_7": m["couv"][7],
             "couv_8": m["couv"][8], "couv_9": m["couv"][9], "boite_complete": m["boite_complete"]}
    ligne = {k: str(v) for k, v in ligne.items()}
    _ecrire([x for x in _lire() if x["date"] != date] + [ligne])
    return ligne


def _moyenne(valeurs):
    xs = [float(v) for v in valeurs if v != ""]
    return sum(xs) / len(xs) if xs else None


def _virgule(x):
    """Nombre en français, comme 3,5 ; « — » si absent."""
    if x is None or x == "":
        return "—"
    return ("%g" % round(float(x), 2)).replace(".", ",")


def bloc_bilan(date, lignes=None):
    """Section du bilan : le quinté du jour, puis le cumul de tous les quintés mesurés."""
    ligne = enregistrer(date, lignes)
    L = ["", "## 4. Le quinté : rangs et couvertures", ""]
    if ligne is None:
        L.append("Pas de quinté mesuré pour cette journée (arrivée ou statut des partants non relevés).")
    else:
        L.append("%s · %s · %s partants · arrivée %s." % (ligne["course"], ligne["hippodrome"], ligne["partants"],
                                                         ligne["arrivee"]))
        complete = ("à partir de %s chevaux" % ligne["boite_complete"]) if ligne["boite_complete"] \
            else "aucune jusqu'à 9 chevaux"
        L.append("Rang médian des arrivants : %s chez nous. Boîte complète : %s."
                 % (_virgule(ligne["rang_median_notre"]), complete))
        L.append("Arrivants couverts : 5 chevaux %s sur 5 ; 6 chevaux %s ; 7 chevaux %s ; 8 chevaux %s ; 9 chevaux %s."
                 % (ligne["couv_5"], ligne["couv_6"], ligne["couv_7"], ligne["couv_8"], ligne["couv_9"]))
    cumul = _lire()
    if cumul:
        n = len(cumul)
        complets = [int(x["boite_complete"]) for x in cumul if x["boite_complete"] != ""]
        notre = _moyenne([x["rang_median_notre"] for x in cumul])
        couv = ["%d chevaux %s" % (k, _virgule(_moyenne([x["couv_%d" % k] for x in cumul]))) for k in KS]
        dont = ", ".join("à %d chevaux : %d" % (k, complets.count(k)) for k in KS if complets.count(k)) or "aucun"
        L += ["", "Cumul sur %d quinté(s) : rang médian moyen des arrivants %s chez nous. "
              "Couverture moyenne (sur 5 arrivants) : %s. Boîte complète : %d quinté(s) sur %d, dont %s."
              % (n, _virgule(notre), " ; ".join(couv), len(complets), n, dont)]
    return "\n".join(L) + "\n"
