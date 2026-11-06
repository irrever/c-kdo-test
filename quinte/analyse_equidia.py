#!/usr/bin/env python3
"""Analyse d'une course Equidia (quinté) à partir d'une page enregistrée.

Usage :
    curl -sS -o course.html "https://www.equidia.fr/courses/AAAA-MM-JJ/R1/C1"
    python3 quinte/analyse_equidia.py course.html

Les cotes (cote_*, rapports, enjeux) ne sont jamais lues.
Sortie : tableau des notes, probabilités d'arrivée (Monte Carlo) et jeu conseillé.
"""
import itertools
import json
import math
import random
import re
import sys

# Poids des critères (somme = 1). Musique (performances passées) : 40 %, notes Equidia : 60 %.
# Choisis sur 48 courses terminées (octobre-novembre 2026) : la musique améliore la perte du vainqueur.
POIDS = {
    "musique": 0.40,
    "aptitudes": 0.15,
    "forme_cheval": 0.15,
    "chronos": 0.12,
    "tandem": 0.06,
    "conditions": 0.06,
    "bruits_ecuries": 0.06,
}
# Netteté des probabilités (Plackett-Luce), choisie sur les mêmes courses.
SENSIBILITE = 8.0
# Part des cotes du jour dans la probabilité finale ; le reste vient du modèle.
COTES_POIDS = 0.5
SIMULATIONS = 200_000
SEED = 20261105

PLACE_SCORE = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.45, 5: 0.3, 6: 0.2, 7: 0.1, 8: 0.1, 9: 0.1}
DECROISSANCE = 0.85


