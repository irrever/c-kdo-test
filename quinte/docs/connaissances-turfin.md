# Connaissances tirées de Turfin (à valider sur nos données)

Source : pages publiques de turfin.fr (méthode et études Turfin Data), relevées le 4 novembre 2026.
Ces chiffres sont ceux publiés par Turfin. Ce sont des hypothèses : nous ne les reprenons dans le modèle qu'après les avoir vérifiées sur nos propres courses passées (`quinte/backtest.py`, `quinte/evaluer.py`).

## 1. Méthode de notation de Turfin

Note sur 100 = 0,92 × qualité + 0,08 × cote du matin. Nous n'utilisons pas la cote.

Poids dans la qualité :

| Critère | Poids | Contenu |
|---|---|---|
| Entourage | 41 % | Driver ou jockey et entraîneur, sur ce type d'épreuve, forme des 7 derniers jours, niveau ELO |
| Forme | 30 % | Places récentes, adversaires battus, valeur des courses (allocation) |
| Aptitude | 24 % | Distance, discipline, terrain, hippodrome, corde, déferrage (+ bonus) |
| Régularité | 5 % | Fréquence des places, proche de la forme |

Points à retenir :
- L'avis officiel de l'entraîneur (confiant ou réservé, au trot) pèse directement sur les chances.
- La confiance baisse quand les données sont incomplètes ou contradictoires.
- Si un partant manque de courses, toute la course est lue à la musique.

## 2. Ce que disent les études (Turfin Data)

| Étude | Résultat principal | Lecture pour nous |
|---|---|---|
| Favori | Gagne 36 % (67,9 % dans les 3 premiers). Dans un peloton de 8 ou moins : 43,9 %. À 16 partants et plus : 20 %. Plat : 29,6 %. Trot attelé : 40,5 %. | Un favori « de base » fort, très dépendant de la taille du peloton et de la discipline. |
| Corde (plat) | Brut : corde 2 gagne 10,7 %, corde 15 gagne 5,2 %. À taille de peloton comparable, l'écart est presque nul (13,5 % contre 9,7 % en petit peloton). | L'écart brut vient de la taille du peloton, pas de la corde. |
| Déferrage (trot) | Déferré des 4 pieds pour la première fois : 13,4 % de victoires, contre 8,2 % pour un cheval ferré. L'effet est surtout chez les outsiders. | Signal possible, à tester en comparant à cote comparable. |
| Referrage (trot) | Qui remet ses fers après avoir été déferré : 2,9 % de victoires, contre 9,5 % pour un cheval déjà ferré. Chez les outsiders : 0,9 % contre 2,5 %. | Signal le plus net de leurs études. À tester en priorité. |
| Œillères (plat) | Pas d'effet à cote comparable : 9,2 % avec, 10,2 % sans chez les intermédiaires. | Ne pas ajouter ce critère. |

## 3. Écarts avec notre modèle actuel

- **Entourage** : nous ne lui donnons que 10 % (tandem driver-entraîneur de la fiche Equidia). Turfin lui donne 41 %, avec la forme récente de l'entourage et son niveau ELO. À tester : une forme récente du driver et de l'entraîneur, calculée à partir des courses passées de notre jeu de données.
- **Taille du peloton** : nos probabilités ne tiennent pas compte de la taille du peloton. Le favori gagne 20 % à 16 partants et plus, contre 44 % à 8 et moins. À tester : un facteur de dispersion selon le nombre de partants.
- **Avis de l'entraîneur** : on l'affiche dans les raisons, mais il n'entre pas dans les pourcentages. À tester.
- **Déferrage, referrage et première fois** : absents des pourcentages. Les données de la fiche Equidia contiennent déferrage et première fois. Le referrage demande la ferrure de la course précédente, à reconstituer depuis les pages des courses passées.
- **Calibrage** : nos probabilités sont très aplaties (favori à environ 16 % de victoire), alors que le favori du marché gagne environ 36 % (chiffre Turfin, toutes courses). Le modèle n'utilise pas la cote, donc ces deux chiffres ne sont pas comparables directement. À vérifier avant d'utiliser le modèle pour parier.

## 4. Prochaines vérifications prévues

1. Ajouter au jeu de données du backtest : ferrure, déferrage, première fois, avis de l'entraîneur, nombre de partants.
2. Tester le referrage et l'avis de l'entraîneur sur nos 30 courses passées, avec la même séparation entraînement / test.
3. Tester un poids plus fort pour l'entourage (forme récente driver et entraîneur).
4. Tester la taille du peloton comme facteur d'aplatissement des probabilités.
5. Ne garder que les changements qui améliorent la log-loss sur les courses de test.
