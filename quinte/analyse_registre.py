#!/usr/bin/env python3
"""Analyses du registre des pronostics (quinte/journal/registre.csv).

Mesures faites sur les courses dont l'arrivée est connue (au moins trois partants classés) :
1. Le modèle face au hasard : perte du vainqueur (plus bas = mieux), top 3 retrouvé, favori gagnant.
2. Les notes : pour chacune, le lien moyen avec la place d'arrivée. Négatif = une meilleure note va avec une
   meilleure place. Proche de zéro = la note ne départage pas les chevaux.
3. Le poids porté et la corde : même mesure, par discipline ; le poids aussi par distance.

Tant qu'il y a moins de 100 courses, le rapport le signale : on ne tire pas de conclusion d'un petit échantillon.
Le poids n'entre pas dans la note : le rapport mesure seulement son lien avec la place.

Usage :
    python3 quinte/analyse_registre.py            # affiche le rapport
    python3 quinte/analyse_registre.py --ecrire   # écrit aussi quinte/journal/analyse-registre.md
"""
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import registre  # noqa: E402

SEUIL_FIABLE = 100      # nombre de courses à partir duquel on peut commencer à lire les résultats
DISTANCE_LONGUE = 2400  # mètres
SORTIE = os.path.join(HERE, "journal", "analyse-registre.md")


