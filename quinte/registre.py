#!/usr/bin/env python3
"""Registre des pronostics : une ligne par cheval et par course, figée avant le départ.

Chaque course qui n'est pas encore partie au moment du calcul de la journée reçoit une ligne par partant :
les données de la course (poids, corde, distance, discipline, nombre de partants), les sept notes du modèle,
la note finale, les probabilités, et la cote si elle existe déjà. Quand la course est terminée, la place de
chaque cheval est ajoutée. Le registre sert aux analyses (quinte/analyse_registre.py) : le modèle et ses
réglages peuvent être vérifiés sur des centaines de courses, et non plus sur un seul quinté par jour.

Fichier : quinte/journal/registre.csv (séparateur ;). Une course n'y entre qu'une fois.
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CHEMIN = os.path.join(HERE, "journal", "registre.csv")
SEP = ";"
NOTES = ["musique", "aptitudes", "forme_cheval", "chronos", "tandem", "conditions", "bruits_ecuries"]
CHAMPS = (["date", "calcule_le", "r", "c", "hippodrome", "heure", "discipline", "distance", "partants",
           "numero", "nom", "monte", "poids", "corde", "musique_texte"]
          + ["n_" + n for n in NOTES]
          + ["score", "rang", "p_victoire", "p_top3", "cote", "arrivee", "cote_depart", "heure_cote", "sans_donnees",
           "rapport_gagnant", "rapport_place"])


def _lire(chemin):
    if not os.path.exists(chemin):
        return []
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=SEP))


def _ecrire(lignes, chemin):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS, delimiter=SEP)
        w.writeheader()
        w.writerows(lignes)


def _vide(v):
    return "" if v is None else v


def lignes_de_course(date, r, c, course, lignes, probs, cotes, calcule_le, sans_donnees=False):
    """Lignes du registre pour une course pas encore partie : une par partant, dans l'ordre du modèle."""
    reunion = course.get("reunion") or {}
    par_numero = {p["num_partant"]: p for p in course.get("partants", [])}
    sortie = []
    for rang, l in enumerate(lignes, start=1):
        p = par_numero.get(l["numero"], {})
        poids = p.get("pds_calc_hand_partant")
        corde = p.get("place_corde_partant")
        notes = l.get("composantes") or {}
        ligne = {
            "date": date, "calcule_le": calcule_le, "r": r, "c": c,
            "hippodrome": (reunion.get("hippodrome") or {}).get("name") or "",
            "heure": _vide(course.get("heure_depart_course")),
            "discipline": _vide(course.get("discipline")),
            "distance": _vide(course.get("distance")),
            "partants": len(lignes),
            "numero": l["numero"],
            "nom": l["nom"],
            "monte": _vide(l.get("driver")),
            "poids": poids if poids else "",    # absent ou nul : pas de poids (trot)
            "corde": corde if corde else "",
            "musique_texte": _vide(l.get("musique")),
            "score": round(l["score"], 6),
            "rang": rang,
            "p_victoire": round(probs["victoire"][l["numero"]], 4),
            "p_top3": round(probs["top3"][l["numero"]], 4),
            "cote": _vide((cotes or {}).get(l["numero"])),
            "arrivee": "",
            "sans_donnees": "1" if sans_donnees else "",
        }
        for n in NOTES:
            v = notes.get(n)
            ligne["n_" + n] = "" if v is None else round(v, 6)
        sortie.append(ligne)
    return sortie


def ajouter(nouvelles, chemin=CHEMIN):
    """Ajoute au registre les courses qui n'y sont pas encore. Renvoie le nombre de lignes ajoutées."""
    existantes = _lire(chemin)
    connues = {(x["date"], x["r"], x["c"]) for x in existantes}
    a_ajouter = [x for x in nouvelles if (str(x["date"]), str(x["r"]), str(x["c"])) not in connues]
    if a_ajouter:
        _ecrire(existantes + a_ajouter, chemin)
    return len(a_ajouter)


