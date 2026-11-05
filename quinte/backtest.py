#!/usr/bin/env python3
"""Construit le jeu de données du backtest (quintés passés) et évalue le modèle.

Pour chaque quinté terminé :
- on garde les informations connues AVANT la course uniquement (historique filtré par date,
  notes internes seulement si créées avant la course) ;
- on compare les probabilités du modèle aux arrivées réelles.

Usage :
    python3 quinte/backtest.py build 2026-10-06 2026-11-04   # construit quinte/.cache/dataset.json
    python3 quinte/backtest.py eval                          # évalue les variantes
"""
import datetime as dt
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import equidia as eq  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, ".cache", "dataset.json")
PLACE_SCORE = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.45, 5: 0.3, 6: 0.2, 7: 0.1, 8: 0.1, 9: 0.1}
DECROISSANCE = 0.85
NOTES = ["aptitudes", "forme_cheval", "chronos", "tandem", "conditions", "bruits_ecuries"]


def place_num(texte):
    s = str(texte or "").strip()
    return int(s) if re.fullmatch(r"0*\d+", s) and int(s) > 0 else None


def score_place(texte, nb):
    n = place_num(texte)
    if n is None:
        return 0.0
    return PLACE_SCORE.get(n, 0.0)


def score_musique(musique):
    runs = []
    for year, val, _disc in re.findall(r"\((\d\d)\)|(D|T|A|R|\d+)([a-z]?)", musique or ""):
        if year:
            continue
        runs.append(PLACE_SCORE.get(int(val), 0.0) if val.isdigit() and int(val) > 0 else 0.0)
    recent = runs[:10]
    if not recent:
        return None
    num = sum(s * DECROISSANCE ** i for i, s in enumerate(recent))
    den = sum(DECROISSANCE ** i for i in range(len(recent)))
    return num / den


def build(d_debut, d_fin):
    dates = []
    d = dt.date.fromisoformat(d_debut)
    while d <= dt.date.fromisoformat(d_fin):
        dates.append(d.isoformat())
        d += dt.timedelta(days=1)

    courses = []
    for day in dates:
        q = eq.quinte_du_jour(day)
        if not q:
            continue
        r, c = q
        x = eq.course(day, r, c)
        if not x or x.get("type_statut_course_id") != "finished":
            continue
        arrivees = [p for p in x["partants"] if p.get("statut_part") == "DP" and place_num(p.get("num_place_arrivee"))]
        if len(arrivees) < 5:
            continue
        courses.append((day, r, c, x))
        print("quinté", day, "R%dC%d" % (r, c), x.get("libcourt_prix_course"), file=sys.stderr)

    slugs = []
    for _, _, _, x in courses:
        for p in x["partants"]:
            slugs.append((p.get("cheval") or {}).get("slug"))
    print("fiches à charger :", len({s for s in slugs if s}), file=sys.stderr)
    fiches = eq.fiches_en_parallele(slugs)

    jeu = []
    for day, r, c, x in courses:
        lignes = []
        date_course = x["reunion"]["date_reunion"]
        for p in x["partants"]:
            if p.get("statut_part") != "DP":
                continue
            slug = (p.get("cheval") or {}).get("slug")
            notes = p.get("interne_note_partant") or {}
            cree = (notes.get("note_created_at") or "")[:10]
            note_ok = bool(cree) and cree <= date_course
            hist = fiches.get(slug, [])
            if isinstance(hist, dict):
                hist = []
            hist_avant = [h for h in hist if h.get("date") and h["date"] < date_course]
            lignes.append({
                "numero": p["num_partant"],
                "nom": (p.get("cheval") or {}).get("nom_cheval"),
                "driver": (p.get("monte") or {}).get("nom_monte"),
                "musique": p.get("musique") or (p.get("cheval") or {}).get("musique"),
                "notes": {k: notes.get(k) for k in NOTES} if note_ok else None,
                "historique": hist_avant,
                "arrivee": place_num(p.get("num_place_arrivee")),
            })
        jeu.append({
            "date": date_course,
            "reunion_course": "R%dC%d" % (r, c),
            "hippodrome": x["reunion"]["hippodrome"]["name"],
            "distance": x.get("distance"),
            "corde": x.get("lib_corde_course"),
            "discipline": x.get("discipline"),
            "partants": lignes,
        })

    os.makedirs(os.path.dirname(DATASET), exist_ok=True)
    with open(DATASET, "w", encoding="utf-8") as f:
        json.dump(jeu, f, ensure_ascii=False)
    print("courses retenues :", len(jeu), "->", DATASET)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "build":
        build(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
