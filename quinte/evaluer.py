#!/usr/bin/env python3
"""Évalue les variantes du modèle sur le jeu de données du backtest.

Usage : python3 quinte/evaluer.py [chemin_dataset.json]

Métriques (sur les courses passées, uniquement avec les infos disponibles avant course) :
- Brier top 3 : erreur quadratique entre probabilité d'être dans le top 3 et résultat ;
- log-loss gagnant : -log(probabilité attribuée au vainqueur réel) ;
- rappel top 3 : part des 3 premiers réels présents dans les 3 premiers prédits ;
- taux de réussite du favori du modèle (vainqueur).
Sensibilité : variation de K (netteté des probabilités).
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import score_musique, score_place, DECROISSANCE, DATASET  # noqa: E402

NOTES_POIDS = {"aptitudes": 0.25, "forme_cheval": 0.25, "chronos": 0.20, "tandem": 0.10,
               "conditions": 0.10, "bruits_ecuries": 0.10}
K_DEFAUT = 6.0
SIMS = 20000


def note_equidia(notes):
    if not notes:
        return None
    tot = poids = 0.0
    for k, w in NOTES_POIDS.items():
        v = notes.get(k)
        if v is None:
            continue
        tot += w * float(v)
        poids += w
    return tot / poids if poids else None


def forme_historique(hist, date_course, nb_max=8):
    """Forme sur l'historique passé (pondérée par la récence)."""
    runs = sorted([h for h in hist if h.get("date") and h["date"] < date_course],
                  key=lambda h: h["date"], reverse=True)[:nb_max]
    if not runs:
        return None
    num = den = 0.0
    for i, h in enumerate(runs):
        w = DECROISSANCE ** i
        num += w * score_place(h.get("place_texte"), h.get("nb_partants"))
        den += w
    return num / den


def correspondance(hist, date_course, cle, valeur, test):
    """Score moyen des courses passées qui correspondent à un critère (hippodrome, distance, corde)."""
    vals = [score_place(h.get("place_texte"), h.get("nb_partants")) for h in hist
            if h.get("date") and h["date"] < date_course and test(h)]
    return sum(vals) / len(vals) if vals else None


def preparer(course, stats_driver):
    """Construit les variables pour chaque partant d'une course."""
    rows = []
    date = course["date"]
    for p in course["partants"]:
        hist = p["historique"]
        mus = score_musique(p["musique"])
        notes = note_equidia(p["notes"])
        forme = forme_historique(hist, date)
        hippo = correspondance(hist, date, "hippo", course["hippodrome"],
                               lambda h: h.get("hippodrome") == course["hippodrome"])
        dist = correspondance(hist, date, "dist", course["distance"],
                              lambda h: h.get("distance") and course["distance"] and abs(int(h["distance"]) - int(course["distance"])) <= 150)
        drv = stats_driver.get(p["driver"])
        drv_score = drv if drv is not None else None
        rows.append({"numero": p["numero"], "arrivee": p["arrivee"], "musique": mus, "notes": notes,
                     "forme": forme, "hippo": hippo, "dist": dist, "driver": drv_score})
    return rows


def stats_driver_avant(course_date, entrees, k_prior=5.0):
    """Forme du driver : moyenne des places passées (historique des chevaux de la course, avant la date),
    lissée vers 0,5 avec k_prior courses fictives."""
    acc = {}
    for drv, date, sc in entrees:
        if date < course_date:
            s, n = acc.get(drv, (0.0, 0))
            acc[drv] = (s + sc, n + 1)
    return {d: (s + k_prior * 0.5) / (n + k_prior) for d, (s, n) in acc.items()}


def score_variante(row, variante):
    """Score brut (échelle 0..1) selon la variante."""
    def v(x, repli):
        return repli if x is None else x
    if variante == "musique":
        return v(row["musique"], 0.5)
    if variante == "notes":
        return v(row["notes"], v(row["musique"], 0.5))
    if variante == "combine":
        parts = [(0.30, v(row["musique"], 0.5)), (0.70, v(row["notes"], 0.5))]
        return sum(w * x for w, x in parts)
    if variante == "combine+historique":
        parts = [(0.25, v(row["musique"], 0.5)), (0.45, v(row["notes"], 0.5)),
                 (0.15, v(row["forme"], 0.5)), (0.05, v(row["hippo"], 0.5)),
                 (0.05, v(row["dist"], 0.5)), (0.05, v(row["driver"], 0.5))]
        return sum(w * x for w, x in parts)
    raise ValueError(variante)


