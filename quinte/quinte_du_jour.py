#!/usr/bin/env python3
"""Charge automatiquement le quinté du jour et écrit sa page d'analyse.

Usage :
    python3 quinte/quinte_du_jour.py              # aujourd'hui (date du système)
    python3 quinte/quinte_du_jour.py 2026-11-05   # une date donnée

Sortie : quinte/pronostics/AAAA-MM-JJ.html, plus un index.html qui liste les pages.
"""
import datetime as dt
import glob
import json
import shutil
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import equidia as eq  # noqa: E402
import rapport  # noqa: E402

SORTIE = os.path.join(HERE, "pronostics")


def _heure_depart(date, r, c):
    """Heure de départ de la course (HH:MM, heure de Paris), lue dans les données de la course."""
    course = eq.course(date, r, c, fresh=True)
    return course.get("heure_depart_course") if course else None


JOURNAL_DIR = os.path.join(HERE, "journal")


def _figee(date):
    """Page du jour telle qu'elle était au pronostic final : son analyse ne change plus ensuite."""
    return os.path.join(JOURNAL_DIR, "%s-avant-course.html" % date)


def _final_fige(date):
    import suivi
    chemin = suivi._fichier_pronostic(date)
    return os.path.exists(chemin) and "final" in json.load(open(chemin, encoding="utf-8"))


def charger(date, final=False):
    """Télécharge le quinté d'une date et écrit sa page.

    final=True : fige le pronostic avec les cotes du moment et garde cette analyse telle quelle.
    Sinon : si l'analyse est figée, la page la reprend, avec le résultat du moment.
    """
    q = eq.quinte_du_jour(date)
    if not q:
        raise SystemExit("Aucun quinté trouvé pour %s." % date)
    r, c = q
    url = "%s/courses/%s/R%d/C%d" % (eq.BASE, date, r, c)
    page_brute = eq.get_html(url, fresh=True)
    os.makedirs(SORTIE, exist_ok=True)
    chemin_brut = os.path.join(eq.CACHE, "course-%s-R%dC%d.html" % (date, r, c))
    with open(chemin_brut, "w", encoding="utf-8") as f:
        f.write(page_brute)
    import suivi
    if final:
        suivi.enregistrer_pronostic(date)
        suivi.enregistrer_final(date)
    page = rapport.generer(chemin_brut, avec_cotes=_final_fige(date))
    if not final and os.path.exists(_figee(date)):
        with open(_figee(date), encoding="utf-8") as f:
            page = rapport.fusionner_resultat(f.read(), page)
    if final:
        os.makedirs(JOURNAL_DIR, exist_ok=True)
        with open(_figee(date), "w", encoding="utf-8") as f:
            f.write(page)
    sortie = os.path.join(SORTIE, "%s.html" % date)
    with open(sortie, "w", encoding="utf-8") as f:
        f.write(page)
    print("écrit :", sortie)
    depart = _heure_depart(date, r, c)
    if depart:
        print("depart :", depart)
    if not final:
        suivi.enregistrer_pronostic(date)  # fige le pronostic du soir, sans cotes, s'il ne l'est pas déjà
    return sortie


def index():
    """Page d'accueil : le pronostic le plus récent, directement (les jours précédents restent dans le dépôt)."""
    pages = sorted(glob.glob(os.path.join(SORTIE, "????-??-??.html")), reverse=True)
    if not pages:
        return
    shutil.copyfile(pages[0], os.path.join(SORTIE, "index.html"))
    open(os.path.join(SORTIE, ".nojekyll"), "w").close()


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    charger(date)
    index()
