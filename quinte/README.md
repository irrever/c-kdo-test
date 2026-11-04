# Analyse du quinté

Application statique (HTML + JavaScript, sans dépendance) qui note la **performance** des chevaux d'une course et propose un pronostic et un jeu conseillé.

Les cotes ne sont jamais utilisées pour le calcul.

## Lancer l'application

Ouvrir `index.html` via un petit serveur web (le bouton « Charger l'exemple » en a besoin) :

```bash
cd quinte
python3 -m http.server 8000
```

Puis ouvrir http://localhost:8000. Coller le JSON de la course ou ouvrir un fichier `.json`, puis « Analyser la course ».

## Tests

```bash
node --test quinte/engine.test.js
```

## Format des données

Un seul objet JSON par course :

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `date` | `AAAA-MM-JJ` | non | Date de la course (sert au calcul de fraîcheur) |
| `hippodrome` | texte | non | Nom de l'hippodrome |
| `discipline` | texte | non | `plat`, `trot attelé`, `trot monté`, `haies`, `steeple`, `cross`… |
| `distance` | nombre | non | Distance en mètres |
| `terrain` | texte | non | Ex. `bon`, `souple`, `collant`, `lourd` |
| `corde` | texte | non | `droite` ou `gauche` |
| `partants` | liste | **oui** (au moins 2) | Voir ci-dessous |

Chaque partant :

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `numero` | nombre | **oui** | Numéro de corde/dossard, unique |
| `nom` | texte | **oui** | Nom du cheval |
| `historique` | liste | non | Courses passées (voir ci-dessous) |

Chaque course passée de `historique` :

| Champ | Type | Description |
|---|---|---|
| `date` | `AAAA-MM-JJ` | Date de la course |
| `hippodrome`, `distance`, `terrain`, `corde`, `discipline` | comme ci-dessus | Conditions de la course passée |
| `place` | nombre ou texte | Arrivée. Un texte non numérique (`D`, `T`, `A`…) compte comme non classé |
| `partants` | nombre | Nombre de partants de cette course |

Un champ `cote` présent dans les données est ignoré.

Exemple complet : `exemple-course.json` (données **fictives**).

## Méthode de notation

Chaque cheval reçoit une note de 0 à 100, moyenne pondérée de sept critères :

| Critère | Poids | Calcul |
|---|---|---|
| Forme récente | 30 % | 8 dernières courses, pondérées par la récence (x0,85 par course en remontant). Une arrivée vaut 1 pour la victoire, 0 pour un non-classé, et décroît linéairement entre les deux |
| Régularité | 10 % | Part des arrivées dans le top 3 |
| Terrain | 15 % | Courses sur la même famille de terrain (sec / intermédiaire / lourd) |
| Distance | 15 % | Courses à ± 150 m de la distance de la course |
| Corde | 10 % | Courses sur la même corde |
| Hippodrome | 5 % | Courses sur le même hippodrome |
| Fraîcheur | 5 % | Jours depuis la dernière course (optimum entre 15 et 60 jours) |

Une donnée absente compte pour 0,5 (neutre) et le cheval est signalé. La confiance est « faible » sous 3 courses, « élevée » à partir de 5 courses avec des données sur la plupart des critères.

## Pronostic et jeu

- **Ordre d'arrivée probable** : les 5 premiers par note.
- **À surveiller** : les chevaux 6 et 7.
- **Jeu conseillé** :
  - si le 1er se détache du 2e d'au moins 8 points et a une note ≥ 60 : simple gagnant (alternative : couplé 1er–2e) ;
  - sinon : trio désordre en box sur les 4 premiers (alternative : quinté+ désordre sur les 5 premiers).

Les seuils sont dans `engine.js` (`SEUIL_MARGE_NETTE`, `POIDS`, `TOLERANCE_DISTANCE`, `DECROISSANCE`) et peuvent être ajustés.

## Limites

- L'application ne récupère pas les données elle-même : il faut fournir le JSON de la course (depuis un export, une saisie ou un script à écrire).
- Une note reflète les performances passées. Elle ne garantit aucun résultat.
- Les jeux comportent des risques. Jeu responsable, interdit aux mineurs.
