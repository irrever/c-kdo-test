#!/usr/bin/env python3
"""Essai hors production : le codage du chrono, évalué chaque soir sans rien changer au pronostic.

Quatre variantes, sur les mêmes courses. Elles ne changent que la manière de noter une composante manquante ou nulle :
- actuel : une composante absente compte pour 0,5 ; un chrono à 0,0 reste 0,0 (c'est la production) ;
- chrono_0_neutre : un chrono à 0,0 compte pour 0,5 ;
- absents_retires : une composante absente est retirée, les poids restants sont renormalisés ;
- les_deux : les deux changements ensemble.

Règle fixée avant de regarder les résultats : une variante n'est adoptée que si, sur au moins 300 courses postérieures
au 9 novembre, elle baisse la perte du vainqueur d'au moins 0,02, augmente le top 3 d'au moins 2 points, et si ce gain
apparaît dans chacune des deux moitiés de la période. Les courses du 8 et du 9 novembre ont servi à concevoir les
variantes : elles restent exploratoires.

Chaque jour, le bilan (constat.py --jour) ajoute une ligne par variante dans quinte/journal/essais-chronos.csv.
"""
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyse_equidia as ae  # noqa: E402
import registre  # noqa: E402

CHEMIN = os.path.join(HERE, "journal", "essais-chronos.csv")
VARIANTES = ("actuel", "chrono_0_neutre", "absents_retires", "les_deux")
LIBELLES = {
    "actuel": "Actuel (production)",
    "chrono_0_neutre": "Chrono à 0,0 traité comme neutre",
    "absents_retires": "Composantes absentes retirées",
    "les_deux": "Les deux ensemble",
}
K = 4.0
DEBUT_HORS_ECHANTILLON = "2026-11-10"
SEUIL_COURSES = 300
CHAMPS = ["date", "variante", "courses", "somme_perte", "somme_top1", "somme_top3"]


def _fr(x, d):
    """Nombre en français, avec d décimales."""
    return ("%.*f" % (d, x)).replace(".", ",")


def score(ligne, variante):
    """Note d'un partant selon la variante. Une composante absente vaut 0,5, comme dans notre analyse, sauf pour les
    variantes qui la retirent. Pour la variante actuelle, la note est celle de la production."""
    renormaliser = variante in ("absents_retires", "les_deux")
    total = poids_total = 0.0
    for n in registre.NOTES:
        v = ligne.get("n_" + n, "")
        if v == "":
            if renormaliser:
                continue
            x = 0.5
        else:
            x = float(v)
            if n == "chronos" and x == 0.0 and variante in ("chrono_0_neutre", "les_deux"):
                x = 0.5
        total += ae.POIDS[n] * x
        poids_total += ae.POIDS[n]
    if renormaliser:
        return total / poids_total if poids_total else 0.5  # aucune composante : note neutre, comme en production
    return total


def evaluer_course(lignes, variante):
    """Perte du vainqueur, top 1 et top 3 d'une course selon la variante. None si la course n'a pas de vainqueur."""
    gagnants = [l["numero"] for l in lignes if l["arrivee"] == "1"]
    if len(gagnants) != 1:
        return None
    gagnant = gagnants[0]
    notes = {l["numero"]: score(l, variante) for l in lignes}
    m = max(notes.values())
    poids = {k: math.exp(K * (v - m)) for k, v in notes.items()}
    p = poids[gagnant] / sum(poids.values())
    ordre = sorted(notes, key=lambda k: (-notes[k], int(k)))
    return (-math.log(max(p, 1e-9)), 1.0 if ordre[0] == gagnant else 0.0, 1.0 if gagnant in ordre[:3] else 0.0)


def resultats_du_jour(date, lignes):
    """Pour chaque variante : nombre de courses, et sommes de la perte, du top 1 et du top 3 sur les courses du jour."""
    par_course = {}
    for l in lignes:
        if l["date"] == date and l.get("sans_donnees") != "1":
            par_course.setdefault((l["r"], l["c"]), []).append(l)
    out = {v: [0, 0.0, 0.0, 0.0] for v in VARIANTES}
    for course in par_course.values():
        for v in VARIANTES:
            r = evaluer_course(course, v)
            if r is None:
                continue
            out[v][0] += 1
            out[v][1] += r[0]
            out[v][2] += r[1]
            out[v][3] += r[2]
    return out


