#!/usr/bin/env python3
"""Constat réel sur les courses terminées du registre : modèle, marché et réglages testés.

Sur les mêmes courses, compare le hasard, le modèle (réglage actuel : sensibilité 8), le favori des cotes, le mélange
actuel (70 % de cotes) et le réglage proposé (sensibilité 4, 90 % de cotes, trot aux cotes seules).
Mesures : perte du vainqueur (plus bas = mieux), taux de top 1 et de top 3, et l'argent : rapport officiel du simple
gagnant et du simple placé sur le pronostic n°1, pour 1 € par course. Les intervalles à 95 % viennent d'un
rééchantillonnage des courses.

Usage : python3 quinte/constat.py        (écrit aussi quinte/journal/constat.md)
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyse_registre as ar  # noqa: E402
import registre  # noqa: E402

SORTIE = os.path.join(HERE, "journal", "constat.md")
TIRAGES = 2000  # rééchantillonnages pour les intervalles à 95 %
SEED = 20261109
CHANGEMENT_K = "2026-11-09T21:30"  # à partir de là, le registre porte K = 4 (8 avant)
FAMILLES = ("plat", "obstacle", "trot", "autre")
LIBELLES = {
    "hasard": "Hasard",
    "modele": "Modèle actuel (sensibilité 8)",
    "favori": "Favori des cotes",
    "melange": "Mélange actuel (70 % cotes)",
    "propose": "Réglage proposé (sensibilité 4, 90 % cotes, trot aux cotes)",
}
COMPARAISONS = [
    ("Perte du vainqueur : réglage proposé − modèle actuel", "propose", "modele", 0, "perte"),
    ("Perte du vainqueur : favori des cotes − modèle actuel", "favori", "modele", 0, "perte"),
    ("Top 1 : réglage proposé − modèle actuel", "propose", "modele", 1, "pts"),
    ("Gagnant pour 1 € : réglage proposé − modèle actuel", "propose", "modele", 3, "pts"),
    ("Gagnant pour 1 € : favori des cotes − modèle actuel", "favori", "modele", 3, "pts"),
    ("Placé pour 1 € : réglage proposé − modèle actuel", "propose", "modele", 4, "pts"),
    ("Placé pour 1 € : favori des cotes − modèle actuel", "favori", "modele", 4, "pts"),
]


def _proba_modele(scores, K):
    """Probabilité de gagner selon le modèle : poids exp(K × note), normalisés. C'est le premier rang de la simulation."""
    m = max(scores.values())
    w = {n: math.exp(K * (s - m)) for n, s in scores.items()}
    t = sum(w.values())
    return {n: v / t for n, v in w.items()}


def _proba_cotes(cotes):
    """Probabilité implicite de chaque cheval d'après sa cote : 1 / cote, normalisé."""
    inverses = {n: 1.0 / c for n, c in cotes.items()}
    t = sum(inverses.values())
    return {n: v / t for n, v in inverses.items()}


def _melange(c, K, poids):
    if not c["cotes"]:
        return None
    pm = _proba_modele(c["scores"], K)
    pk = _proba_cotes(c["cotes"])
    return {n: poids * pk[n] + (1 - poids) * pm[n] for n in pm}


def _propose(c):
    if c["famille"] == "trot":
        return _proba_cotes(c["cotes"]) if c["cotes"] else None
    return _melange(c, 4.0, 0.9)


PROBABILITES = {
    "modele": lambda c: _proba_modele(c["scores"], 8.0),
    "favori": lambda c: _proba_cotes(c["cotes"]) if c["cotes"] else None,
    "melange": lambda c: _melange(c, 8.0, 0.7),
    "propose": _propose,
}


