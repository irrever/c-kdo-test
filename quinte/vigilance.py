#!/usr/bin/env python3
"""Zones de vigilance du pronostic final : les chevaux où notre modèle et le marché sont à deux fois d'écart.

Méfiance : le modèle y croit au moins deux fois plus que le marché. À surveiller : le marché y croit au moins deux
fois plus que le modèle. Les parts sont celles du mélange à 90 % (au trot, cotes seules) : part du modèle (notes, avec la sensibilité K) et
part du marché (cotes, marge retirée). Seuls les chevaux qui ont au moins 6 % de chances dans l'un des
deux avis sont signalés. Repère simple, pas encore validé sur nos courses.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyse_equidia as ae  # noqa: E402

SEUIL = 2.0      # écart d'un facteur deux au moins
MIN_PART = 0.06   # au moins 6 % de chances dans l'un des deux avis : sinon ce ne sont que des outsiders
MAX_PAR_ZONE = 5


def part_modele(scores):
    """Part du modèle seul : softmax de K × note, comme dans melanger_cotes."""
    m = max(scores.values())
    w = {k: math.exp(ae.SENSIBILITE * (s - m)) for k, s in scores.items()}
    total = sum(w.values())
    return {k: w[k] / total for k in w}


def zones(pm, pk):
    """Numéros en méfiance et à surveiller, du plus fort écart au plus faible (MAX_PAR_ZONE au plus)."""
    mefiance, surveiller = [], []
    for k in pm:
        if pm[k] <= 0 or pk.get(k, 0) <= 0 or max(pm[k], pk[k]) < MIN_PART:
            continue
        if pm[k] / pk[k] >= SEUIL:
            mefiance.append((pm[k] / pk[k], k))
        elif pk[k] / pm[k] >= SEUIL:
            surveiller.append((pk[k] / pm[k], k))

    def trier(xs):
        return [k for _, k in sorted(xs, reverse=True)][:MAX_PAR_ZONE]

    return trier(mefiance), trier(surveiller)


def depuis_journal(d):
    """Données du pronostic final, à partir du journal. None tant que le pronostic final n'est pas figé."""
    if "final" not in d:
        return None
    chevaux = d["chevaux"]
    scores = {x["numero"]: x["score"] for x in chevaux}
    pk = {x["numero"]: x["proba_cotes"] for x in chevaux}
    melange = {x["numero"]: x["proba_melange"] for x in chevaux}
    noms = {x["numero"]: x["nom"] for x in chevaux}
    pm = part_modele(scores)
    mefiance, surveiller = zones(pm, pk)
    cotes = {int(k): v for k, v in d["final"]["cotes"].items()}
    ordre_final = sorted(melange, key=lambda k: (-melange[k], k))
    soir = d.get("pronostic_soir", {}).get("chevaux", [])
    return {
        "mefiance": mefiance, "surveiller": surveiller, "pm": pm, "pk": pk, "noms": noms, "cotes": cotes,
        "melange": melange, "ordre_final": ordre_final, "fige_le": d["final"]["fige_le"],
        "rang_soir": {x["numero"]: i for i, x in enumerate(soir, start=1)},
        "rang_final": {k: i for i, k in enumerate(ordre_final, start=1)},
        "rang_marche": {k: i for i, k in enumerate(sorted(pk, key=lambda k: (-pk[k], k)), start=1)},
    }


def modele_seul(d):
    """Le pronostic du soir, sans cotes, gardé à côté du pronostic final. None s'il n'y a pas de final."""
    if "final" not in d or "pronostic_soir" not in d:
        return None
    soir = d["pronostic_soir"]
    return {"fige_le": soir["fige_le"], "ordre": list(soir["ordre_predit"])[:5],
            "noms": {x["numero"]: x["nom"] for x in soir["chevaux"]},
            "notes": {x["numero"]: x["score"] for x in soir["chevaux"]}}
