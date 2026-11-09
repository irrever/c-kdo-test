#!/usr/bin/env python3
"""Mouvement des cotes sur le quinté : cote du gel (une heure avant le départ) et cote au départ.

Une ligne par partant, dans quinte/journal/mouvement.csv (séparateur ;). Une date n'est inscrite qu'une fois :
relancer le même jour remplace ses lignes. La cote du gel vient du pronostic final figé dans le journal ; la cote
au départ vient du registre, une fois le constat passé (rattrapage).

Usage : python3 quinte/mouvement.py AAAA-MM-JJ
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
JOURNAL = os.path.join(HERE, "journal")
CHEMIN = os.path.join(JOURNAL, "mouvement.csv")
CHAMPS = ["date", "r", "c", "numero", "cote_gel", "cote_depart", "arrivee"]


def _nombre(x):
    try:
        v = float(x)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _lire(chemin):
    if not os.path.exists(chemin):
        return []
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def ecrire_jour(lignes, date, chemin=CHEMIN):
    """Remplace les lignes de ce jour dans le fichier, et garde les autres jours."""
    autres = [x for x in _lire(chemin) if x["date"] != date]
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS, delimiter=";")
        w.writeheader()
        w.writerows(sorted(autres + lignes, key=lambda x: (x["date"], int(x["numero"]))))


def lignes_du_jour(date):
    """Les lignes du mouvement pour le quinté du jour. Liste vide si le pronostic final n'est pas figé."""
    import registre
    chemin = os.path.join(JOURNAL, "%s.json" % date)
    if not os.path.exists(chemin):
        return []
    with open(chemin, encoding="utf-8") as f:
        journal = json.load(f)
    final = journal.get("final") or {}
    if not final.get("cotes"):
        return []
    r, c = [int(x) for x in journal["course"].replace("R", "").split("C")]
    gel = {int(k): _nombre(v) for k, v in final["cotes"].items()}
    rows = [l for l in registre.lire() if l["date"] == date and l["r"] == str(r) and l["c"] == str(c)]
    return [{"date": date, "r": r, "c": c, "numero": int(l["numero"]), "cote_gel": gel.get(int(l["numero"])),
             "cote_depart": _nombre(l["cote_depart"]), "arrivee": l["arrivee"] or ""} for l in rows]


def enregistrer(date):
    lignes = lignes_du_jour(date)
    if not lignes:
        return "Rien à inscrire pour %s : pas de pronostic final figé avec les cotes." % date
    ecrire_jour(lignes, date)
    return "Mouvement inscrit pour %s : %d partants." % (date, len(lignes))


def main(argv):
    if len(argv) != 2:
        print("usage : mouvement.py AAAA-MM-JJ")
        return 2
    print(enregistrer(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
