#!/usr/bin/env python3
"""Tests du registre, des analyses et de la journée, sans réseau : python3 quinte/test_registre.py"""
import math
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import registre  # noqa: E402
import analyse_registre as ar  # noqa: E402
import journee  # noqa: E402


def _partant(num, nom, musique, notes, poids, corde, statut="DP", place=None, cote=None):
    return {
        "num_partant": num, "statut_part": statut, "cheval": {"nom_cheval": nom}, "musique": musique,
        "monte": {"nom_monte": "J%d" % num}, "interne_note_partant": notes,
        "pds_calc_hand_partant": poids, "place_corde_partant": corde, "num_place_arrivee": place,
        "get_last_cote_off": {"rapp_evol": cote} if cote is not None else None,
    }


def _course(arrivee=False):
    def notes(aptitudes, forme):
        return {"aptitudes": aptitudes, "forme_cheval": forme, "chronos": 0.5, "tandem": 0.5,
                "conditions": 0.5, "bruits_ecuries": 0.5}
    partants = [
        _partant(1, "ALPHA", "1a2a3a", notes(0.8, 0.7), 58, 3, place=1 if arrivee else None, cote=4.0),
        _partant(2, "BETA", "5a0a2a", notes(0.4, 0.5), 56, 1, place=3 if arrivee else None, cote=6.0),
        _partant(3, "GAMMA", "0a0a9a", notes(0.5, 0.3), 60, 5, place=2 if arrivee else None, cote=9.0),
        _partant(4, "DELTA", "8a8a8a", notes(0.6, 0.6), 54, 2, statut="NP"),
    ]
    return {"discipline": "Plat", "distance": 1900, "heure_depart_course": "15:15",
            "reunion": {"hippodrome": {"name": "DEAUVILLE"}},
            "type_statut_course_id": "finished" if arrivee else "before", "partants": partants}


def _ligne(date, numero, arrivee, p_victoire, poids="", corde="", discipline="Plat", distance="1900", cote=""):
    ligne = {champ: "" for champ in registre.CHAMPS}
    ligne.update({"date": date, "r": "1", "c": "1", "discipline": discipline, "distance": distance,
                  "partants": "3", "numero": str(numero), "nom": "H%d" % numero,
                  "arrivee": "" if arrivee is None else str(arrivee), "p_victoire": str(p_victoire),
                  "p_top3": "0.5", "rang": str(numero),
                  "poids": str(poids) if poids != "" else "", "corde": str(corde) if corde != "" else "",
                  "cote": str(cote) if cote != "" else ""})
    return ligne


class TestRegistre(unittest.TestCase):
    def setUp(self):
        self.chemin = os.path.join(tempfile.mkdtemp(), "registre.csv")

    def test_lignes_de_course(self):
        c = _course()
        lignes, probs = journee._calcul(c)
        rows = registre.lignes_de_course("2026-11-07", 1, 3, c, lignes, probs,
                                         journee.ae.cotes_de(c), "2026-11-07T16:50:00")
        self.assertEqual(len(rows), 3)  # le non-partant est exclu
        par_numero = {r["numero"]: r for r in rows}
        self.assertEqual(par_numero[1]["poids"], 58)
        self.assertEqual(par_numero[2]["corde"], 1)
        self.assertEqual(par_numero[1]["cote"], 4.0)
        self.assertNotEqual(par_numero[1]["n_aptitudes"], "")
        self.assertEqual(sorted(r["rang"] for r in rows), [1, 2, 3])

    def test_ajout_sans_doublon(self):
        c = _course()
        lignes, probs = journee._calcul(c)
        rows = registre.lignes_de_course("2026-11-07", 1, 3, c, lignes, probs, None, "t")
        self.assertEqual(registre.ajouter(rows, self.chemin), 3)
        self.assertEqual(registre.ajouter(rows, self.chemin), 0)
        self.assertEqual(len(registre.lire(self.chemin)), 3)

    def test_arrivees(self):
        c = _course()
        lignes, probs = journee._calcul(c)
        rows = registre.lignes_de_course("2026-11-07", 1, 3, c, lignes, probs, None, "t")
        registre.ajouter(rows, self.chemin)
        places = {1: 1, 2: 3, 3: 2}
        self.assertEqual(registre.mettre_a_jour_arrivees("2026-11-07", 1, 3, places, self.chemin), 3)
        self.assertEqual(registre.mettre_a_jour_arrivees("2026-11-07", 1, 3, places, self.chemin), 0)
        arrivees = {r["numero"]: r["arrivee"] for r in registre.lire(self.chemin)}
        self.assertEqual(arrivees, {"1": "1", "2": "3", "3": "2"})