def probas_top3(scores, k, rng):
    """Probabilité d'être dans le top 3 et d'être vainqueur, par simulation Plackett-Luce."""
    m = max(scores)
    w = [math.exp(k * (s - m)) for s in scores]
    top3 = [0] * len(scores)
    win = [0] * len(scores)
    n = len(scores)
    for _ in range(SIMS):
        rest = list(range(n))
        for pos in range(min(3, n)):
            tot = sum(w[i] for i in rest)
            r = rng.random() * tot
            acc = 0.0
            for i in rest:
                acc += w[i]
                if acc >= r:
                    if pos == 0:
                        win[i] += 1
                    top3[i] += 1
                    rest.remove(i)
                    break
    return [t / SIMS for t in top3], [x / SIMS for x in win]


def evaluer(courses, variante, k, rng):
    brier = ll = rappel = 0.0
    favoris = 0
    n_courses = 0
    for c in courses:
        rows = c["lignes"]
        scores = [score_variante(r, variante) for r in rows]
        p3, pw = probas_top3(scores, k, rng)
        reels = sorted([r for r in rows if r["arrivee"]], key=lambda r: r["arrivee"])
        if len(reels) < 3:
            continue
        idx = {r["numero"]: i for i, r in enumerate(rows)}
        vainqueur = reels[0]["numero"]
        for i, r in enumerate(rows):
            y = 1.0 if (r["arrivee"] and r["arrivee"] <= 3) else 0.0
            brier += (p3[i] - y) ** 2
        ll += -math.log(max(pw[idx[vainqueur]], 1e-6))
        top3_pred = {rows[i]["numero"] for i in sorted(range(len(rows)), key=lambda i: -p3[i])[:3]}
        rappel += len(top3_pred & {r["numero"] for r in reels[:3]}) / 3
        favori = max(range(len(rows)), key=lambda i: pw[i])
        favoris += 1 if rows[favori]["numero"] == vainqueur else 0
        n_courses += 1
    n_chevaux = sum(len(c["lignes"]) for c in courses)
    return {"brier_top3": brier / n_chevaux, "logloss_gagnant": ll / n_courses,
            "rappel_top3": rappel / n_courses, "favori_gagne": favoris / n_courses, "courses": n_courses}


def main(chemin):
    with open(chemin, encoding="utf-8") as f:
        brut = json.load(f)
    # Entrées (driver, date, place) de toutes les courses passées des chevaux du jeu de données
    entrees = []
    for c in brut:
        for p in c["partants"]:
            for h in p["historique"]:
                if h.get("driver") and h.get("date") and h.get("place_texte") is not None:
                    entrees.append((h["driver"], h["date"], score_place(h.get("place_texte"), h.get("nb_partants"))))
    courses = []
    for c in brut:
        stats = stats_driver_avant(c["date"], entrees)
        rows = preparer(c, stats)
        courses.append({"date": c["date"], "hippodrome": c["hippodrome"], "distance": c["distance"],
                        "partants": c["partants"], "lignes": rows})
    print("courses : %d, chevaux : %d" % (len(courses), sum(len(c["lignes"]) for c in courses)))
    print("%-24s %-8s %-12s %-14s %-12s" % ("variante", "K", "Brier top3", "log-loss gagn.", "rappel top3"))
    rng = random.Random(1)
    for variante in ["musique", "notes", "combine", "combine+historique"]:
        for k in [2.0, 4.0, 6.0, 8.0, 10.0]:
            r = evaluer(courses, variante, k, rng)
            print("%-24s %-8.1f %-12.4f %-14.4f %-12.3f" % (variante, k, r["brier_top3"], r["logloss_gagnant"], r["rappel_top3"]))
    # Référence sans information : probabilité constante 3/n d'être dans le top 3, 1/n de gagner
    n_moy = sum(len(c["lignes"]) for c in courses) / len(courses)
    p0 = 3 / n_moy
    print("référence sans information : Brier top3 = %.4f, log-loss gagnant = %.4f" % (
        p0 * (1 - p0), math.log(n_moy)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DATASET)
