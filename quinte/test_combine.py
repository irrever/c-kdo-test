"""Tests de l'avis combiné : règles de la dernière course, à jouer, à éviter, boîte de 6, et bloc de la page."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import combine  # noqa: E402


def ligne(n, musique, score):
    return {"numero": n, "nom": "CHEVAL %d" % n, "musique": musique, "score": score}


class TestDerniereCourse(unittest.TestCase):
    def test_places_et_incidents(self):
        self.assertEqual(combine.derniere_course("1p2p3p"), (1, False))
        self.assertEqual(combine.derniere_course("0p5p"), (0, False))
        self.assertEqual(combine.derniere_course("(25)3p"), (3, False))
        self.assertEqual(combine.derniere_course("Dp1p"), (None, True))
        self.assertEqual(combine.derniere_course(""), (None, False))


class TestAvis(unittest.TestCase):
    def setUp(self):
        self.lignes = [ligne(1, "1p", 0.9), ligne(2, "8p", 0.8), ligne(3, "2p", 0.7), ligne(4, "0p", 0.6),
                       ligne(5, "3p", 0.5), ligne(6, "5p", 0.4), ligne(7, "Tp", 0.3)]
        self.presse = {"parier": [2, 4], "cinq": None, "bases": [2], "belles": [4], "outsiders": [],
                       "delaisses": []}

    def test_a_jouer_et_a_eviter(self):
        a = combine.avis(self.lignes, self.presse)
        self.assertEqual(a["a_jouer"], [1, 3, 5])   # dernière course forte et écartés par la presse
        self.assertEqual(a["a_eviter"], [2, 4])     # retenus par la presse, dernière course hors des 4 premières
        self.assertEqual(a["top5"], [1, 2, 3, 4, 5])

    def test_boite(self):
        a = combine.avis(self.lignes, self.presse)
        self.assertEqual(a["box"], [1, 3, 5, 6, 7])  # notre top 5 sans les « à éviter », puis le reste

    def test_sans_presse_boite_top_6(self):
        a = combine.avis(self.lignes, None)
        self.assertEqual(a["box"], [1, 2, 3, 4, 5, 6])
        self.assertFalse(a["presse_disponible"])

    def test_boite_de_six_comme_le_choix_du_10_novembre(self):
        # notre top 5 : 5 8 6 10 12 ; la presse retient 16 14 7 9 2 1 8 5 ; 13 est écarté, dernière course 2e
        lignes = [ligne(5, "1p", 0.78), ligne(8, "1p", 0.74), ligne(6, "1p", 0.67), ligne(10, "2p", 0.65),
                  ligne(12, "3p", 0.62), ligne(13, "2p", 0.59), ligne(16, "8p", 0.48), ligne(14, "1p", 0.55),
                  ligne(7, "3p", 0.60), ligne(9, "2p", 0.58), ligne(2, "1p", 0.56), ligne(1, "9p", 0.54)]
        presse = {"parier": [16, 14, 7, 9, 2, 1, 8, 5], "cinq": None, "bases": [16, 14],
                  "belles": [7, 9, 2, 1, 8, 5], "outsiders": [15, 3, 10, 13, 11, 4, 12, 6], "delaisses": []}
        a = combine.avis(lignes, presse)
        self.assertEqual(a["box"], [5, 8, 6, 10, 12, 13])
        self.assertEqual(a["a_jouer"], [6, 10, 12, 13])
        self.assertEqual(a["a_eviter"], [16, 1])


class TestBlocPage(unittest.TestCase):
    def test_bloc_avis_dans_la_page(self):
        import rapport
        lignes = [ligne(1, "1p", 0.9), ligne(2, "0p", 0.5)]
        a = combine.avis(lignes, None)
        bloc = rapport._avis_html(a)
        self.assertIn("Notre avis combiné", bloc)
        self.assertIn("boîte de 2", bloc)
        self.assertEqual(rapport._avis_html(None), "")


if __name__ == "__main__":
    unittest.main()
