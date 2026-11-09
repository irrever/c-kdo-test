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
        self.assertIn("90 % de cotes", bloc)
        self.assertEqual(rapport._vigilance_html(None), "")
        m = {"fige_le": "2026-11-08T08:10:49", "ordre": [1, 2], "noms": {1: "ALPHA", 2: "BETA"},
             "notes": {1: 0.87, 2: 0.74}}
        self.assertIn("09 h 10", rapport._modele_seul_html(m))


class TestFond(unittest.TestCase):
    def test_choix_du_fond(self):
        import rapport
        bouton = rapport._bouton_fond_html()
        self.assertIn("fond-bouton", bouton)
        self.assertIn("quinte-fond", bouton)

    def test_ajout_aux_pages_publiees(self):
        import rapport
        page = ("<!doctype html><html><head><title>Quinté</title>\n<style>\nbody{}\n</style></head><body><main>"
                "<section>Entête</section>\n<div class='onglets' role='tablist'></div>\n"
                "<div class=\"vue\" data-vue=\"analyse\"></div></main></body></html>")
        avec = rapport.ajouter_fond(page)
        self.assertEqual(avec.count("id='fond-bouton'"), 1)
        self.assertEqual(rapport.ajouter_fond(avec), avec)  # une seconde passe ne change rien
        retire = avec.replace("\n" + rapport.FOND_TETE, "", 1).replace(rapport.FOND_CSS, "", 1)
        retire = retire.replace("<div class='fond-ligne'>" + rapport._bouton_fond_html() + "</div>\n", "", 1)
        self.assertEqual(retire, page)  # le reste de la page est intact


class TestSansDonnees(unittest.TestCase):
    def test_detection(self):
        import analyse_equidia as ae
        vide = [{"composantes": {"musique": None, "aptitudes": None}}] * 2
        self.assertTrue(ae.sans_donnees(vide))
        self.assertFalse(ae.sans_donnees([{"composantes": {"musique": 0.8, "aptitudes": None}}] + vide))
        self.assertFalse(ae.sans_donnees([]))

    def test_entree_sans_pronostic(self):
        course = {"conditions_txt_course": "Pour poulains de 2 ans.", "partants": [
            {"num_partant": 1, "cheval": {"nom_cheval": "DUTCHMAN"}},
            {"num_partant": 9, "cheval": {"nom_cheval": "THE PYRENEES"}}]}
        entree = journee._sans_pronostic(course, {9: 2.4, 1: 16.0}, "2026-11-08T11:01")
        self.assertTrue(entree["sans_donnees"])
        self.assertEqual((entree["ordre"], entree["top"]), ([], []))
        self.assertEqual(entree["cotes"], [{"numero": 1, "nom": "DUTCHMAN", "cote": 16.0},
                                           {"numero": 9, "nom": "THE PYRENEES", "cote": 2.4}])
        self.assertEqual(entree["conditions"], "Pour poulains de 2 ans.")
        self.assertEqual(entree["cotes_releve"], "2026-11-08T11:01")

    def test_marquage_et_exclusion(self):
        import analyse_equidia as ae
        chemin = os.path.join(tempfile.mkdtemp(), "registre.csv")
        partants = [_partant(n, nom, "", {}, 58, n, place=n, cote=cote)
                    for n, nom, cote in [(1, "ALPHA", 16.0), (2, "BETA", 5.7), (3, "GAMMA", 9.0)]]
        c = {"discipline": "Plat", "distance": 1500, "heure_depart_course": "12:48",
             "reunion": {"hippodrome": {"name": "SAINT-CLOUD"}}, "type_statut_course_id": "finished",
             "partants": partants}
        lignes, probs = journee._calcul(c)
        self.assertTrue(ae.sans_donnees(lignes))
        for r in (1, 2):
            registre.ajouter(registre.lignes_de_course("2026-11-08", r, 1, c, lignes, probs,
                                                       {1: 16.0, 2: 5.7, 3: 9.0}, "t"), chemin)
            registre.mettre_a_jour_arrivees("2026-11-08", r, 1, {1: 1, 2: 2, 3: 3}, chemin)
        self.assertEqual(registre.marquer_sans_donnees("2026-11-08", 1, 1, chemin), 3)
        self.assertEqual(registre.marquer_sans_donnees("2026-11-08", 1, 1, chemin), 0)  # déjà marquée
        texte = ar.rapport(registre.lire(chemin))
        self.assertIn("Courses avec arrivée connue : 1", texte)
        self.assertIn("exclues : 1", texte)

    def test_cotes_du_dernier_releve_pour_une_course_sans_pronostic(self):
        import json
        import datetime as dt
        from zoneinfo import ZoneInfo
        import analyse_equidia as ae
        dossier = tempfile.mkdtemp()
        avant, d_course, d_cotes = journee.JOURNAL, journee.eq.course, ae.cotes_de
        journee.JOURNAL = dossier
        try:
            with open(journee.fichier("2026-11-08"), "w", encoding="utf-8") as f:
                json.dump({"date": "2026-11-08", "courses": [
                    {"r": 1, "c": 1, "statut": "before", "heure": "12:48", "sans_donnees": True,
                     "ordre": [], "top": []},
                    {"r": 1, "c": 2, "statut": "before", "heure": "13:23", "ordre": [1], "top": []}]}, f)
            course = {"partants": [_partant(n, nom, "", {}, 58, n, cote=val)
                                   for n, nom, val in [(1, "ALPHA", 16.0), (2, "BETA", 5.7), (3, "GAMMA", 9.0)]]}
            journee.eq.course = lambda *a, **k: course
            ae.cotes_de = lambda c: {1: 4.0, 2: 6.5, 3: 9.0}
            maintenant = dt.datetime(2026, 11, 8, 12, 35, tzinfo=ZoneInfo("Europe/Paris"))
            self.assertEqual(journee.rafraichir_cotes_sans_donnees("2026-11-08", maintenant), 1)
            with open(journee.fichier("2026-11-08"), encoding="utf-8") as f:
                courses = json.load(f)["courses"]
            self.assertEqual(courses[0]["cotes_releve"], "2026-11-08T12:35")
            self.assertEqual([h["cote"] for h in courses[0]["cotes"]], [4.0, 6.5, 9.0])
            self.assertNotIn("cotes", courses[1])  # une course avec pronostic n'est pas touchée
        finally:
            journee.eq.course, ae.cotes_de = d_course, d_cotes
            journee.JOURNAL = avant


