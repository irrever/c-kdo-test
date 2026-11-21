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
import journee as jr  # noqa: E402

SORTIE = os.path.join(HERE, "pronostics")


JOURNAL_DIR = os.path.join(HERE, "journal")


def _figee(date):
    """Page du jour telle qu'elle était au pronostic final : son analyse ne change plus ensuite."""
    return os.path.join(JOURNAL_DIR, "%s-avant-course.html" % date)


def _final_fige(date):
    import suivi
    chemin = suivi._fichier_pronostic(date)
    return os.path.exists(chemin) and "final" in json.load(open(chemin, encoding="utf-8"))


def _fige_le(date):
    """Heure (UTC) à laquelle le pronostic du jour a été figé, ou None."""
    import suivi
    chemin = suivi._fichier_pronostic(date)
    if not os.path.exists(chemin):
        return None
    with open(chemin, encoding="utf-8") as f:
        return json.load(f).get("fige_le")


def _figer(date, page):
    """Garde la page du jour telle qu'elle est : son analyse ne change plus ensuite."""
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    with open(_figee(date), "w", encoding="utf-8") as f:
        f.write(page)


def _avis(date):
    """L'avis combiné enregistré pour ce quinté (sinon rien)."""
    import combine
    return combine.charger(date)


def charger(date, final=False, calculer_journee=False):
    """Télécharge le quinté d'une date et écrit sa page.

    La page affiche le pronostic du soir, figé : il ne change plus, et il n'est pas recalculé avec les cotes.
    Un pronostic final de l'ancienne méthode, s'il a été figé avant le 21 novembre, reste affiché pour l'historique.
    final=True est refusé : le pronostic n'utilise plus les cotes.
    """
    if final:
        raise SystemExit("Pronostic final avec les cotes : supprimé le 21 novembre, le pronostic reste sans cotes.")
    import suivi
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
    suivi.enregistrer_pronostic(date)  # sans effet si le pronostic du soir est déjà figé
    soir, historique = None, None
    chemin_journal = suivi._fichier_pronostic(date)
    if os.path.exists(chemin_journal):
        with open(chemin_journal, encoding="utf-8") as f:
            journal = json.load(f)
        if "final" in journal:
            soir = journal.get("pronostic_soir")
            historique = {"fige_le": journal["final"]["fige_le"], "ordre": journal.get("ordre_predit", []),
                          "noms": {x["numero"]: x["nom"] for x in journal.get("chevaux", [])}}
        else:
            soir = journal
    page = rapport.generer(chemin_brut, journee=jr.charger(date, calculer=calculer_journee),
                           fige_le=(soir or {}).get("fige_le"), avis=_avis(date), soir=soir, final=historique)
    sortie = os.path.join(SORTIE, "%s.html" % date)
    with open(sortie, "w", encoding="utf-8") as f:
        f.write(page)
    print("écrit :", sortie)
    course = eq.course(date, r, c)
    if course and course.get("heure_depart_course"):
        print("depart :", course["heure_depart_course"])
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
    charger(date, calculer_journee=True)
    index()
