"""Tests du pronostic de la presse : lecture des pages Equidia et comparaison des classements."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import presse  # noqa: E402

# Extraits réels des pages Equidia (8 et 9 novembre, après la course ; 10 novembre, avant la course).
PAGE_8 = ("<div>Pronostic Quinté d'Equidia Par FREDDY BOERSCH 7 ORAGEUX 1 DON'T SHUT ME DOWN 10 DARK ROCKSTER "
          "9 PAOLINO 8 RAM SEA Bases : 7 - 1 Outsiders : 6 - 4 - 3 - 13 - 15 - 12 - 2 Belles chances : "
          "10 - 9 - 8 - 5 - 11 - 14 Délaissés : Arrivée définitive 7 1 10 11 4</div>")
PAGE_9 = ("<div>Pronostic Quinté d'Equidia du jour Par FREDDY BOERSCH 5 KEROSEN DU GERS 4 NELSON GREENWOOD "
          "13 ICARE DU BERYL 6 KASSIOPEE WIND 11 GERICAULT Bases : 5 - 4 Outsiders : 7 - 3 - 14 - 9 "
          "Belles chances : 13 - 6 - 11 - 15 - 10 - 12 Délaissés : 1 - 2 - 8 Arrivée définitive 5 6 15 13 10</div>")
PAGE_10 = ("<div>Pronostic Quinté d'Equidia de demain Par FREDDY BOERSCH Parier avec : 16 FATA MORGANA 14 ALPARSLAN "
           "7 PRINCE AUBOIS 9 SCHUMAN 2 INTERACTIV 1 LESSLEPASSER 8 KHALINSKHA 5 MARBELLESA Bases : 16 - 14 "
           "Outsiders : 15 - 3 - 10 - 13 - 11 - 4 - 12 - 6 Belles chances : 7 - 9 - 2 - 1 - 8 - 5 Délaissés : "
           "Notre avis : FATA MORGANA (16) Surprenante deuxième dans le Quinté+ du 15 août.</div>")


class TestLirePronostic(unittest.TestCase):
    def test_cinq_et_categories(self):
        p = presse.lire_pronostic(PAGE_8)
        self.assertEqual(p["cinq"], [7, 1, 10, 9, 8])
        self.assertIsNone(p["parier"])
        self.assertEqual(p["bases"], [7, 1])
        self.assertEqual(p["outsiders"], [6, 4, 3, 13, 15, 12, 2])
        self.assertEqual(p["belles"], [10, 9, 8, 5, 11, 14])
        self.assertEqual(p["delaisses"], [])

    def test_cinq_avec_delaisses(self):
        p = presse.lire_pronostic(PAGE_9)
        self.assertEqual(p["cinq"], [5, 4, 13, 6, 11])
        self.assertEqual(p["outsiders"], [7, 3, 14, 9])
        self.assertEqual(p["delaisses"], [1, 2, 8])

    def test_boite_parier_avec(self):
        p = presse.lire_pronostic(PAGE_10)
        self.assertEqual(p["parier"], [16, 14, 7, 9, 2, 1, 8, 5])
        self.assertIsNone(p["cinq"])
        self.assertEqual(p["bases"], [16, 14])
        self.assertEqual(p["belles"], [7, 9, 2, 1, 8, 5])
        self.assertEqual(p["delaisses"], [])

    def test_pas_de_pronostic(self):
        self.assertIsNone(presse.lire_pronostic("<p>Rien à voir ici.</p>"))

    def test_numero_en_double_refuse(self):
        with self.assertRaises(ValueError):
            presse.lire_pronostic("<p>Pronostic Quinté Par X 7 A 1 B Bases : 7 - 1 Outsiders : 7 - 3 "
                                  "Belles chances : Délaissés :</p>")


class TestClassement(unittest.TestCase):
    def test_ordre_de_la_presse(self):
        p = presse.lire_pronostic(PAGE_8)
        self.assertEqual(presse.ordre_presse(p)[:8], [7, 1, 10, 9, 8, 5, 11, 14])
        self.assertEqual(presse.categorie(p, 10), "belle")
        self.assertEqual(presse.categorie(p, 4), "outsider")
        self.assertEqual(presse.categorie(p, 99), "—")

    def test_boite_et_couverture(self):
        ordre = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        self.assertEqual(presse.mesures(ordre, [1, 3, 5, 7, 9]), (4, 9))
        self.assertEqual(presse.mesures(ordre, [1, 2, 3, 4, 5]), (5, 5))


class TestDiagnostic(unittest.TestCase):
    def test_erreurs(self):
        self.assertEqual(presse.erreurs([7, 1, 10, 9, 8], [7, 1, 10, 11, 4]), ([4, 11], [8, 9]))

    def test_categories(self):
        p = presse.lire_pronostic(PAGE_8)
        cat = presse._categories(p)
        self.assertEqual(cat[7], "base")
        self.assertEqual(cat[10], "belle")
        self.assertEqual(cat[4], "outsider")


if __name__ == "__main__":
    unittest.main()