class TestRattrapage(unittest.TestCase):
    def test_cotes_reprises_sans_toucher_aux_cotes_captees(self):
        chemin = os.path.join(tempfile.mkdtemp(), "registre.csv")
        c = _course()
        lignes, probs = journee._calcul(c)
        registre.ajouter(registre.lignes_de_course("2026-11-08", 1, 6, c, lignes, probs, None, "t"), chemin)
        registre.ajouter(registre.lignes_de_course("2026-11-08", 1, 7, c, lignes, probs, None, "t"), chemin)
        registre.capturer_cotes("2026-11-08", 1, 7, {1: 3.5, 2: 6.0, 3: 8.0}, "2026-11-08T14:50", chemin)
        self.assertEqual(registre.completer_cotes("2026-11-08", 1, 6, {1: 4.0, 2: 6.0, 3: 9.0}, chemin), 3)
        self.assertEqual(registre.completer_cotes("2026-11-08", 1, 7, {1: 4.0, 2: 6.0, 3: 9.0}, chemin), 0)
        lues = registre.lire(chemin)
        reprises = {x["numero"]: (x["cote_depart"], x["heure_cote"]) for x in lues if x["c"] == "6"}
        self.assertEqual(reprises["1"], ("4.0", "reprise"))
        captees = {x["cote_depart"] for x in lues if x["c"] == "7"}
        self.assertEqual(captees, {"3.5", "6.0", "8.0"})

    def test_rapports_officiels(self):
        chemin = os.path.join(tempfile.mkdtemp(), "registre.csv")
        c = _course()
        lignes, probs = journee._calcul(c)
        registre.ajouter(registre.lignes_de_course("2026-11-08", 1, 6, c, lignes, probs, None, "t"), chemin)
        rapports = {"gagnant": {1: 1.2}, "place": {1: 1.05, 2: 2.1}}
        self.assertEqual(registre.inscrire_rapports("2026-11-08", 1, 6, rapports, chemin), 3)
        self.assertEqual(registre.inscrire_rapports("2026-11-08", 1, 6, rapports, chemin), 0)
        par_numero = {x["numero"]: x for x in registre.lire(chemin)}
        self.assertEqual((par_numero["1"]["rapport_gagnant"], par_numero["1"]["rapport_place"]), ("1.2", "1.05"))
        self.assertEqual((par_numero["2"]["rapport_gagnant"], par_numero["2"]["rapport_place"]), ("", "2.1"))


class TestRapportsSimples(unittest.TestCase):
    def test_lecture_des_rapports(self):
        import equidia
        page = ('<script>var r=[{"place":"1,05","gagnant":"1,20","combinaison_rap_def":"5","type_reserve_rap_def":"Simple"},'
                '{"place":"2,10","combinaison_rap_def":"2","type_reserve_rap_def":"Simple"},'
                '{"gagnant":"9,50","combinaison_rap_def":"3-4","type_reserve_rap_def":"Couplé"}];</script>')
        self.assertEqual(equidia.rapports_simples(page), {"gagnant": {5: 1.2}, "place": {5: 1.05, 2: 2.1}})
        self.assertEqual(equidia._montant("1.234,50"), 1234.5)


