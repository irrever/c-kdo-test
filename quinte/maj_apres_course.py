#!/usr/bin/env python3
"""Mise à jour après course, adaptée à l'heure de départ de chaque course.

Usage :
    python3 quinte/maj_apres_course.py                       # aujourd'hui (heure de Paris)
    python3 quinte/maj_apres_course.py --date AAAA-MM-JJ     # une date donnée
    python3 quinte/maj_apres_course.py --maintenant AAAA-MM-JJTHH:MM   # pour tester

Ne fait la mise à jour que si, à la fois :
- le pronostic du jour est figé (journal) et le résultat n'est pas encore enregistré ;
- la course est terminée (arrivée publiée) ;
- l'heure de départ + 1 h est atteinte (heure de Paris).

Affiche une seule ligne d'état commençant par RIEN, ATTENTE ou MISE_A_JOUR.
"""
import datetime as dt
import json
import os
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import equidia as eq  # noqa: E402
import suivi  # noqa: E402
import quinte_du_jour  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")


def _parametres(argv):
    date = None
    maintenant = None
    i = 0
    while i < len(argv):
        if argv[i] == "--date" and i + 1 < len(argv):
            date = argv[i + 1]
            i += 2
        elif argv[i] == "--maintenant" and i + 1 < len(argv):
            maintenant = dt.datetime.fromisoformat(argv[i + 1]).replace(tzinfo=PARIS)
            i += 2
        else:
            raise SystemExit(__doc__)
    if date is None:
        date = dt.datetime.now(PARIS).date().isoformat()
    if maintenant is None:
        maintenant = dt.datetime.now(PARIS)
    return date, maintenant


def _deja_enregistre(date):
    if not os.path.exists(os.path.join(suivi.JOURNAL, "bilan.csv")):
        return False
    import csv
    with open(os.path.join(suivi.JOURNAL, "bilan.csv"), encoding="utf-8") as f:
        return any(x["date"] == date for x in csv.DictReader(f, delimiter=";"))


def _en_attente(chemin):
    """Nombre de rapports encore marqués « pas encore publié » dans la page (None si la page n'existe pas)."""
    if not os.path.exists(chemin):
        return None
    with open(chemin, encoding="utf-8") as f:
        return f.read().count("pas encore publié")


def _rafraichir_suivant(date):
    """Le quinté du lendemain reprend le dernier quinté couru : si sa page existe, on la régénère."""
    suivant = (dt.date.fromisoformat(date) + dt.timedelta(days=1)).isoformat()
    page = os.path.join(quinte_du_jour.SORTIE, "%s.html" % suivant)
    if os.path.exists(suivi._fichier_pronostic(suivant)) and os.path.exists(page):
        quinte_du_jour.charger(suivant)


def _depart(date, heure):
    return dt.datetime.fromisoformat("%sT%s" % (date, heure)).replace(tzinfo=PARIS)


def main(argv):
    date, maintenant = _parametres(argv)
    chemin_journal = suivi._fichier_pronostic(date)
    if not os.path.exists(chemin_journal):
        print("RIEN : pas de pronostic figé pour %s" % date)
        return
    deja = _deja_enregistre(date)
    with open(chemin_journal, encoding="utf-8") as f:
        journal = json.load(f)
    r, c = [int(x) for x in journal["course"].replace("R", "").split("C")]
    course = eq.course(date, r, c, fresh=True)
    if not course:
        print("ATTENTE : page de la course %s introuvable" % journal["course"])
        return
    heure = course.get("heure_depart_course")
    if course.get("type_statut_course_id") != "finished":
        # Pronostic final : figé avec les cotes une heure avant le départ, une seule fois.
        if heure and "final" not in journal:
            depart = _depart(date, heure)
            if depart - dt.timedelta(hours=1) <= maintenant < depart:
                try:
                    quinte_du_jour.charger(date, final=True)
                except SystemExit as e:
                    # Pas encore de cotes pour cette course : le passage suivant réessaiera.
                    print("ATTENTE : pronostic final pas encore figé pour %s (%s)" % (date, e))
                    return
                quinte_du_jour.index()
                print("FINAL : pronostic figé avec les cotes pour %s (départ %s)" % (date, heure))
                return
        print("ATTENTE : course %s pas encore terminée (statut %s)" % (
            journal["course"], course.get("type_statut_course_id")))
        return
    if not heure:
        print("ATTENTE : heure de départ inconnue pour %s" % journal["course"])
        return
    seuil = _depart(date, heure) + dt.timedelta(hours=1)
    if maintenant < seuil:
        print("ATTENTE : départ à %s, mise à jour à partir de %s" % (heure, seuil.strftime("%H:%M")))
        return
    page = os.path.join(quinte_du_jour.SORTIE, "%s.html" % date)
    if deja:
        # Résultat déjà enregistré : la page n'est reprise que si des rapports officiels viennent de paraître.
        avant = _en_attente(page)
        if avant == 0:
            print("RIEN : résultat et rapports déjà complets pour %s" % date)
            return
        quinte_du_jour.charger(date)
        apres = _en_attente(page)
        if apres is None or (avant is not None and apres >= avant):
            print("RIEN : résultat déjà enregistré, rapports officiels toujours en attente pour %s" % date)
            return
        _rafraichir_suivant(date)
        quinte_du_jour.index()
        print("MISE_A_JOUR : %s, rapports officiels publiés (%d en attente, au lieu de %s)" % (
            date, apres, avant if avant is not None else "aucun"))
        return
    ligne = suivi.enregistrer_resultat(date)
    if ligne is None:
        print("RIEN : arrivée incomplète pour %s" % date)
        return
    quinte_du_jour.charger(date)  # régénère la page du jour
    _rafraichir_suivant(date)     # reprend ses résultats sur la page du lendemain, si elle existe
    quinte_du_jour.index()        # puis la page d'accueil, qui reprend la plus récente
    print("MISE_A_JOUR : %s, départ %s, arrivée %s" % (date, heure, ligne["ordre_reel"]))


if __name__ == "__main__":
    main(sys.argv[1:])
