"""Tests du mouvement des cotes sur le quinté."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mouvement  # noqa: E402


class TestMouvement(unittest.TestCase):
    def test_nombre(self):
        self.assertEqual(mouvement._nombre("4,9"), None)
        self.assertEqual(mouvement._nombre("4.9"), 4.9)
        self.assertIsNone(mouvement._nombre(""))
        self.assertIsNone(mouvement._nombre("0"))
        self.assertIsNone(mouvement._nombre(None))

    def test_ecrire_jour_remplace_le_jour(self):
        with tempfile.TemporaryDirectory() as d:
            chemin = os.path.join(d, "mouvement.csv")
            un = [{"date": "2026-11-08", "r": 1, "c": 5, "numero": 7, "cote_gel": 5.2, "cote_depart": 4.9,
                   "arrivee": "1"}]
            mouvement.ecrire_jour(un, "2026-11-08", chemin)
            mouvement.ecrire_jour(un + [dict(un[0], numero=1, arrivee="2")], "2026-11-08", chemin)
            lus = mouvement._lire(chemin)
            self.assertEqual(len(lus), 2)            # relancer le même jour ne double pas les lignes
            autre = [dict(un[0], date="2026-11-09", r=1, c=2)]
            mouvement.ecrire_jour(autre, "2026-11-09", chemin)
            self.assertEqual(len(mouvement._lire(chemin)), 3)   # les autres jours sont gardés


if __name__ == "__main__":
    unittest.main()
