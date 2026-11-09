#!/usr/bin/env python3
"""Constat réel sur les courses terminées du registre, et bilan de chaque journée.

Sur les mêmes courses, compare le hasard, le modèle (sensibilité 8, puis 4), le favori des cotes, le mélange à 70 % de
cotes, le réglage du 9 novembre (90 % de cotes, trot aux cotes seules) et notre analyse (sensibilité 4, sans cotes),
qui est le pronostic en production depuis le 9 novembre au soir.
Mesures : perte du vainqueur (plus bas = mieux), taux de top 1 et de top 3, et l'argent : rapport officiel du simple
gagnant et du simple placé sur le pronostic n°1, pour 1 € par course. Les intervalles à 95 % viennent d'un
rééchantillonnage des courses.

Usage : python3 quinte/constat.py                    constat global (écrit quinte/journal/constat.md)
        python3 quinte/constat.py --jour AAAA-MM-JJ  bilan d'une journée (écrit quinte/journal/bilan-AAAA-MM-JJ.md)
        ... --rattraper                              relit d'abord les rapports et cotes des courses terminées
"""
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyse_registre as ar  # noqa: E402
import registre  # noqa: E402

SORTIE = os.path.join(HERE, "journal", "constat.md")
TIRAGES = 2000  # rééchantillonnages pour les intervalles à 95 %
SEED = 20261109
CHANGEMENT_K = "2026-11-09T21:30"  # à partir de là, le registre porte K = 4 (8 avant)
FAMILLES = ("plat", "obstacle", "trot", "autre")
LIBELLES = {
    "hasard": "Hasard",
    "modele": "Modèle (sensibilité 8)",
    "favori": "Favori des cotes",
    "melange": "Mélange à 70 % de cotes",
    "propose": "Réglage du 9 novembre (sensibilité 4, 90 % cotes, trot aux cotes seules)",
    "analyse": "Notre analyse (sensibilité 4, sans cotes)",
}
COMPARAISONS = [
    ("Perte du vainqueur : notre analyse − favori des cotes", "analyse", "favori", 0, "perte"),
    ("Perte du vainqueur : réglage du 9 novembre − modèle", "propose", "modele", 0, "perte"),
    ("Perte du vainqueur : favori des cotes − modèle", "favori", "modele", 0, "perte"),
    ("Top 1 : notre analyse − favori des cotes", "analyse", "favori", 1, "pts"),
    ("Gagnant pour 1 € : notre analyse − favori des cotes", "analyse", "favori", 3, "pts"),
    ("Placé pour 1 € : notre analyse − favori des cotes", "analyse", "favori", 4, "pts"),
    ("Placé pour 1 € : favori des cotes − modèle", "favori", "modele", 4, "pts"),
]


def _proba_modele(scores, K):
    """Probabilité de gagner selon le modèle : poids exp(K × note), normalisés. C'est le premier rang de la simulation."""
    m = max(scores.values())
    w = {n: math.exp(K * (s - m)) for n, s in scores.items()}
    t = sum(w.values())
    return {n: v / t for n, v in w.items()}


def _proba_cotes(cotes):
    """Probabilité implicite de chaque cheval d'après sa cote : 1 / cote, normalisé."""
    inverses = {n: 1.0 / c for n, c in cotes.items()}
    t = sum(inverses.values())
    return {n: v / t for n, v in inverses.items()}


def _melange(c, K, poids):
    if not c["cotes"]:
        return None
    pm = _proba_modele(c["scores"], K)
    pk = _proba_cotes(c["cotes"])
    return {n: poids * pk[n] + (1 - poids) * pm[n] for n in pm}


def _reglage_9_nov(c):
    """Le réglage du 9 novembre au soir : modèle à sensibilité 4, mélangé aux cotes (90 %, cotes seules au trot).
    Les poids sont fixés ici, pour que ce constat ne change pas avec la production."""
    if not c["cotes"]:
        return None
    poids = 1.0 if c["famille"] == "trot" else 0.9
    pm = _proba_modele(c["scores"], 4.0)
    pk = _proba_cotes(c["cotes"])
    return {n: poids * pk[n] + (1 - poids) * pm[n] for n in pm}