def charger(lignes=None):
    """Courses terminées exploitables, avec leurs notes, leurs cotes de départ (si tous les partants en ont),
    leur vainqueur et leurs rapports officiels. Renvoie (courses, écartées par motif)."""
    lignes = registre.lire() if lignes is None else lignes
    courses, ecartees = [], {"sans rapport gagnant": 0, "rapport placé incomplet": 0}
    for c in ar.courses_arrivees(lignes):
        partants = [p for p in c["partants"] if ar._nombre(p["arrivee"]) is not None]  # sans arrivée : non-partant retiré
        gagnants = [p for p in partants if ar._nombre(p["arrivee"]) == 1]
        if len(gagnants) != 1:
            continue
        gagnant = gagnants[0]
        placés = {p["numero"] for p in partants if ar._nombre(p["arrivee"]) in (1.0, 2.0, 3.0)}
        rp = {p["numero"]: ar._nombre(p.get("rapport_place")) for p in partants if p["numero"] in placés}
        rp = {n: v for n, v in rp.items() if v}
        rg = ar._nombre(gagnant.get("rapport_gagnant"))
        if not rg:
            ecartees["sans rapport gagnant"] += 1
            continue
        if len(rp) != len(placés):
            ecartees["rapport placé incomplet"] += 1
            continue
        cotes, sources = {}, set()
        for p in partants:
            if ar._nombre(p.get("cote_depart")):
                v = ar._nombre(p["cote_depart"])
                sources.add("reprise" if p.get("heure_cote") == "reprise" else "captée")
            else:
                v = ar._nombre(p.get("cote"))
                sources.add("cote du registre")
            if not v or v <= 0:
                cotes = None
                break
            cotes[p["numero"]] = v
        courses.append({
            "cle": c["cle"], "calcule_le": c["partants"][0]["calcule_le"], "n": len(partants), "famille": ar.famille(partants[0]["discipline"]),
            "scores": {p["numero"]: float(p["score"]) for p in partants},
            "scores_tous": {p["numero"]: float(p["score"]) for p in c["partants"]},
            "p_registre": {p["numero"]: ar._nombre(p.get("p_victoire")) for p in c["partants"]},
            "cotes": cotes, "sources": sources, "gagnant": gagnant["numero"], "placés": placés,
            "rg": rg, "rp": rp,
        })
    return courses, ecartees


def evaluer(courses, cle):
    """Par course, pour une variante : (perte du vainqueur, top 1, top 3, gain du gagnant, gain du placé), gains
    pour 1 € sur le pronostic n°1. None quand une cote manque. Le hasard donne l'espérance : chaque cheval a une
    chance sur n d'être choisi."""
    sortie = []
    for c in courses:
        if cle == "hasard":
            n = c["n"]
            sortie.append((math.log(n), 1 / n, min(3, n) / n, c["rg"] / n, sum(c["rp"].values()) / n))
            continue
        p = PROBABILITES[cle](c)
        if p is None:
            sortie.append(None)
            continue
        ordre = sorted(p, key=lambda k: (-p[k], int(k)))
        pick = ordre[0]
        perte = -math.log(max(p[c["gagnant"]], 1e-9))
        top1 = 1.0 if pick == c["gagnant"] else 0.0
        top3 = 1.0 if c["gagnant"] in ordre[:3] else 0.0
        gain_g = c["rg"] if pick == c["gagnant"] else 0.0
        gain_p = c["rp"].get(pick, 0.0) if pick in c["placés"] else 0.0
        sortie.append((perte, top1, top3, gain_g, gain_p))
    return sortie


def moyennes(resultats):
    """Moyennes sur les courses calculées. Les gains sont donnés en bénéfice pour 1 € misé (gain moins mise)."""
    xs = [r for r in resultats if r is not None]
    if not xs:
        return None
    n = len(xs)
    m = [sum(r[k] for r in xs) / n for k in range(5)]
    return {"n": n, "perte": m[0], "top1": m[1], "top3": m[2], "gagnant": m[3] - 1, "place": m[4] - 1}


def _alignes(ra, rb):
    """Mêmes courses dans les deux listes : celles où les deux variantes sont calculées."""
    paires = [(x, y) for x, y in zip(ra, rb) if x is not None and y is not None]
    return [p[0] for p in paires], [p[1] for p in paires]


def intervalle(a, b, k, rng):
    """Différence moyenne a − b sur la colonne k, avec son intervalle à 95 % (rééchantillonnage des courses)."""
    d = [x[k] - y[k] for x, y in zip(a, b)]
    n = len(d)
    tirages = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(TIRAGES))
    return sum(d) / n, tirages[int(0.025 * TIRAGES)], tirages[int(0.975 * TIRAGES) - 1]


def _fr(x, d=2, signe=False):
    return ar._fr(x, d, signe)


def _pourcent(x):
    return _fr(100 * x, 1, True) + " %"


def _ecart(x, unite):
    if unite == "perte":
        return _fr(x, 2, True)
    return _fr(100 * x, 1, True) + " pts"


