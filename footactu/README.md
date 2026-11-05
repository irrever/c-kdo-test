# footactu : collecte et analyse automatique des blessures

`collect.py` lit l'API WordPress publique de footactu.com (`/wp-json/wp/v2/`), récupère les articles, classe ceux
qui parlent d'une blessure et produit une analyse.

## Utilisation

```bash
python3 footactu/collect.py           # mise à jour incrémentale (articles modifiés depuis le dernier run)
python3 footactu/collect.py --full    # re-crawl complet des ~6 000 articles (environ 1 min 30 à 0,3 s de délai)
```

Python 3.10 ou plus, bibliothèque standard uniquement.

## Données produites (`footactu/data/`)

| Fichier | Contenu |
|---|---|
| `articles.json` | Tous les articles, indexés par id WordPress. Le texte intégral n'est gardé que pour les articles blessures. |
| `injuries.json` | Les articles classés blessure, avec les types de blessure détectés. |
| `report.md` | Analyse : volume par mois, types de blessure, rubriques (compétitions/équipes), 40 cas récents. |
| `state.json` | Date du dernier run et date de modification la plus récente vue (pour l'incrémental). |

## Classement

Un article est classé « blessure » si le titre ou le chapeau contient un terme fort (blessure, blessé, indisponible,
infirmerie, entorse, claquage, pubalgie, forfait lié à un match, rupture de ligament ou de tendon), ou si ce terme
apparaît au moins deux fois dans le corps. Le type de blessure vient d'une liste de mots-clés (`INJURY_TYPES`).

Limites connues : quelques faux positifs (articles où le mot « blessure » est employé au sens figuré) et des types
« non précisé » quand l'article ne nomme pas la zone touchée.

## Automatisation

Le workflow `.github/workflows/footactu-injuries.yml` tourne chaque jour à 06:17 UTC, fait une mise à jour
incrémentale et commit `footactu/data/` si quelque chose a changé. Il peut aussi être lancé à la main, avec
l'option « full » pour un re-crawl complet.

Note : `articles.json` pèse environ 4 Mo et sera re-commité à chaque changement. Si l'historique git grossit trop,
on peut déplacer les données vers un stockage dédié (branche séparée, bucket, base de données).

## Respect du site

- `robots.txt` n'interdit pas `wp-json`.
- Requêtes séquentielles avec délai, réessai avec backoff sur 429 et 5xx.
- User-Agent explicite et générique.