def mettre_a_jour_arrivees(date, r, c, places, chemin=CHEMIN):
    """Inscrit la place de chaque partant d'une course terminée (places : numéro -> place).
    Renvoie le nombre de lignes modifiées."""
    lignes = _lire(chemin)
    modifiees = 0
    for x in lignes:
        if (x["date"], x["r"], x["c"]) == (str(date), str(r), str(c)):
            numero = int(x["numero"])
            nouvelle = str(places[numero]) if numero in places else ""
            if x["arrivee"] != nouvelle:
                x["arrivee"] = nouvelle
                modifiees += 1
    if modifiees:
        _ecrire(lignes, chemin)
    return modifiees


def marquer_sans_donnees(date, r, c, chemin=CHEMIN):
    """Marque une course où le modèle n'avait rien à départager : elle sort des comparaisons du modèle.
    Renvoie le nombre de lignes marquées."""
    lignes = _lire(chemin)
    modifiees = 0
    for x in lignes:
        if (x["date"], x["r"], x["c"]) == (str(date), str(r), str(c)) and x.get("sans_donnees") != "1":
            x["sans_donnees"] = "1"
            modifiees += 1
    if modifiees:
        _ecrire(lignes, chemin)
    return modifiees


def capturer_cotes(date, r, c, cotes, heure, chemin=CHEMIN):
    """Inscrit les cotes relevées juste avant le départ d'une course (numéro -> rapport) et l'heure du relevé.
    Chaque relevé remplace le précédent : seul compte le dernier, celui d'avant le départ."""
    lignes = _lire(chemin)
    modifiees = 0
    for x in lignes:
        if (x["date"], x["r"], x["c"]) == (str(date), str(r), str(c)):
            numero = int(x["numero"])
            if numero in cotes:
                x["cote_depart"] = str(cotes[numero])
                x["heure_cote"] = heure
                modifiees += 1
    if modifiees:
        _ecrire(lignes, chemin)
    return modifiees


def completer_cotes(date, r, c, cotes, chemin=CHEMIN):
    """Complète une course terminée dont aucune cote n'a été relevée avant le départ : la dernière cote de départ,
    relue après la course, est inscrite avec heure_cote « reprise ». Une course déjà relevée n'est pas touchée.
    Renvoie le nombre de lignes complétées."""
    lignes = _lire(chemin)
    de_la_course = [x for x in lignes if (x["date"], x["r"], x["c"]) == (str(date), str(r), str(c))]
    if not de_la_course or any(x.get("cote_depart") for x in de_la_course):
        return 0
    completees = 0
    for x in de_la_course:
        numero = int(x["numero"])
        if numero in cotes:
            x["cote_depart"] = str(cotes[numero])
            x["heure_cote"] = "reprise"
            completees += 1
    if completees:
        _ecrire(lignes, chemin)
    return completees


def inscrire_rapports(date, r, c, rapports, chemin=CHEMIN):
    """Inscrit les rapports officiels d'une course terminée, pour 1 € misé : le simple gagnant (au vainqueur) et le
    simple placé (aux trois premiers). rapports : {"gagnant": {numero: rapport}, "place": {numero: rapport}}.
    Renvoie le nombre de lignes modifiées."""
    lignes = _lire(chemin)
    modifiees = 0
    for x in lignes:
        if (x["date"], x["r"], x["c"]) != (str(date), str(r), str(c)):
            continue
        numero = int(x["numero"])
        valeurs = {"rapport_gagnant": rapports.get("gagnant", {}).get(numero),
                   "rapport_place": rapports.get("place", {}).get(numero)}
        for champ, v in valeurs.items():
            texte = "" if v is None else str(v)
            if x.get(champ, "") != texte:
                x[champ] = texte
                modifiees += 1
    if modifiees:
        _ecrire(lignes, chemin)
    return modifiees


def lire(chemin=CHEMIN):
    """Toutes les lignes du registre, valeurs en texte."""
    return _lire(chemin)