def _notre_analyse(c):
    """Notre analyse : le modèle seul, sensibilité 4, sans les cotes. C'est le pronostic en production."""
    return _proba_modele(c["scores"], 4.0)


PROBABILITES = {
    "modele": lambda c: _proba_modele(c["scores"], 8.0),
    "favori": lambda c: _proba_cotes(c["cotes"]) if c["cotes"] else None,
    "melange": lambda c: _melange(c, 8.0, 0.7),
    "propose": _reglage_9_nov,
    "analyse": _notre_analyse,
}


def charger(lignes=None):
    """Courses terminées exploitables, avec leurs notes, leurs cotes de départ (si tous les partants en ont),
    leur vainqueur et leurs rapports officiels. Renvoie (courses, écartées par motif)."""
    lignes = registre.lire() if lignes is None else lignes
    courses, ecartees = [], {"sans rapport gagnant": 0, "rapport placé incomplet": 0}
    for c in ar.courses_arrivees(lignes):
        partants = [p for p in c["partants"] if ar._nombre(p["arrivee"]) is not None]  # sans arrivée : non-partant retiré
        gagnants = [p for p in partants if ar._nombre(p["arrivee"]) == 1]
        if len(gagnants) != 1:
            continue
        gagnant = gagnants[0]
        placés = {p["numero"] for p in partants if ar._nombre(p["arrivee"]) in (1.0, 2.0, 3.0)}
        rp = {p["numero"]: ar._nombre(p.get("rapport_place")) for p in partants if p["numero"] in placés}
        rp = {n: v for n, v in rp.items() if v}
        rg = ar._nombre(gagnant.get("rapport_gagnant"))
        if not rg:
            ecartees["sans rapport gagnant"] += 1
            continue
        if len(rp) != len(placés):
            ecartees["rapport placé incomplet"] += 1
            continue
        cotes, sources = {}, set()
        for p in partants:
            if ar._nombre(p.get("cote_depart")):
                v = ar._nombre(p["cote_depart"])
                sources.add("reprise" if p.get("heure_cote") == "reprise" else "captée")
            else:
                v = ar._nombre(p.get("cote"))
                sources.add("cote du registre")
            if not v or v <= 0:
                cotes = None
                break
            cotes[p["numero"]] = v
        premier = c["partants"][0]
        courses.append({
            "cle": c["cle"], "calcule_le": premier["calcule_le"], "n": len(partants),
            "discipline": partants[0]["discipline"], "hippodrome": partants[0]["hippodrome"],
            "heure": partants[0]["heure"], "famille": ar.famille(partants[0]["discipline"]),
            "places": {p["numero"]: ar._nombre(p["arrivee"]) for p in partants},
            "scores": {p["numero"]: float(p["score"]) for p in partants},
            "scores_tous": {p["numero"]: float(p["score"]) for p in c["partants"]},
            "p_registre": {p["numero"]: ar._nombre(p.get("p_victoire")) for p in c["partants"]},
            "cotes": cotes, "sources": sources, "gagnant": gagnant["numero"], "placés": placés,
            "rg": rg, "rp": rp,
        })
    return courses, ecartees


