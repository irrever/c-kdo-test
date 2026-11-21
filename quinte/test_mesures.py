#!/usr/bin/env python3
"""Mesures et non-partants, sans réseau : python3 quinte/test_mesures.py

Un non-partant (statut NP) ne prend pas le départ : il n'entre ni dans les calculs de probabilité, ni dans le
classement de notre analyse, ni dans l'ordre affiché retenu. Un cheval disqualifié ou arrêté (AI, AR, TB, DX, RP) a
couru : il reste dans la course, sans rang.
"""
import math
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyse_registre as ar  # noqa: E402
import constat  # noqa: E402
import essais  # noqa: E402
import journee  # noqa: E402
import quintes  # noqa: E402
import registre  # noqa: E402

DATE = "2026-11-10"


def _ligne(numero, arrivee="", statut="DP", p=0.25, score=0.5, r=1, c=1, **extra):
    ligne = {champ: "" for champ in registre.CHAMPS}
    ligne.update({"date": DATE, "r": str(r), "c": str(c), "numero": str(numero), "nom": "H%s" % numero,
                  "discipline": "Plat", "distance": "1900", "hippodrome": "X", "heure": "13:00",
                  "calcule_le": "2026-11-10T11:00", "partants": "4", "score": str(score), "rang": str(numero),
                  "p_victoire": str(p), "p_top3": "0.5", "arrivee": str(arrivee), "statut": statut})
    ligne.update(extra)
    return ligne


def _course_avec_np(r=1, c=1):
    """Quatre chevaux au départ prévu : trois classés, le 4 (le mieux noté) déclaré non-partant après le calcul."""
    return [
        _ligne(1, 1, p=0.4, score=0.9, r=r, c=c, rapport_gagnant="1.6", rapport_place="1.1", cote_depart="2.0",
               n_musique="0.9"),
        _ligne(2, 2, p=0.3, score=0.5, r=r, c=c, rapport_place="1.9", cote_depart="4.0", n_musique="0.5"),
        _ligne(3, 3, p=0.2, score=0.4, r=r, c=c, rapport_place="3.0", cote_depart="9.0", n_musique="0.4"),
        _ligne(4, "", statut="NP", p=0.1, score=1.5, r=r, c=c, cote_depart="5.0", n_musique="1.0"),
    ]


def _quinte_avec_np():
    """Six partants qui ont couru, et un non-partant noté plus haut que tous."""
    rangs = [(1, 2, 0.9, 10), (2, 1, 0.8, 3), (3, 4, 0.7, 20), (4, 6, 0.6, 5), (5, 5, 0.5, 8), (6, 3, 0.4, 12)]
    rows = [_ligne(n, arr, score=sc, cote_depart=co) for n, arr, sc, co in rangs]
    rows.append(_ligne(7, "", statut="NP", score=0.95, cote_depart=4))
    return rows


class TestRegistre(unittest.TestCase):
    def test_coureurs_et_statut_connu(self):
        lignes = _course_avec_np()
        self.assertEqual([x["numero"] for x in registre.coureurs(lignes)], ["1", "2", "3"])
        self.assertTrue(registre.statut_connu(lignes))
        self.assertFalse(registre.statut_connu([dict(x, statut="") for x in lignes]))

    def test_inscrire_statuts(self):
        chemin = os.path.join(tempfile.mkdtemp(), "registre.csv")
        lignes = [dict(x, statut="") for x in _course_avec_np()] + [_ligne(1, 1, c=2, statut="")]
        registre._ecrire(lignes, chemin)
        statuts = {(1, 1): {1: "DP", 2: "DP", 3: "DP", 4: "NP"}}
        self.assertEqual(registre.inscrire_statuts(DATE, statuts, chemin), 4)
        self.assertEqual(registre.inscrire_statuts(DATE, statuts, chemin), 0)  # déjà inscrit
        relus = registre.lire(chemin)
        self.assertEqual({x["numero"]: x["statut"] for x in relus if x["c"] == "1"},
                         {"1": "DP", "2": "DP", "3": "DP", "4": "NP"})
        self.assertEqual([x["statut"] for x in relus if x["c"] == "2"], [""])  # l'autre course n'est pas touchée

    def test_statuts_de_une_course(self):
        course = {"partants": [{"num_partant": 1, "statut_part": "DP"}, {"num_partant": 2, "statut_part": "AI"},
                               {"num_partant": 3, "statut_part": "NP"}, {"num_partant": 4}]}
        self.assertEqual(journee.statuts_de(course), {1: "DP", 2: "AI", 3: "NP"})


