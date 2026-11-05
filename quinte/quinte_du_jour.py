#!/usr/bin/env python3
"""Charge automatiquement le quinté du jour et écrit sa page d'analyse.

Usage :
    python3 quinte/quinte_du_jour.py              # aujourd'hui (date du système)
    python3 quinte/quinte_du_jour.py 2026-11-05   # une date donnée

Sortie : quinte/pronostics/AAAA-MM-JJ.html, plus un index.html qui liste les pages.
"""
import datetime as dt
import glob
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import equidia as eq  # noqa: E402
import rapport  # noqa: E402

SORTIE = os.path.join(HERE, "pronostics")


def charger(date):
    q = eq.quinte_du_jour(date)
    if not q:
        raise SystemExit("Aucun quinté trouvé pour %s." % date)
    r, c = q
    url = "%s/courses/%s/R%d/C%d" % (eq.BASE, date, r, c)
    page_brute = eq.get_html(url)
    os.makedirs(SORTIE, exist_ok=True)
    chemin_brut = os.path.join(eq.CACHE, "course-%s-R%dC%d.html" % (date, r, c))
    with open(chemin_brut, "w", encoding="utf-8") as f:
        f.write(page_brute)
    sortie = os.path.join(SORTIE, "%s.html" % date)
    with open(sortie, "w", encoding="utf-8") as f:
        f.write(rapport.generer(chemin_brut))
    print("écrit :", sortie)
    return sortie


def index():
    pages = sorted(glob.glob(os.path.join(SORTIE, "????-??-??.html")), reverse=True)
    lignes = "".join('<li><a href="%s">%s</a></li>' % (os.path.basename(p), os.path.basename(p)[:-5]) for p in pages)
    corps = ("<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
             "<meta name='viewport' content='width=device-width, initial-scale=1'>"
             "<title>Quintés analysés</title></head><body style='font:16px system-ui;padding:16px'>"
             "<h1>Quintés analysés</h1><ul>%s</ul></body></html>" % lignes)
    with open(os.path.join(SORTIE, "index.html"), "w", encoding="utf-8") as f:
        f.write(corps)


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    charger(date)
    index()
