#!/usr/bin/env python3
"""Mise à jour après course, adaptée à l'heure de départ de chaque course.

Usage :
    python3 quinte/maj_apres_course.py                       # aujourd'hui (heure de Paris)
    python3 quinte/maj_apres_course.py --date AAAA-MM-JJ     # une date donnée
    python3 quinte/maj_apres_course.py --maintenant AAAA-MM-JJTHH:MM   # pour tester

Pour le quinté du jour :
- une heure avant le départ, tant que le pronostic final n'est pas figé, le pronostic final est figé avec les cotes ;
- une fois la course terminée et l'heure de départ + 1 h atteinte, le résultat est enregistré et la page reprise.
Pour toute la journée, les arrivées sont mises à jour dès qu'elles sont connues.

Affiche une ligne d'état commençant par RIEN, ATTENTE, FINAL ou MISE_A_JOUR.
"""
import csv
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
import journee  # noqa: E402

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


def _statut_quinte(date, maintenant):
    """Traite le quinté du jour et renvoie la ligne d'état."""
    chemin_journal = suivi._fichier_pronostic(date)
    if not os.path.exists(chemin_journal):
        return "RIEN : pas de pronostic figé pour %s" % date
    deja = _deja_enregistre(date)
    with open(chemin_journal, encoding="utf-8") as f:
        journal = json.load(f)
    r, c = [int(x) for x in journal["course"].replace("R", "").split("C")]
    try:
        course = eq.course(date, r, c, fresh=True)
    except Exception as e:
        return "ATTENTE : données Equidia indisponibles pour %s (%s)" % (date, e)
    if not course:
        return "ATTENTE : page de la course %s introuvable" % journal["course"]
    heure = course.get("heure_depart_course")
    if course.get("type_statut_course_id") != "finished":
        # Pronostic final : figé avec les cotes une heure avant le départ, une seule fois.
        if heure and "final" not in journal:
            depart = _depart(date, heure)
            if depart - dt.timedelta(hours=1) <= maintenant < depart:
                try:
                    quinte_du_jour.charger(date, final=True)
                except SystemExit as e:
                    return "ATTENTE : pronostic final pas encore figé pour %s (%s)" % (date, e)
                quinte_du_jour.index()
                return "FINAL : pronostic figé avec les cotes pour %s (départ %s)" % (date, heure)
        return "ATTENTE : course %s pas encore terminée (statut %s)" % (
            journal["course"], course.get("type_statut_course_id"))
    if not heure:
        return "ATTENTE : heure de départ inconnue pour %s" % journal["course"]
    seuil = _depart(date, heure) + dt.timedelta(hours=1)
    if maintenant < seuil:
        return "ATTENTE : départ à %s, mise à jour à partir de %s" % (heure, seuil.strftime("%H:%M"))
    page = os.path.join(quinte_du_jour.SORTIE, "%s.html" % date)
    if deja:
        # Résultat déjà enregistré : la page n'est reprise que si des rapports officiels viennent de paraître.
        avant = _en_attente(page)
        if avant == 0:
            return "RIEN : résultat et rapports déjà complets pour %s" % date
        quinte_du_jour.charger(date)
        apres = _en_attente(page)
        if apres is None or (avant is not None and apres >= avant):
            return "RIEN : résultat déjà enregistré, rapports officiels toujours en attente pour %s" % date
        _rafraichir_suivant(date)
        quinte_du_jour.index()
        return "MISE_A_JOUR : %s, rapports officiels publiés (%d en attente, au lieu de %s)" % (
            date, apres, avant if avant is not None else "aucun")
    ligne = suivi.enregistrer_resultat(date)
    if ligne is None:
        return "RIEN : arrivée incomplète pour %s" % date
    quinte_du_jour.charger(date)  # régénère la page du jour
    _rafraichir_suivant(date)     # reprend ses résultats sur la page du lendemain, si elle existe
    quinte_du_jour.index()        # puis la page d'accueil, qui reprend la plus récente
    return "MISE_A_JOUR : %s, départ %s, arrivée %s" % (date, heure, ligne["ordre_reel"])


def main(argv):
    date, maintenant = _parametres(argv)
    arrivees = False
    cotes = 0
    if os.path.exists(suivi._fichier_pronostic(date)):
        arrivees = journee.rafraichir_arrivees(date, maintenant)
        try:
            cotes = journee.capturer_cotes_proches(date, maintenant)
        except Exception as e:
            print("AVERTISSEMENT : cotes avant départ non relevées : %s" % e)
        try:
            journee.rafraichir_cotes_sans_donnees(date, maintenant)
        except Exception as e:
            print("AVERTISSEMENT : cotes des courses sans pronostic non relevées : %s" % e)
    ligne = _statut_quinte(date, maintenant)
    if arrivees and not ligne.startswith(("FINAL", "MISE_A_JOUR")):
        # Des courses de la journée viennent de se terminer : la page est reprise avec leurs arrivées.
        quinte_du_jour.charger(date)
        quinte_du_jour.index()
        ligne = "MISE_A_JOUR : arrivées de la journée mises à jour pour %s" % date
    if cotes and not ligne.startswith(("FINAL", "MISE_A_JOUR")):
        ligne = "MISE_A_JOUR : cotes relevées avant départ pour %d course(s) de %s" % (cotes, date)
    print(ligne)


if __name__ == "__main__":
    main(sys.argv[1:])