def charger_etat(html_path):
    html = open(html_path, encoding="utf-8").read()
    m = re.search(r'<script id="serverApp-state" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise SystemExit("Bloc serverApp-state introuvable : page non reconnue.")
    etat = json.loads(m.group(1))
    trouves = []

    def parcourir(o):
        if isinstance(o, dict):
            if "partants" in o and "distance" in o and "num_course_pmu" in o:
                trouves.append(o)
            for v in o.values():
                parcourir(v)
        elif isinstance(o, list):
            for v in o:
                parcourir(v)

    parcourir(etat)
    if not trouves:
        raise SystemExit("Aucune course avec partants dans la page.")
    return trouves[0]


def score_musique(musique):
    """Note 0..1 à partir de la musique (plus récent en premier). Les marqueurs d'année (25) sont ignorés."""
    runs = []
    for year, val, disc in re.findall(r"\((\d\d)\)|(D|T|A|R|\d+)([a-z]?)", musique or ""):
        if year:
            continue
        if val.isdigit() and int(val) > 0:
            runs.append(PLACE_SCORE.get(int(val), 0.0))
        else:
            runs.append(0.0)  # 0 = non placé, D = disqualifié, T/A/R = incident
    recent = runs[:10]
    if not recent:
        return None, 0
    somme = sum(s * (DECROISSANCE ** i) for i, s in enumerate(recent))
    poids = sum(DECROISSANCE ** i for i in range(len(recent)))
    return somme / poids, len(recent)


def valeur_note(partant, cle):
    v = (partant.get("interne_note_partant") or {}).get(cle)
    return None if v is None else float(v)


def analyser(course):
    lignes = []
    for p in course["partants"]:
        if p.get("statut_part") == "NP":
            continue  # non-partant exclu (les disqualifiés à l'arrivée restent des partants)
        musique = (p.get("cheval") or {}).get("musique") or p.get("musique")
        m_score, nb = score_musique(musique)
        composantes = {"musique": m_score}
        for cle in ["aptitudes", "forme_cheval", "chronos", "tandem", "conditions", "bruits_ecuries"]:
            composantes[cle] = valeur_note(p, cle)
        total, poids = 0.0, 0.0
        manquants = []
        for cle, w in POIDS.items():
            v = composantes.get(cle)
            if v is None:
                manquants.append(cle)
                v = 0.5  # donnée absente : neutre
            total += w * v
            poids += w
        lignes.append({
            "numero": p["num_partant"],
            "nom": p["cheval"]["nom_cheval"],
            "driver": (p.get("monte") or {}).get("nom_monte"),
            "entraineur": (p.get("entraineur") or {}).get("nom_entraineur"),
            "musique": musique,
            "nb_courses_musique": nb,
            "score": total / poids,
            "composantes": composantes,
            "manquants": manquants,
        })
    # Tri déterministe : d'abord par note, puis par numéro. Ainsi le résultat ne dépend pas de l'ordre de la page.
    lignes.sort(key=lambda x: (-x["score"], x["numero"]))
    return lignes


def _score_sim(l):
    """Score utilisé pour simuler les arrivées : la note, ou la probabilité mélangée aux cotes (échelle log)."""
    return l.get("score_sim", l["score"])


def cotes_de(course):
    """Rapport du jour de chaque partant (cote de la dernière mise avant le départ), ou None si incomplet."""
    cotes = {}
    for p in course["partants"]:
        if p.get("statut_part") == "NP":
            continue
        try:
            v = float(((p.get("get_last_cote_off") or {}).get("rapp_evol")))
        except (TypeError, ValueError):
            return None
        if v <= 0:
            return None
        cotes[p["num_partant"]] = v
    return cotes


def melanger_cotes(lignes, cotes, poids_cotes=COTES_POIDS):
    """Mélange la probabilité du modèle et la probabilité implicite des cotes.

    Les cotes ne servent qu'à ce mélange ; la note de chaque cheval reste celle du modèle.
    Renvoie les lignes triées par probabilité mélangée, avec score_sim pour la simulation.
    """
    m = max(l["score"] for l in lignes)
    w = {l["numero"]: math.exp(SENSIBILITE * (l["score"] - m)) for l in lignes}
    W = sum(w.values())
    pm = {k: w[k] / W for k in w}
    inv = {k: 1.0 / cotes[k] for k in pm}
    I = sum(inv.values())
    pk = {k: inv[k] / I for k in pm}
    pb = {k: poids_cotes * pk[k] + (1 - poids_cotes) * pm[k] for k in pm}
    nouvelles = []
    for l in lignes:
        x = dict(l)
        n = l["numero"]
        x["proba_modele"] = pm[n]
        x["proba_cotes"] = pk[n]
        x["proba_melange"] = pb[n]
        x["score_sim"] = math.log(pb[n]) / SENSIBILITE
        nouvelles.append(x)
    nouvelles.sort(key=lambda x: (-x["proba_melange"], x["numero"]))
    return nouvelles


def simuler(lignes, n=SIMULATIONS):
    """Simule des ordres d'arrivée (Plackett-Luce) et renvoie les comptages utiles."""
    rng = random.Random(SEED)
    s0 = _score_sim(lignes[0])
    poids = [math.exp(SENSIBILITE * (_score_sim(l) - s0)) for l in lignes]
    nums = [l["numero"] for l in lignes]
    ordres = []
    for _ in range(n):
        restants = list(range(len(nums)))
        w = poids[:]
        ordre = []
        for _k in range(min(5, len(nums))):
            total = sum(w[i] for i in restants)
            r = rng.random() * total
            acc = 0.0
            for i in restants:
                acc += w[i]
                if acc >= r:
                    ordre.append(i)
                    restants.remove(i)
                    break
        ordres.append(tuple(nums[i] for i in ordre))
    return ordres


def probabilites(ordres, lignes):
    n = len(ordres)
    top3, top5, victoire = {}, {}, {}
    for o in ordres:
        victoire[o[0]] = victoire.get(o[0], 0) + 1
        for x in o[:3]:
            top3[x] = top3.get(x, 0) + 1
        for x in o[:5]:
            top5[x] = top5.get(x, 0) + 1
    p = lambda d, k: d.get(k, 0) / n
    return {
        "victoire": {l["numero"]: p(victoire, l["numero"]) for l in lignes},
        "top3": {l["numero"]: p(top3, l["numero"]) for l in lignes},
        "top5": {l["numero"]: p(top5, l["numero"]) for l in lignes},
    }


def jeux(ordres, lignes):
    """Probabilité de réussite de chaque jeu courant, à partir des simulations."""
    n = len(ordres)
    nums = [l["numero"] for l in lignes]
    res = {}

    def proba(fn):
        return sum(1 for o in ordres if fn(o)) / n

    # Simples
    res["Simple gagnant n°%d" % nums[0]] = proba(lambda o: o[0] == nums[0])
    res["Simple placé n°%d" % nums[0]] = proba(lambda o: nums[0] in o[:3])
    # Couplé
    a, b = nums[0], nums[1]
    res["Couplé gagnant ordre %d-%d" % (a, b)] = proba(lambda o: o[0] == a and o[1] == b)
    res["Couplé gagnant désordre %d-%d" % (a, b)] = proba(lambda o: {a, b} <= set(o[:2]))
    res["Couplé placé %d-%d (désordre)" % (a, b)] = proba(lambda o: {a, b} <= set(o[:3]))
    # Trio : 3 premiers désordre (box) et ordre
    for k in (4, 5):
        box = set(nums[:k])
        res["Trio désordre box %d (%s)" % (k, ",".join(str(x) for x in nums[:k]))] = proba(lambda o: set(o[:3]) <= box)
    res["Trio ordre %d-%d-%d" % tuple(nums[:3])] = proba(lambda o: o[:3] == tuple(nums[:3]))
    # Quarté (4 premiers) désordre
    for k in (5, 6):
        box = set(nums[:k])
        res["Quarté désordre box %d" % k] = proba(lambda o: set(o[:4]) <= box)
    # Quinté désordre
    for k in (5, 6, 7):
        box = set(nums[:k])
        res["Quinté désordre box %d" % k] = proba(lambda o: set(o[:5]) <= box)
    # Quinté ordre (ordre exact des 5 premiers du classement)
    res["Quinté ordre %s" % "-".join(str(x) for x in nums[:5])] = proba(lambda o: o[:5] == tuple(nums[:5]))
    return res


BUDGET_COMBINAISONS = 10  # nombre maximal de combinaisons pour la recommandation par type de pari
TAILLES_BOX = {
    # type : (nombre de rangs couverts, tailles de box testées)
    "Tiercé": (3, [3, 4, 5, 6]),
    "Quarté": (4, [4, 5, 6, 7]),
    "Quinté": (5, [5, 6, 7, 8, 9]),
}


def combinaisons_en_box(ordres, lignes):
    """Probabilité de chaque box de tiercé, quarté et quinté (désordre), avec le nombre de combinaisons.

    Un box de k chevaux gagne si les N premiers de l'arrivée sont tous dans les k chevaux choisis.
    Nombre de combinaisons = C(k, N).
    """
    from math import comb
    n = len(ordres)
    nums = [l["numero"] for l in lignes]
    resultats = {}
    for type_pari, (rangs, tailles) in TAILLES_BOX.items():
        liste = []
        for k in tailles:
            if k > len(nums):
                continue
            box = set(nums[:k])
            p = sum(1 for o in ordres if set(o[:rangs]) <= box) / n
            nb = comb(k, rangs)
            liste.append({"box": k, "chevaux": nums[:k], "combinaisons": nb,
                          "probabilite": p, "par_combinaison": p / nb})
        resultats[type_pari] = liste
    return resultats


def recommandation_par_type(combinaisons):
    """Pour chaque type de pari, la taille de box la plus probable dans le budget de combinaisons."""
    rec = {}
    for type_pari, liste in combinaisons.items():
        dans_budget = [b for b in liste if b["combinaisons"] <= BUDGET_COMBINAISONS]
        if dans_budget:
            rec[type_pari] = max(dans_budget, key=lambda b: b["probabilite"])
    return rec


def main(chemin):
    course = charger_etat(chemin)
    lignes = analyser(course)
    ordres = simuler(lignes)
    prob = probabilites(ordres, lignes)
    rep = jeux(ordres, lignes)

    rd = course.get("reunion", {}).get("hippodrome", {}).get("name")
    print("%s R%sC%s — %s — %s m — %s" % (
        rd, course["reunion"]["num_reunion"], course["num_course_pmu"],
        course.get("libcourt_prix_course"), course["distance"], course.get("discipline")))
    print("Partants déclarés : %d" % len(lignes))
    print()
    print("%-3s %-20s %-16s %-7s %-7s %-7s %-7s" % ("N°", "Cheval", "Driver", "Note", "1er%", "Top3%", "Top5%"))
    for l in lignes:
        n = l["numero"]
        print("%-3d %-20s %-16s %-7.3f %-7.1f %-7.1f %-7.1f" % (
            n, l["nom"][:20], (l["driver"] or "")[:16], l["score"],
            100 * prob["victoire"][n], 100 * prob["top3"][n], 100 * prob["top5"][n]))
    print()
    print("Probabilités des jeux (sur %d simulations) :" % SIMULATIONS)
    for k, v in sorted(rep.items(), key=lambda kv: -kv[1]):
        print("  %6.2f %%  %s" % (100 * v, k))
    print()
    ordre_probable = [l["numero"] for l in lignes[:5]]
    print("Ordre probable du quinté :", "-".join(str(x) for x in ordre_probable))
    return lignes, prob, rep


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