def _nombre(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fr(x, decimales=2, signe=False):
    texte = ("%+.*f" if signe else "%.*f") % (decimales, x)
    return texte.replace(".", ",")


def famille(discipline):
    d = (discipline or "").lower()
    if "plat" in d:
        return "plat"
    if "haie" in d or "steeple" in d or "cross" in d or "obstacle" in d:
        return "obstacle"
    if "attel" in d or "mont" in d or "trot" in d:
        return "trot"
    return "autre"


def moyenne(xs):
    return sum(xs) / len(xs) if xs else None


def courses_arrivees(lignes):
    """Regroupe les lignes par course ; ne garde que les courses où trois partants au moins sont classés."""
    par_course = defaultdict(list)
    for x in lignes:
        par_course[(x["date"], x["r"], x["c"])].append(x)
    courses = []
    for cle, partants in sorted(par_course.items()):
        classes = [p for p in partants if _nombre(p["arrivee"]) is not None]
        if len(classes) < 3:
            continue
        courses.append({"cle": cle, "partants": partants, "distance": _nombre(partants[0]["distance"])})
    return courses


def modele(courses):
    """Par course : perte du vainqueur pour le modèle et pour le hasard, top 3 retrouvé, favori gagnant."""
    out = []
    for c in courses:
        partants = c["partants"]
        gagnants = [p for p in partants if _nombre(p["arrivee"]) == 1]
        if not gagnants:
            continue
        p_gagnant = _nombre(gagnants[0]["p_victoire"])
        if p_gagnant is None:
            continue
        reels = {p["numero"] for p in partants if _nombre(p["arrivee"]) in (1.0, 2.0, 3.0)}
        predits = {p["numero"] for p in sorted(partants, key=lambda p: -(_nombre(p["p_top3"]) or 0))[:3]}
        favori = min(partants, key=lambda p: _nombre(p["rang"]) or 99)
        out.append({"famille": famille(partants[0]["discipline"]), "distance": c["distance"],
                    "perte": -math.log(max(p_gagnant, 1e-6)), "hasard": math.log(len(partants)),
                    "rappel": len(reels & predits) / max(len(reels), 1),
                    "favori": _nombre(favori["arrivee"]) == 1})
    return out


def correlation(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def correlations(courses, colonne):
    """Par course : corrélation entre une valeur (note, poids, corde) et la place d'arrivée."""
    out = []
    for c in courses:
        pts = [(_nombre(p[colonne]), _nombre(p["arrivee"])) for p in c["partants"]]
        pts = [(a, b) for a, b in pts if a is not None and b is not None]
        r = correlation([a for a, _ in pts], [b for _, b in pts])
        if r is not None:
            out.append({"famille": famille(c["partants"][0]["discipline"]), "distance": c["distance"], "r": r})
    return out


def _ligne_correlation(nom, rs, attendu=0):
    if not rs:
        return "- %s : pas assez de données" % nom
    texte = "- %s (%d courses) : corrélation moyenne %s" % (nom, len(rs), _fr(moyenne([x["r"] for x in rs]), 2, True))
    if attendu:
        dans_le_sens = sum(1 for x in rs if x["r"] * attendu > 0)
        texte += ", dans le sens attendu dans %d courses sur %d" % (dans_le_sens, len(rs))
    return texte


def section_modele(resultats):
    def ligne(nom, rs):
        if not rs:
            return "- %s : aucune course" % nom
        return ("- %s (%d courses) : perte du modèle %s, perte du hasard %s, top 3 retrouvé %s %%, "
                "favori gagnant %s %%") % (
            nom, len(rs), _fr(moyenne([r["perte"] for r in rs])), _fr(moyenne([r["hasard"] for r in rs])),
            _fr(100 * moyenne([r["rappel"] for r in rs]), 0), _fr(100 * sum(r["favori"] for r in rs) / len(rs), 0))
    texte = ["## 1. Le modèle face au hasard", "",
             "Perte du vainqueur : plus c'est bas, mieux c'est.", "", ligne("ensemble", resultats)]
    for f in ("plat", "obstacle", "trot"):
        texte.append(ligne(f, [r for r in resultats if r["famille"] == f]))
    return texte


def section_notes(courses):
    texte = ["## 2. Les notes du modèle", "",
             "Pour chaque note : lien moyen, par course, avec la place d'arrivée. "
             "Négatif = une meilleure note va avec une meilleure place.", ""]
    for nom in registre.NOTES:
        texte.append(_ligne_correlation(nom, correlations(courses, "n_" + nom), attendu=-1))
    return texte


def section_poids(courses):
    avec = [c for c in courses if famille(c["partants"][0]["discipline"]) in ("plat", "obstacle")]
    rs = correlations(avec, "poids")
    longues = [x for x in rs if x["distance"] and x["distance"] >= DISTANCE_LONGUE]
    courtes = [x for x in rs if x["distance"] and x["distance"] < DISTANCE_LONGUE]
    return ["## 3. Le poids porté (plat et obstacle)", "",
            "Lien moyen, par course, entre le poids et la place. Positif = les plus lourds finissent derrière. "
            "Le poids n'entre pas dans la note : on mesure seulement ce lien.", "",
            _ligne_correlation("ensemble", rs, attendu=1),
            _ligne_correlation("plat", [x for x in rs if x["famille"] == "plat"], attendu=1),
            _ligne_correlation("obstacle", [x for x in rs if x["famille"] == "obstacle"], attendu=1),
            _ligne_correlation("distance < %d m" % DISTANCE_LONGUE, courtes, attendu=1),
            _ligne_correlation("distance ≥ %d m" % DISTANCE_LONGUE, longues, attendu=1)]


def section_corde(courses):
    avec = [c for c in courses if famille(c["partants"][0]["discipline"]) in ("plat", "obstacle")]
    rs = correlations(avec, "corde")
    return ["## 4. La place à la corde (plat et obstacle)", "",
            "Lien moyen, par course, entre le numéro de corde et la place. Le sens attendu n'est pas fixé d'avance.",
            "",
            _ligne_correlation("ensemble", rs),
            _ligne_correlation("plat", [x for x in rs if x["famille"] == "plat"]),
            _ligne_correlation("obstacle", [x for x in rs if x["famille"] == "obstacle"])]


def rapport(lignes):
    courses = courses_arrivees(lignes)
    texte = ["# Analyse du registre des pronostics", ""]
    if not courses:
        return "\n".join(texte + ["Rien à analyser pour l'instant : aucune course du registre n'a encore son arrivée."])
    jours = sorted({c["cle"][0] for c in courses})
    chevaux = sum(len(c["partants"]) for c in courses)
    texte.append("Courses avec arrivée connue : %d (%d chevaux), du %s au %s." % (
        len(courses), chevaux, jours[0], jours[-1]))
    if len(courses) < SEUIL_FIABLE:
        texte += ["", "**Échantillon trop petit (moins de %d courses) : ces chiffres servent à suivre, "
                      "pas à conclure.**" % SEUIL_FIABLE]
    texte += [""] + section_modele(modele(courses)) + [""] + section_notes(courses) + [""] \
        + section_poids(courses) + [""] + section_corde(courses)
    return "\n".join(texte)


def main(argv):
    texte = rapport(registre.lire())
    print(texte)
    if "--ecrire" in argv:
        with open(SORTIE, "w", encoding="utf-8") as f:
            f.write(texte + "\n")
        print("\nécrit :", SORTIE)


if __name__ == "__main__":
    main(sys.argv[1:])