class TestAnalyseSansNonPartant(unittest.TestCase):
    def test_courses_sans_non_partant(self):
        courses = ar.courses_arrivees(_course_avec_np())
        self.assertEqual(len(courses), 1)
        self.assertEqual([p["numero"] for p in courses[0]["partants"]], ["1", "2", "3"])
        self.assertEqual(courses[0]["non_partants"], ["4"])
        self.assertEqual(len(courses[0]["tous"]), 4)

    def test_modele_repartit_la_part_du_non_partant(self):
        res = ar.modele(ar.courses_arrivees(_course_avec_np()))
        self.assertEqual(len(res), 1)
        self.assertAlmostEqual(res[0]["perte"], -math.log(0.4 / 0.9), places=6)
        self.assertAlmostEqual(res[0]["hasard"], math.log(3), places=6)
        self.assertTrue(res[0]["favori"])

    def test_disqualifie_reste_dans_la_course(self):
        lignes = [_ligne(1, 1), _ligne(2, 2), _ligne(3, 3), _ligne(4, "", statut="AI")]
        courses = ar.courses_arrivees(lignes)
        self.assertEqual(len(courses[0]["partants"]), 4)
        self.assertEqual(courses[0]["non_partants"], [])

    def test_course_sans_statut_ecartee_et_signalee(self):
        lignes = [dict(x, statut="") for x in _course_avec_np(c=2)] + _course_avec_np(c=1)
        sans = []
        courses = ar.courses_arrivees(lignes, sans_statut=sans)
        self.assertEqual([x["cle"] for x in courses], [(DATE, "1", "1")])
        self.assertEqual(sans, [(DATE, "1", "2")])
        self.assertIn("sans statut relevé, exclues : 1", ar.rapport(lignes))


class TestEssaisEtQuintesSansNonPartant(unittest.TestCase):
    def test_essais_ignore_le_non_partant(self):
        lignes = _course_avec_np()
        for variante in essais.VARIANTES:
            avec = essais.evaluer_course(lignes, variante)
            sans = essais.evaluer_course(registre.coureurs(lignes), variante)
            self.assertAlmostEqual(avec[0], sans[0], places=9)
            self.assertEqual(avec[1:], sans[1:])

    def test_quinte_ignore_le_non_partant(self):
        avec = quintes.mesure_course(_quinte_avec_np())
        self.assertEqual(avec, quintes.mesure_course(registre.coureurs(_quinte_avec_np())))
        self.assertEqual(avec["partants"], 6)
        self.assertEqual(avec["rang_median_notre"], 3)  # arrivants classés 2, 1, 6, 3 et 5 chez nous, sans le 7


class TestConstatSansNonPartant(unittest.TestCase):
    def test_charger_retire_le_non_partant(self):
        courses, ecartees = constat.charger(_course_avec_np())
        self.assertEqual(len(courses), 1)
        c = courses[0]
        self.assertEqual(c["n"], 3)
        self.assertEqual(set(c["scores"]), {"1", "2", "3"})
        self.assertEqual(c["non_partants"], {"4"})
        self.assertEqual(ecartees["statut non relevé"], 0)

    def test_bilan_ne_retient_pas_le_non_partant_affiche(self):
        texte = constat.bilan_jour(DATE, entrees=[{"r": 1, "c": 1, "ordre": ["4", "1", "2"]}],
                                   lignes=_course_avec_np())
        self.assertIn("4 (NP)", texte)  # le non-partant est marqué dans le tableau
        self.assertIn("1 course(s) sur 1 ; 1 non-partant(s) parmi les trois premiers affichés", texte)
        # sans le 4, le n° 1 affiché est le 1 : il gagne, donc 100 % de top 1 et de top 3
        self.assertIn("| Ce qui était affiché | — | 100,0 % | 100,0 % |", texte)


if __name__ == "__main__":
    unittest.main()