class TestJournee(unittest.TestCase):
    def test_places_et_arrivee(self):
        c = _course(arrivee=True)
        self.assertEqual(journee._places(c), {1: 1, 2: 3, 3: 2})
        self.assertEqual(journee._arrivee(c), [1, 3, 2])
        self.assertEqual(journee._arrivee(_course()), [])


class TestCompletion(unittest.TestCase):
    def test_completer_garde_les_courses_existantes(self):
        import json
        dossier = tempfile.mkdtemp()
        avant = journee.JOURNAL
        journee.JOURNAL = dossier
        original = journee.analyser_journee
        try:
            with open(journee.fichier("2026-11-09"), "w", encoding="utf-8") as f:
                json.dump({"date": "2026-11-09",
                           "courses": [{"r": 1, "c": 1, "statut": "before", "ordre": [2, 1]}]}, f)

            def faux_analyser(date, ignorer=frozenset()):
                self.assertIn((1, 1), ignorer)  # la course déjà présente n'est pas recalculée
                return [{"r": 3, "c": 2, "statut": "before", "ordre": [5]}], []
            journee.analyser_journee = faux_analyser
            self.assertEqual(journee.completer("2026-11-09"), 1)
            courses = json.load(open(journee.fichier("2026-11-09"), encoding="utf-8"))["courses"]
            self.assertEqual([(x["r"], x["c"]) for x in courses], [(1, 1), (3, 2)])
            self.assertEqual(courses[0]["ordre"], [2, 1])
        finally:
            journee.analyser_journee = original
            journee.JOURNAL = avant


class TestAnalyse(unittest.TestCase):
    def _jeu(self):
        rows = []
        for jour in ["2026-11-01", "2026-11-02", "2026-11-03"]:
            rows += [_ligne(jour, 1, 1, 0.5, poids=58, corde=3),
                     _ligne(jour, 2, 2, 0.3, poids=56, corde=1),
                     _ligne(jour, 3, 3, 0.2, poids=60, corde=5)]
        return rows

    def test_modele_et_hasard(self):
        resultats = ar.modele(ar.courses_arrivees(self._jeu()))
        self.assertEqual(len(resultats), 3)
        self.assertAlmostEqual(ar.moyenne([r["perte"] for r in resultats]), -math.log(0.5), places=6)
        self.assertAlmostEqual(ar.moyenne([r["hasard"] for r in resultats]), math.log(3), places=6)
        self.assertTrue(all(r["favori"] for r in resultats))

    def test_correlation_poids(self):
        rs = ar.correlations(ar.courses_arrivees(self._jeu()), "poids")
        self.assertEqual(len(rs), 3)
        # poids 58 / 56 / 60 pour les places 1 / 2 / 3 : corrélation +0,5 dans chaque course
        self.assertAlmostEqual(rs[0]["r"], 0.5, places=6)

    def test_cotes_du_jour(self):
        rows = []
        for jour in ["2026-11-01", "2026-11-02", "2026-11-03"]:
            rows += [_ligne(jour, 1, 1, 0.5, cote=2.0), _ligne(jour, 2, 2, 0.3, cote=4.0),
                     _ligne(jour, 3, 3, 0.2, cote=4.0)]
        resultats = ar.modele(ar.courses_arrivees(rows))
        # cotes 2 / 4 / 4 : probabilités implicites 0,5 / 0,25 / 0,25 ; le vainqueur (cote 2) a 0,5
        self.assertAlmostEqual(ar.moyenne([r["perte_marche"] for r in resultats]), math.log(2), places=6)
        self.assertIn("cotes du jour seules", ar.rapport(rows))

    def test_rapport_signale_petit_echantillon(self):
        texte = ar.rapport(self._jeu())
        self.assertIn("Courses avec arrivée connue : 3", texte)
        self.assertIn("Échantillon trop petit", texte)

    def test_rapport_sans_arrivee(self):
        self.assertIn("Rien à analyser", ar.rapport([_ligne("2026-11-08", 1, None, 0.5)]))

    def test_famille(self):
        self.assertEqual(ar.famille("Plat"), "plat")
        self.assertEqual(ar.famille("Steeple Chase"), "obstacle")
        self.assertEqual(ar.famille("Haies"), "obstacle")
        self.assertEqual(ar.famille("Attelé"), "trot")


