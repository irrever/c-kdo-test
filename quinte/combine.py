#!/usr/bin/env python3
"""Notre avis combiné : notre modèle en production, confronté à la logique de la presse, pour un quinté.

Règles fixées à l'avance (aucune n'est ajustée sur les résultats) :
- Notre classement : le modèle en production (analyse_equidia.analyser).
- Dernière course : la première place de la musique. « Forte » si 1re, 2e ou 3e ; « excusée » si c'est un incident
  (D, T, A, R).
- « Retenu » : dans la boîte « Parier avec » de la presse, ou dans son pronostic à 5.
- « À jouer » : dernière course forte, et écarté par la presse.
- « À éviter en base » : retenu par la presse, dernière course hors des 4 premières (ou non placé), non excusée.
- Boîte de 6 : notre top 5 (sauf « à éviter »), puis les « à jouer » par notre rang, puis le reste de notre rang.
Sans sélection de la presse, la boîte est notre top 6.

Écrit quinte/journal/avis-AAAA-MM-JJ.json.
Usage : python3 quinte/combine.py AAAA-MM-JJ   (après presse.py capturer, pour que la presse soit prise en compte)
"""
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
JOURNAL = os.path.join(HERE, "journal")
TAILLE_BOITE = 6
CATEGORIES = [("bases", "base"), ("belles", "belle"), ("outsiders", "outsider"), ("delaisses", "délaissé")]


def chemin(date):
    return os.path.join(JOURNAL, "avis-%s.json" % date)


def derniere_course(musique):
    """(place de la dernière course, excusée). La place est None s'il n'y a pas de course, ou s'il s'agit d'un incident."""
    runs = [v for y, v, d in re.findall(r"\((\d\d)\)|(D|T|A|R|\d+)([a-z]?)", musique or "") if not y]
    if not runs:
        return None, False
    v = runs[0]
    if v.isdigit():
        return int(v), False          # 0 = non placé
    return None, True                 # incident : excusé


def categories(presse):
    return {n: nom for cle, nom in CATEGORIES for n in presse.get(cle) or []}


def avis(lignes, presse=None, probas_top5=None):
    """Notre avis combiné. lignes : sortie de analyse_equidia.analyser ; presse : le dictionnaire « presse » du journal."""
    ordre = [int(l["numero"]) for l in lignes]
    rang = {n: i + 1 for i, n in enumerate(ordre)}
    info = {}
    for l in lignes:
        n = int(l["numero"])
        pos, excusee = derniere_course(l.get("musique"))
        info[n] = {"numero": n, "nom": l["nom"], "rang": rang[n], "pos": pos, "excusee": excusee,
                   "forte": pos in (1, 2, 3),
                   "top5": round(probas_top5[n], 4) if probas_top5 else None}
    if presse is None:
        box = ordre[:TAILLE_BOITE]
        retenus, cat, a_jouer, a_eviter = None, {}, [], []
    else:
        retenus = set(presse.get("parier") or presse.get("cinq") or [])
        cat = categories(presse)
        a_jouer = [n for n in ordre if info[n]["forte"] and n not in retenus]
        a_eviter = [n for n in ordre if n in retenus and info[n]["pos"] is not None
                    and (info[n]["pos"] == 0 or info[n]["pos"] >= 4) and not info[n]["excusee"]]
        box = [n for n in ordre[:5] if n not in a_eviter]
        for n in a_jouer + ordre:
            if len(box) >= TAILLE_BOITE:
                break
            if n not in box and n not in a_eviter:
                box.append(n)
        box = box[:TAILLE_BOITE]
    lignes_out = [dict(info[n], categorie=cat.get(n, "—"), retenu=(retenus is not None and n in retenus))
                  for n in ordre]
    return {"box": box, "top5": ordre[:5], "a_jouer": a_jouer, "a_eviter": a_eviter,
            "presse_disponible": presse is not None, "lignes": lignes_out}


def enregistrer(date, r, c, lignes, presse, probas_top5, hippodrome, heure):
    donnees = dict(avis(lignes, presse, probas_top5), date=date, r=r, c=c, hippodrome=hippodrome,
                   heure_depart=heure,
                   fige_le_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    os.makedirs(JOURNAL, exist_ok=True)
    with open(chemin(date), "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return donnees


def charger(date):
    """L'avis enregistré pour un quinté, ou None."""
    if not os.path.exists(chemin(date)):
        return None
    with open(chemin(date), encoding="utf-8") as f:
        return json.load(f)


def main(argv):
    if len(argv) != 2:
        print("usage : combine.py AAAA-MM-JJ")
        return 2
    date = argv[1]
    import equidia as eq
    import analyse_equidia as ae
    q = eq.quinte_du_jour(date)
    if not q:
        print("Aucun quinté trouvé pour %s." % date)
        return 1
    r, c = q
    course = eq.course(date, r, c, fresh=True)
    lignes = ae.analyser(course)
    probas = ae.probabilites(ae.simuler(lignes), lignes)["top5"]
    presse = None
    chemin_presse = os.path.join(JOURNAL, "presse-%s.json" % date)
    if os.path.exists(chemin_presse):
        with open(chemin_presse, encoding="utf-8") as f:
            presse = json.load(f)["presse"]
    hippodrome = ((course.get("reunion") or {}).get("hippodrome") or {}).get("name")
    d = enregistrer(date, r, c, lignes, presse, probas, hippodrome, course.get("heure_depart_course"))
    print("Avis enregistré : %s · boîte de %d : %s" % (chemin(date), len(d["box"]),
                                                      " · ".join(map(str, d["box"]))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
