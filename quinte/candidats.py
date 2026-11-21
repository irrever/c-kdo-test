#!/usr/bin/env python3
"""Propositions de pronostic, comparées sur les mêmes courses que le constat (courses avec cotes complètes).

Rien n'est ajusté ici : K = 4 (notre réglage), mélanges à 70 % ou 50 % de cotes, moyenne des rangs du modèle et du
marché. Les courses, les probabilités et la méthode des intervalles viennent de constat.py. Le résultat est écrit dans
quinte/journal/candidats.md et imprimé.
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import constat as C  # noqa: E402

SORTIE = os.path.join(HERE, "journal", "candidats.md")
TIRAGES = 2000
MOYENNE_DES_RANGS = "Moyenne des rangs, modèle et marché"


def melange(c, K, poids):
    pm = C._proba_modele(c["scores"], K)
    pk = C._proba_cotes(c["cotes"])
    return {n: poids * pk[n] + (1 - poids) * pm[n] for n in pm}


def classement_moyen(c):
    """Moyenne des rangs du modèle (K 4) et du marché, à poids égaux. Renvoie une note : plus haut = meilleur."""
    pm = C._proba_modele(c["scores"], 4.0)
    pk = C._proba_cotes(c["cotes"])
    r1 = {n: i + 1 for i, n in enumerate(sorted(pm, key=lambda k: (-pm[k], int(k))))}
    r2 = {n: i + 1 for i, n in enumerate(sorted(pk, key=lambda k: (-pk[k], int(k))))}
    return {n: -(r1[n] + r2[n]) / 2.0 for n in pm}


VARIANTES = [
    ("Hasard", None),
    ("Favori des cotes", lambda c: C._proba_cotes(c["cotes"])),
    ("Mélange 70 % cotes, K 4", lambda c: melange(c, 4.0, 0.7)),
    ("Mélange 50 % cotes, K 4", lambda c: melange(c, 4.0, 0.5)),
    ("Notre analyse, sans cotes (production)", lambda c: C._proba_modele(c["scores"], 4.0)),
    (MOYENNE_DES_RANGS, classement_moyen),
]


def mesurer(c, p, probabilite=True):
    """(perte du vainqueur, top 1, top 3, arrivants dans le top 5, couverture) pour une course.
    La perte n'a de sens que pour des probabilités ; la couverture est le rang du dernier des cinq arrivants."""
    ordre = sorted(p, key=lambda k: (-p[k], int(k)))
    cinq = {n for n, a in c["places"].items() if a is not None and a <= 5}
    pos = {n: i + 1 for i, n in enumerate(ordre)}
    perte = -math.log(max(p[c["gagnant"]], 1e-9)) if probabilite else None
    return (perte, 1.0 if ordre[0] == c["gagnant"] else 0.0, 1.0 if c["gagnant"] in ordre[:3] else 0.0,
            float(len(set(ordre[:5]) & cinq)), float(max(pos[n] for n in cinq)))


def ecart(a, b, k):
    """Écarts appariés (a − b) par course pour la colonne k, avec la moyenne et l'intervalle à 95 %."""
    d = [x[k] - y[k] for x, y in zip(a, b)]
    rng = random.Random(C.SEED)
    n = len(d)
    tirages = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(TIRAGES))
    return sum(d) / n, tirages[int(0.025 * TIRAGES)], tirages[int(0.975 * TIRAGES) - 1]


def fr(x, d=2, signe=False):
    s = ("%+.*f" if signe else "%.*f") % (d, x)
    return s.replace(".", ",")


def main():
    print("Propositions de pronostic : arrêté. Ce rapport comparait des pronostics au marché.")


if __name__ == "__main__":
    main()