def evaluer(courses, cle):
    """Par course, pour une variante : (perte du vainqueur, top 1, top 3, gain du gagnant, gain du placé), gains
    pour 1 € sur le pronostic n°1. None quand une cote manque. Le hasard donne l'espérance : chaque cheval a une
    chance sur n d'être choisi."""
    sortie = []
    for c in courses:
        if cle == "hasard":
            n = c["n"]
            sortie.append((math.log(n), 1 / n, min(3, n) / n, c["rg"] / n, sum(c["rp"].values()) / n))
            continue
        p = PROBABILITES[cle](c)
        if p is None:
            sortie.append(None)
            continue
        ordre = sorted(p, key=lambda k: (-p[k], int(k)))
        pick = ordre[0]
        perte = -math.log(max(p[c["gagnant"]], 1e-9))
        top1 = 1.0 if pick == c["gagnant"] else 0.0
        top3 = 1.0 if c["gagnant"] in ordre[:3] else 0.0
        gain_g = c["rg"] if pick == c["gagnant"] else 0.0
        gain_p = c["rp"].get(pick, 0.0) if pick in c["placés"] else 0.0
        sortie.append((perte, top1, top3, gain_g, gain_p))
    return sortie


def moyennes(resultats):
    """Moyennes sur les courses calculées. Les gains sont donnés en bénéfice pour 1 € misé (gain moins mise)."""
    xs = [r for r in resultats if r is not None]
    if not xs:
        return None
    n = len(xs)
    m = [sum(r[k] for r in xs) / n if all(r[k] is not None for r in xs) else None for k in range(5)]
    return {"n": n, "perte": m[0], "top1": m[1], "top3": m[2], "gagnant": m[3] - 1, "place": m[4] - 1}


def _alignes(ra, rb):
    """Mêmes courses dans les deux listes : celles où les deux variantes sont calculées."""
    paires = [(x, y) for x, y in zip(ra, rb) if x is not None and y is not None]
    return [p[0] for p in paires], [p[1] for p in paires]


def intervalle(a, b, k, rng):
    """Différence moyenne a − b sur la colonne k, avec son intervalle à 95 % (rééchantillonnage des courses)."""
    d = [x[k] - y[k] for x, y in zip(a, b)]
    n = len(d)
    tirages = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(TIRAGES))
    return sum(d) / n, tirages[int(0.025 * TIRAGES)], tirages[int(0.975 * TIRAGES) - 1]


def _fr(x, d=2, signe=False):
    return ar._fr(x, d, signe)


def _pourcent(x):
    return _fr(100 * x, 1, True) + " %"


def _ecart(x, unite):
    if unite == "perte":
        return _fr(x, 2, True)
    return _fr(100 * x, 1, True) + " pts"


def _ligne_tableau(nom, m):
    if not m:
        return "| %s | — | — | — | — | — |" % nom
    return "| %s | %s | %s | %s | %s | %s |" % (
        nom, _fr(m["perte"]) if m["perte"] is not None else "—", _fr(100 * m["top1"], 1) + " %",
        _fr(100 * m["top3"], 1) + " %", _pourcent(m["gagnant"]), _pourcent(m["place"]))