def _ligne_tableau(nom, m):
    if not m:
        return "| %s | — | — | — | — | — |" % nom
    return "| %s | %s | %s | %s | %s | %s |" % (
        nom, _fr(m["perte"]), _fr(100 * m["top1"], 1) + " %", _fr(100 * m["top3"], 1) + " %",
        _pourcent(m["gagnant"]), _pourcent(m["place"]))


def rapport(courses, ecartees):
    """Texte du constat, en Markdown."""
    avec = [c for c in courses if c["cotes"]]
    rng = random.Random(SEED)
    resultats = {k: evaluer(avec, k) for k in LIBELLES}
    toutes = evaluer(courses, "modele")
    captees = sum(1 for c in avec if c["sources"] == {"captée"})
    reprises = sum(1 for c in avec if c["sources"] == {"reprise"})
    ecarts = []  # contrôle sur tous les partants analysés, y compris ceux retirés avant le départ
    for c in courses:
        K = 4.0 if c["calcule_le"] >= CHANGEMENT_K else 8.0  # chaque ligne du registre porte le K de son calcul
        pm = _proba_modele(c["scores_tous"], K)
        ecarts += [abs(pm[n] - v) for n, v in c["p_registre"].items() if v is not None]
    L = ["# Constat réel : modèle, marché et rapports", ""]
    L.append("Courses terminées exploitables : %d, dont %d avec les cotes de départ de tous les partants. Écartées : %s."
             % (len(courses), len(avec), ", ".join("%s %d" % (motif, n) for motif, n in ecartees.items())))
    L.append("Origine des cotes : %d course(s) relevées avant le départ, %d relues après la course, %d autre(s)."
             % (captees, reprises, len(avec) - captees - reprises))
    if ecarts:
        L.append("Contrôle : la probabilité du modèle reconstruite s'écarte de celle du registre de %s en moyenne "
                 "(%s au plus), à cause des simulations." % (_fr(sum(ecarts) / len(ecarts), 4), _fr(max(ecarts), 4)))
    L += ["", "## 1. Sur les %d courses avec cotes complètes" % len(avec), "",
          "| Variante | Perte du vainqueur | Top 1 | Top 3 | Gagnant : bénéfice pour 1 € | Placé : bénéfice pour 1 € |",
          "|---|---:|---:|---:|---:|---:|"]
    for k in LIBELLES:
        L.append(_ligne_tableau(LIBELLES[k], moyennes(resultats[k])))
    L.append(_ligne_tableau("Modèle actuel, sur toutes les %d courses" % len(courses), moyennes(toutes)))
    if avec:
        L += ["", "## 2. Différences entre variantes, avec intervalle à 95 %", ""]
        for libelle, a, b, k, unite in COMPARAISONS:
            xa, xb = _alignes(resultats[a], resultats[b])
            if not xa:
                continue
            d, lo, hi = intervalle(xa, xb, k, rng)
            L.append("- %s : %s [intervalle %s ; %s]" % (libelle, _ecart(d, unite), _ecart(lo, unite), _ecart(hi, unite)))
        L += ["", "## 3. Perte du vainqueur par famille, sur les %d courses avec cotes" % len(avec), "",
              "| Famille | Courses | Hasard | Modèle | Favori | Mélange | Proposé |",
              "|---|---:|---:|---:|---:|---:|---:|"]
        for f in FAMILLES:
            sous = [i for i, c in enumerate(avec) if c["famille"] == f]
            if not sous:
                continue
            cellules = []
            for k in LIBELLES:
                xs = [resultats[k][i][0] for i in sous if resultats[k][i] is not None]
                cellules.append(_fr(sum(xs) / len(xs)) if xs else "—")
            L.append("| %s | %d | %s |" % (f.capitalize(), len(sous), " | ".join(cellules)))
    L += ["", "## Réserves", "",
          "- Le réglage proposé a été choisi sur les courses déjà vues : seul un nouveau lot de courses peut le confirmer.",
          "- Les cotes « relues après la course » sont les dernières cotes avant le départ, telles que la page Equidia "
          "les garde. Ce ne sont pas des relevés faits pendant la journée.",
          "- Les gains sont ceux de la page Equidia une fois la course terminée : simple gagnant et simple placé, "
          "pour 1 € misé."]
    return "\n".join(L) + "\n"


def main():
    courses, ecartees = charger()
    texte = rapport(courses, ecartees)
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    with open(SORTIE, "w", encoding="utf-8") as f:
        f.write(texte)
    print(texte)


if __name__ == "__main__":
    main()