def _lire():
    if not os.path.exists(CHEMIN):
        return []
    with open(CHEMIN, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def enregistrer(date, lignes=None):
    """Inscrit les résultats du jour (une seule série par date) et les renvoie."""
    lignes = registre.lire() if lignes is None else lignes
    res = resultats_du_jour(date, lignes)
    autres = [x for x in _lire() if x["date"] != date]
    for v in VARIANTES:
        n, p, t1, t3 = res[v]
        autres.append({"date": date, "variante": v, "courses": str(n), "somme_perte": "%.6f" % p,
                       "somme_top1": "%.1f" % t1, "somme_top3": "%.1f" % t3})
    autres.sort(key=lambda x: (x["date"], VARIANTES.index(x["variante"])))
    os.makedirs(os.path.dirname(CHEMIN), exist_ok=True)
    with open(CHEMIN, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS, delimiter=";")
        w.writeheader()
        w.writerows(autres)
    return res


def cumul():
    """Totaux par variante sur les courses hors échantillon (à partir du 10 novembre), et par moitié de la période."""
    hors = [x for x in _lire() if x["date"] >= DEBUT_HORS_ECHANTILLON]
    jours = sorted({x["date"] for x in hors})
    moitie = {j: (0 if i < len(jours) / 2 else 1) for i, j in enumerate(jours)}
    tot = {v: [0, 0.0, 0.0, 0.0] for v in VARIANTES}
    demi = {(v, h): [0, 0.0, 0.0, 0.0] for v in VARIANTES for h in (0, 1)}
    for x in hors:
        v = x["variante"]
        valeurs = [int(x["courses"]), float(x["somme_perte"]), float(x["somme_top1"]), float(x["somme_top3"])]
        for acc in (tot[v], demi[(v, moitie[x["date"]])]):
            for i, val in enumerate(valeurs):
                acc[i] += val
    return tot, demi, jours


def decision(tot, demi):
    """Décision selon la règle fixée d'avance : rien à adopter tant que la règle n'est pas remplie."""
    base = tot["actuel"]
    if base[0] == 0:
        return "Décision : aucune, pas encore de courses hors échantillon."
    if base[0] < SEUIL_COURSES:
        return "Décision : aucune, il faut %d courses hors échantillon, il y en a %d." % (SEUIL_COURSES, base[0])
    adoptables = []
    for v in VARIANTES[1:]:
        n = tot[v][0]
        if n == 0:
            continue
        dp = tot[v][1] / n - base[1] / base[0]
        dt3 = 100 * (tot[v][3] / n - base[3] / base[0])
        moitie_ok = True
        for h in (0, 1):
            a, b = demi[(v, h)], demi[("actuel", h)]
            if a[0] == 0 or b[0] == 0 or a[1] / a[0] - b[1] / b[0] > 0:
                moitie_ok = False
        if dp <= -0.02 and dt3 >= 2 and moitie_ok:
            adoptables.append(LIBELLES[v])
    if adoptables:
        return "Décision : à adopter, selon la règle fixée d'avance : %s." % ", ".join(adoptables)
    return "Décision : aucune variante ne remplit la règle fixée d'avance."


def bloc_bilan(date, lignes=None):
    """Section du bilan : résultats du jour, cumul hors échantillon et décision."""
    res = enregistrer(date, lignes)
    tot, demi, jours = cumul()
    L = ["", "## 5. Essai hors production : codage du chrono", ""]
    n_jour = res["actuel"][0]
    if n_jour == 0:
        L.append("Pas de course à mesurer ce jour-là.")
    else:
        L.append("Ce jour-là, sur %d courses. Exploratoire : les variantes ont été conçues sur le 8 et le 9 novembre."
                 % n_jour)
        L += ["", "| Variante | Perte du vainqueur | Top 1 | Top 3 |", "|---|---:|---:|---:|"]
        for v in VARIANTES:
            n, p, t1, t3 = res[v]
            if n:
                L.append("| %s | %s | %s %% | %s %% |" % (LIBELLES[v], _fr(p / n, 2), _fr(100 * t1 / n, 1),
                                                         _fr(100 * t3 / n, 1)))
    L += ["", "Hors échantillon (à partir du 10 novembre) : %d courses sur %d jour(s)."
          % (tot["actuel"][0], len(jours))]
    if tot["actuel"][0]:
        L += ["", "| Variante | Perte du vainqueur | Top 1 | Top 3 |", "|---|---:|---:|---:|"]
        for v in VARIANTES:
            n, p, t1, t3 = tot[v]
            if n:
                L.append("| %s | %s | %s %% | %s %% |" % (LIBELLES[v], _fr(p / n, 3), _fr(100 * t1 / n, 1),
                                                         _fr(100 * t3 / n, 1)))
    L += ["", decision(tot, demi)]
    return "\n".join(L) + "\n"