class TestConstat(unittest.TestCase):
    def test_variantes_et_gains(self):
        import constat
        c = {"n": 3, "famille": "plat", "scores": {"1": 0.9, "2": 0.5, "3": 0.2}, "p_registre": {},
             "cotes": {"1": 2.0, "2": 4.0, "3": 9.0}, "sources": {"captée"}, "gagnant": "1",
             "placés": {"1", "2", "3"}, "rg": 1.6, "rp": {"1": 1.1, "2": 1.9, "3": 3.0}}
        self.assertAlmostEqual(sum(constat._proba_modele(c["scores"], 8.0).values()), 1.0)
        perte, top1, top3, gain_g, gain_p = constat.evaluer([c], "modele")[0]
        self.assertEqual((top1, top3), (1.0, 1.0))  # le modèle désigne le vainqueur
        self.assertAlmostEqual(gain_g, 1.6)
        self.assertAlmostEqual(gain_p, 1.1)
        self.assertAlmostEqual(constat.evaluer([c], "hasard")[0][3], 1.6 / 3)


class TestFinalAvecCotes(unittest.TestCase):
    def test_poids_des_cotes_selon_la_discipline(self):
        import analyse_equidia as ae
        self.assertEqual(ae.poids_cotes_pour("Attelé"), 1.0)  # au trot, les cotes seules
        self.assertEqual(ae.poids_cotes_pour("Monté"), 1.0)
        self.assertEqual(ae.poids_cotes_pour("Plat"), ae.COTES_POIDS)

    def test_pronostic_final_fige_une_fois_dans_la_fenetre(self):
        import datetime as dt
        import json
        from unittest import mock
        import analyse_equidia as ae
        dossier = tempfile.mkdtemp()
        courses = [
            {"r": 1, "c": 4, "statut": "before", "heure": "13:10", "sans_donnees": False, "ordre": [9, 8, 7, 6, 5], "top": []},
            {"r": 1, "c": 5, "statut": "before", "heure": "15:00", "sans_donnees": False, "ordre": [1], "top": []},
        ]
        chemin = os.path.join(dossier, "2026-11-07-journee.json")
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump({"date": "2026-11-07", "courses": courses}, f)
        maintenant = dt.datetime(2026, 11, 7, 12, 20, tzinfo=journee.PARIS)
        with mock.patch.object(journee, "JOURNAL", dossier), mock.patch.object(journee, "SIMULATIONS", 2000), \
                mock.patch.object(journee.eq, "course", return_value=_course()):
            self.assertEqual(journee.figer_finaux("2026-11-07", maintenant), 1)  # seule la course de 13 h 10 est dans la fenêtre
            self.assertEqual(journee.figer_finaux("2026-11-07", maintenant), 0)  # figée une seule fois
        with open(chemin, encoding="utf-8") as f:
            lues = {x["c"]: x for x in json.load(f)["courses"]}
        self.assertEqual(set(lues[4]["ordre"]), {1, 2, 3})
        self.assertEqual(lues[4]["final"], {"fige_le": "2026-11-07T12:20", "part_cotes": ae.COTES_POIDS})
        self.assertNotIn("final", lues[5])
        self.assertEqual(lues[5]["ordre"], [1])


def _ligne_bilan(numero, score, cote, arrivee, rg=None, rp=None):
    ligne = {champ: "" for champ in registre.CHAMPS}
    ligne.update({"date": "2026-11-08", "r": "1", "c": "1", "discipline": "Plat", "distance": "1900",
                  "partants": "3", "numero": str(numero), "nom": "H%d" % numero, "hippodrome": "X", "heure": "13:00",
                  "calcule_le": "2026-11-08T23:07", "score": str(score), "rang": str(numero), "p_victoire": "0.5",
                  "cote_depart": str(cote), "heure_cote": "reprise", "arrivee": str(arrivee)})
    if rg:
        ligne["rapport_gagnant"] = str(rg)
    if rp:
        ligne["rapport_place"] = str(rp)
    return ligne


class TestBilanJour(unittest.TestCase):
    def test_bilan_du_jour(self):
        import constat
        lignes = [_ligne_bilan(1, 0.9, 2.0, 1, rg=1.6, rp=1.1), _ligne_bilan(2, 0.5, 4.0, 2, rp=1.9),
                  _ligne_bilan(3, 0.2, 9.0, 3, rp=3.0)]
        texte = constat.bilan_jour("2026-11-08", entrees=[{"r": 1, "c": 1, "ordre": [1, 2, 3]}], lignes=lignes)
        self.assertIn("| Ce qui était affiché |", texte)
        self.assertIn("100,0 %", texte)  # le n° 1 affiché gagne
        self.assertIn("1 / 1", texte)  # le vainqueur est 1er à la fois dans l'affiché et dans le nouveau réglage


if __name__ == "__main__":
    unittest.main()