class TestVigilance(unittest.TestCase):
    def test_zones_a_deux_fois_d_ecart(self):
        import vigilance
        pm = {1: 0.5, 2: 0.3, 3: 0.2}
        pk = {1: 0.2, 2: 0.4, 3: 0.4}
        mefiance, surveiller = vigilance.zones(pm, pk)
        self.assertEqual(mefiance, [1])    # le modèle y croit 2,5 fois plus que le marché
        self.assertEqual(surveiller, [3])  # le marché y croit 2 fois plus que le modèle
        self.assertAlmostEqual(sum(vigilance.part_modele({1: 0.9, 2: 0.2}).values()), 1.0, places=9)

    def test_outsiders_non_signales(self):
        import vigilance
        # un outsider à 2 % pour le modèle contre 5 % pour le marché : écart de 2,5 fois, mais sans enjeu
        mefiance, surveiller = vigilance.zones({1: 0.02, 2: 0.5}, {1: 0.05, 2: 0.5})
        self.assertEqual(surveiller, [])
        self.assertEqual(mefiance, [])


class TestCaptureCotes(unittest.TestCase):
    def test_capture_des_cotes_avant_depart(self):
        chemin = os.path.join(tempfile.mkdtemp(), "registre.csv")
        c = _course()
        lignes, probs = journee._calcul(c)
        registre.ajouter(registre.lignes_de_course("2026-11-08", 1, 5, c, lignes, probs, None, "t"), chemin)
        self.assertEqual(registre.capturer_cotes("2026-11-08", 1, 5, {1: 4.0, 2: 6.5, 3: 9.0},
                                                 "2026-11-08T14:45", chemin), 3)
        self.assertEqual(registre.capturer_cotes("2026-11-08", 1, 5, {1: 3.5, 2: 6.0, 3: 8.0},
                                                 "2026-11-08T15:00", chemin), 3)
        rows = {r["numero"]: r for r in registre.lire(chemin)}
        self.assertEqual(rows["1"]["cote_depart"], "3.5")          # le dernier relevé remplace le précédent
        self.assertEqual(rows["1"]["heure_cote"], "2026-11-08T15:00")


class TestBlocsPage(unittest.TestCase):
    def test_blocs_de_vigilance_et_modele_seul(self):
        import rapport
        v = {"mefiance": [1], "surveiller": [3], "pm": {1: 0.5, 2: 0.3, 3: 0.2}, "pk": {1: 0.2, 2: 0.4, 3: 0.4},
             "noms": {1: "ALPHA", 2: "BETA", 3: "GAMMA"}, "cotes": {1: 5.0, 2: 2.5, 3: 2.5}}
        bloc = rapport._vigilance_html(v)
        self.assertIn("Méfiance", bloc)
        self.assertIn("ALPHA", bloc)
        self.assertIn("cote 5", bloc)
        self.assertIn("À surveiller", bloc)
        self.assertIn("70 % de cotes", bloc)
        self.assertEqual(rapport._vigilance_html(None), "")
        m = {"fige_le": "2026-11-08T08:10:49", "ordre": [1, 2], "noms": {1: "ALPHA", 2: "BETA"},
             "notes": {1: 0.87, 2: 0.74}}
        self.assertIn("09 h 10", rapport._modele_seul_html(m))


if __name__ == "__main__":
    unittest.main()