def rapport(courses, ecartees):
    """Texte du constat global, en Markdown."""
    avec = [c for c in courses if c["cotes"]]
    rng = random.Random(SEED)
    resultats = {k: evaluer(avec, k) for k in LIBELLES}
    toutes = evaluer(courses, "modele")
    captees = sum(1 for c in avec if c["sources"] == {"captée"})
    reprises = sum(1 for c in avec if c["sources"] == {"reprise"})
    ecarts = []  # contrôle sur tous les partants analysés, y compris ceux retirés avant le départ
    for c in courses:
        K = 4.0 if c["calcule_le"] >= CHANGEMENT_K else 8.0  # chaque ligne du registre porte le K de son calcul
        pm = _proba_modele(c["scores_tous"], K)
        ecarts += [abs(pm[n] - v) for n, v in c["p_registre"].items() if v is not None]
    L = ["# Constat réel : modèle, marché et notre analyse", ""]
    L.append("Courses terminées exploitables : %d, dont %d avec les cotes de départ de tous les partants. Écartées : %s."
             % (len(courses), len(avec), ", ".join("%s %d" % (motif, n) for motif, n in ecartees.items())))
    L.append("Origine des cotes : %d course(s) relevées avant le départ, %d relues après la course, %d autre(s)."
             % (captees, reprises, len(avec) - captees - reprises))
    if ecarts:
        L.append("Contrôle : la probabilité du modèle reconstruite s'écarte de celle du registre de %s en moyenne "
                 "(%s au plus), à cause des simulations." % (_fr(sum(ecarts) / len(ecarts), 4), _fr(max(ecarts), 4)))
    L += ["", "## 1. Sur les %d courses avec cotes complètes" % len(avec), "",
          "| Variante | Perte du vainqueur | Top 1 | Top 3 | Gagnant : bénéfice pour 1 € | Placé : bénéfice pour 1 € |",
          "|---|---:|---:|---:|---:|---:|"]
    for k in LIBELLES:
        L.append(_ligne_tableau(LIBELLES[k], moyennes(resultats[k])))
    L.append(_ligne_tableau("Modèle (sensibilité 8), sur toutes les %d courses" % len(courses), moyennes(toutes)))
    if avec:
        L += ["", "## 2. Différences entre variantes, avec intervalle à 95 %", ""]
        for libelle, a, b, k, unite in COMPARAISONS:
            xa, xb = _alignes(resultats[a], resultats[b])
            if not xa:
                continue
            d, lo, hi = intervalle(xa, xb, k, rng)
            L.append("- %s : %s [intervalle %s ; %s]" % (libelle, _ecart(d, unite), _ecart(lo, unite), _ecart(hi, unite)))
        L += ["", "## 3. Perte du vainqueur par famille, sur les %d courses avec cotes" % len(avec), "",
              "| Famille | Courses | Hasard | Modèle | Favori | Mélange | Réglage du 9 nov. | Notre analyse |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for f in FAMILLES:
            sous = [i for i, c in enumerate(avec) if c["famille"] == f]
            if not sous:
                continue
            cellules = []
            for k in LIBELLES:
                xs = [resultats[k][i][0] for i in sous if resultats[k][i] is not None]
                cellules.append(_fr(sum(xs) / len(xs)) if xs else "—")
            L.append("| %s | %d | %s |" % (f.capitalize(), len(sous), " | ".join(cellules)))
    L += ["", "## Réserves", "",
          "- Le réglage du 9 novembre a été choisi sur les courses déjà vues : seul un nouveau lot de courses peut le confirmer.",
          "- Les cotes « relues après la course » sont les dernières cotes avant le départ, telles que la page Equidia les garde. "
          "Ce ne sont pas des relevés faits pendant la journée.",
          "- Les gains sont ceux de la page Equidia une fois la course terminée : simple gagnant et simple placé, pour 1 € misé.",
          "- Notre analyse est le pronostic en production depuis le 9 novembre au soir : ses résultats sur les courses suivantes "
          "sont dans les bilans quotidiens."]
    return "\n".join(L) + "\n"


def _cle_course(c):
    return (int(c["cle"][1]), int(c["cle"][2]))


def _evaluer_affiche(c, ordre):
    """Ce qui était affiché : le n° 1 publié, sans probabilité. Renvoie (None, top 1, top 3, gain du gagnant, gain du
    placé), comme evaluer."""
    pick = ordre[0]
    gagnant = c["gagnant"]
    gain_g = c["rg"] if pick == gagnant else 0.0
    gain_p = c["rp"].get(pick, 0.0) if pick in c["placés"] else 0.0
    return (None, 1.0 if pick == gagnant else 0.0, 1.0 if gagnant in ordre[:3] else 0.0, gain_g, gain_p)


def _ordre_de(p):
    """Numéros par probabilité décroissante (à égalité, le plus petit numéro d'abord)."""
    return sorted(p, key=lambda k: (-p[k], int(k)))


def _top(ordre, n=3):
    return "–".join(ordre[:n]) if ordre else "—"


def _rang(ordre, numero):
    return str(ordre.index(numero) + 1) if numero in ordre else "hors pronostic"


def _analyse_affichee(c):
    """Notre analyse telle qu'elle aurait été calculée : tous les partants analysés, sans les cotes."""
    return _ordre_de(_proba_modele(c["scores_tous"], 4.0))


def bilan_jour(date, entrees=None, quinte=None, lignes=None):
    """Bilan des courses terminées d'une journée : ce qui était affiché, et notre analyse (sans cotes) recalculée sur
    les mêmes courses, comparée au favori des cotes. entrees : les courses de la journée (journee.json).
    quinte : (r, c) du quinté du jour."""
    lignes = registre.lire() if lignes is None else lignes
    courses, ecartees = charger([x for x in lignes if x["date"] == date])
    affiche = {}
    for e in entrees or []:
        affiche[(int(e["r"]), int(e["c"]))] = [str(n) for n in (e.get("ordre") or [])]
    cq = (int(quinte[0]), int(quinte[1])) if quinte else None
    avec_affiche = [c for c in courses if affiche.get(_cle_course(c))]
    commun = [c for c in avec_affiche if c["cotes"]]
    resultats = {
        "hasard": evaluer(commun, "hasard"),
        "affiche": [_evaluer_affiche(c, affiche[_cle_course(c)]) for c in commun],
        "analyse": evaluer(commun, "analyse"),
        "propose": evaluer(commun, "propose"),
        "favori": evaluer(commun, "favori"),
    }
    tous = [_evaluer_affiche(c, affiche[_cle_course(c)]) for c in avec_affiche]
    autre_que_affiche = sum(1 for c in commun
                            if _ordre_de(PROBABILITES["analyse"](c))[0] != affiche[_cle_course(c)][0])
    autre_que_favori = sum(1 for c in commun
                           if _ordre_de(PROBABILITES["analyse"](c))[0] != _ordre_de(PROBABILITES["favori"](c))[0])
    raisons = ", ".join("%s %d" % (motif, n) for motif, n in ecartees.items()) or "aucune"
    L = ["# Bilan des courses du %s : ce qui était affiché, et notre analyse" % date, ""]
    L.append("Courses terminées exploitables : %d, dont %d avec un pronostic affiché et les cotes de tous les partants. "
             "Écartées : %s." % (len(courses), len(commun), raisons))
    L += ["", "## 1. Sur les %d courses avec pronostic affiché et cotes" % len(commun), "",
          "| Variante | Perte du vainqueur | Top 1 | Top 3 | Gagnant : bénéfice pour 1 € | Placé : bénéfice pour 1 € |",
          "|---|---:|---:|---:|---:|---:|"]
    L.append(_ligne_tableau("Hasard", moyennes(resultats["hasard"])))
    L.append(_ligne_tableau("Ce qui était affiché", moyennes(resultats["affiche"])))
    L.append(_ligne_tableau("Notre analyse (sensibilité 4, sans cotes)", moyennes(resultats["analyse"])))
    L.append(_ligne_tableau("Réglage du 9 novembre (90 % cotes, trot aux cotes seules)", moyennes(resultats["propose"])))
    L.append(_ligne_tableau("Favori des cotes", moyennes(resultats["favori"])))
    L.append(_ligne_tableau("Ce qui était affiché, sur les %d courses avec pronostic" % len(avec_affiche),
                            moyennes(tous)))
    L += ["", "Notre analyse choisit un autre n° 1 que l'affiché dans %d course(s) sur %d, et un autre que le favori des "
          "cotes dans %d course(s)." % (autre_que_affiche, len(commun), autre_que_favori)]
    L += ["", "## 2. Le quinté du jour", ""]
    course_q = next((c for c in courses if cq and _cle_course(c) == cq), None)
    if cq is None:
        L.append("Pas de quinté pour cette journée.")
    elif course_q is None or not course_q["places"]:
        L.append("Le quinté (R%dC%d) n'a pas encore d'arrivée enregistrée." % cq)
    else:
        arrivee = sorted(course_q["places"], key=lambda n: course_q["places"][n])
        aff = affiche.get(cq, [])
        analyse = _analyse_affichee(course_q)
        L.append("R%dC%d · %s · arrivée %s" % (cq[0], cq[1], course_q["hippodrome"], _top(arrivee, 5)))
        L.append("Affiché : %s (dans les 5 premiers : %d sur 5)." % (
            _top(aff, 5), len(set(aff[:5]) & set(arrivee[:5]))))
        L.append("Notre analyse : %s (dans les 5 premiers : %d sur 5)." % (
            _top(analyse, 5), len(set(analyse[:5]) & set(arrivee[:5]))))
    L += ["", "## 3. Course par course", "",
          "| Course | Arrivée (3 premiers) | Affiché | Notre analyse | Vainqueur : rang affiché / analyse |",
          "|---|---|---|---|---|"]
    for c in sorted(courses, key=_cle_course):
        cle = _cle_course(c)
        arrivee = sorted(c["places"], key=lambda n: c["places"][n])
        aff = affiche.get(cle)
        analyse = _analyse_affichee(c)
        nom = "R%dC%d%s · %s %s" % (cle[0], cle[1], " (quinté)" if cle == cq else "", c["hippodrome"], c["heure"])
        L.append("| %s | %s | %s | %s | %s / %s |" % (
            nom, _top(arrivee), _top(aff) if aff else "—", _top(analyse),
            _rang(aff, c["gagnant"]) if aff else "—", _rang(analyse, c["gagnant"])))
    L += ["", "## Contrôle", ""]
    hors_quinte = [c for c in avec_affiche if _cle_course(c) != cq]
    reproduites = sum(1 for c in hors_quinte if _analyse_affichee(c)[:5] == affiche[_cle_course(c)][:5])
    L.append("Notre analyse, recalculée à partir des notes enregistrées, reproduit le pronostic affiché sur %d course(s) "
             "sur %d (hors quinté, dont le pronostic final peut avoir été figé avec les cotes)."
             % (reproduites, len(hors_quinte)))
    L += ["", "## Réserves", "",
          "- Notre analyse est recalculée ici à partir des notes et des cotes du registre : c'est un contrôle, pas un "
          "pronostic en direct.",
          "- Les cotes sont celles relevées avant le départ ou relues après la course. Elles ne sont pas forcément celles "
          "d'un relevé à l'heure fixée.",
          "- Les chevaux qui n'ont pas fini sont écartés des calculs, sauf dans le pronostic affiché, tel qu'il était.",
          "- Une seule journée ne suffit pas à conclure : le constat global reste sur plusieurs jours."]
    return "\n".join(L) + "\n"


def _quinte_du_jour(date):
    """(r, c) du quinté du jour, d'après son journal, ou None."""
    import suivi
    chemin = suivi._fichier_pronostic(date)
    if not os.path.exists(chemin):
        return None
    with open(chemin, encoding="utf-8") as f:
        r, c = [int(x) for x in json.load(f)["course"].replace("R", "").split("C")]
    return (r, c)


def main(argv):
    if "--jour" in argv:
        date = argv[argv.index("--jour") + 1]
        import journee
        if "--rattraper" in argv:
            print("courses terminées relues pour %s : %d" % (date, journee.rattraper(date)))
        texte = bilan_jour(date, entrees=journee.charger(date), quinte=_quinte_du_jour(date))
        import essais
        import quintes
        texte += quintes.bloc_bilan(date) + essais.bloc_bilan(date)
        os.makedirs(os.path.join(HERE, "journal"), exist_ok=True)
        with open(os.path.join(HERE, "journal", "bilan-%s.md" % date), "w", encoding="utf-8") as f:
            f.write(texte)
        print(texte)
        return
    courses, ecartees = charger()
    texte = rapport(courses, ecartees)
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    with open(SORTIE, "w", encoding="utf-8") as f:
        f.write(texte)
    print(texte)


if __name__ == "__main__":
    main(sys.argv[1:])
