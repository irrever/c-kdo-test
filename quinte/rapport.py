#!/usr/bin/env python3
"""Génère la page HTML d'analyse et de pronostic d'une course Equidia.

Usage :
    python3 quinte/rapport.py page_equidia.html sortie.html

Réutilise le modèle de analyse_equidia.py (notes Equidia, sans cotes). Pour chaque cheval,
ajoute les raisons tirées de la fiche. Ajoute aussi le détail des combinaisons de
tiercé, quarté et quinté (y compris les quintés de plus de 5 chevaux).
"""
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyse_equidia as ae  # noqa: E402

GABARIT = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@titre_page@@</title>
<style>
:root{color-scheme:light;
  --bg:#f5f6f8;--surface:#ffffff;--line:#e3e6ec;--text:#1b2230;--muted:#667085;
  --or:#1f3a5f;--or-bg:#e9eef5;--bleu:#1f3a5f;--bleu-bg:#e9eef5;
  --vert:#1f3a5f;--vert-bg:#e9eef5;--violet:#1f3a5f;--violet-bg:#e9eef5;
  --rouge:#8a3b3b;--rouge-bg:#f7ecec;--gris:#667085;--gris-bg:#f1f3f6;}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;
  padding:0 max(16px,env(safe-area-inset-right,0px)) 40px max(16px,env(safe-area-inset-left,0px))}
main{max-width:1120px;margin:0 auto;padding-top:20px}
.hero{background:var(--surface);color:var(--text);border-radius:8px;padding:20px 22px;margin-bottom:14px;border:1px solid var(--line);border-left:3px solid var(--bleu)}
.hero h1{font-size:22px;margin:0 0 6px}
.hero p{margin:0;opacity:.92}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.chip{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.22);border-radius:4px;padding:2px 9px;font-size:12px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:18px;margin-bottom:14px}
.card.accent-or{border-left:3px solid var(--or)}
.card.accent-bleu{border-left:3px solid var(--bleu)}
.card.accent-vert{border-left:3px solid var(--vert)}
.card.accent-violet{border-left:3px solid var(--violet)}
.card.accent-gris{border-left:3px solid var(--gris)}
h2{font-size:17px;margin:0 0 10px}
.label{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:700}
.ordre{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}
.pastille{min-width:44px;height:44px;padding:0 10px;display:inline-flex;align-items:center;justify-content:center;border-radius:6px;font-weight:700;font-size:16px;color:var(--text);background:var(--surface);border:1px solid var(--line)}
.zones{position:sticky;top:0;z-index:5;background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:6px;margin-bottom:14px;display:flex;gap:4px;overflow-x:auto;white-space:nowrap}
.zones a{color:var(--bleu);text-decoration:none;font-size:13px;font-weight:600;padding:5px 10px;border-radius:6px}
.zones a:hover{background:var(--bleu-bg)}
section{scroll-margin-top:64px}
.pastille.r1{background:var(--bleu);color:#ffffff;border-color:var(--bleu)}
.pastille.r2{border-color:var(--bleu)}
.pastille.box{background:var(--violet)}
.pastille.gris{background:var(--gris)}
.jeu-titre{font-size:19px;font-weight:700;color:var(--text)}
.note{color:var(--muted);font-size:13px;margin:6px 0}
.wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:9px 6px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
th{color:var(--muted);font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tr.favori td{background:var(--bleu-bg)}
tr.top2 td{background:var(--gris-bg)}
.barre{height:8px;border-radius:999px;background:var(--gris-bg);overflow:hidden;min-width:90px}
.barre span{display:block;height:100%;border-radius:999px;background:var(--bleu)}
.tag{display:inline-block;font-size:12px;border-radius:999px;padding:1px 9px;margin:2px 4px 2px 0}
.tag.ok{background:var(--gris-bg);color:var(--text)}
.tag.ko{background:var(--rouge-bg);color:var(--rouge)}
.tag.info{background:var(--gris-bg);color:var(--muted)}
.tag.box{background:var(--bleu-bg);color:var(--bleu);border:1px solid var(--bleu)}
details{border-bottom:1px solid var(--line);padding:10px 0}
summary{cursor:pointer;font-weight:700}
details ul{margin:8px 0 0;padding-left:18px;font-size:14px}
details li{margin-bottom:6px}
.etapes{counter-reset:etape;list-style:none;padding:0;margin:0}
.etapes li{counter-increment:etape;position:relative;padding:6px 0 6px 38px;margin-bottom:4px}
.etapes li::before{content:counter(etape);position:absolute;left:0;top:4px;width:26px;height:26px;border-radius:50%;background:var(--violet);color:#fff;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:13px}
.rec{display:grid;grid-template-columns:1fr;gap:12px}
@media (min-width:640px){.rec{grid-template-columns:repeat(3,1fr)}}
.rec .bloc{border:1px solid var(--line);border-radius:12px;padding:12px;background:var(--surface)}
.rec .bloc.reco{border:1px solid var(--bleu);background:var(--bleu-bg)}
.rec .gros{font-size:22px;font-weight:800}
.foot{color:var(--muted);font-size:12px;margin-top:8px}

.bloc-pari{margin-bottom:18px}
.bloc-pari h3{font-size:14px;font-weight:600;margin:0 0 8px;color:var(--text)}
.numeros{display:flex;flex-wrap:wrap;gap:4px}
.num-box{display:inline-block;min-width:24px;text-align:center;padding:2px 6px;border:1px solid var(--line);border-radius:4px;font-size:12.5px;font-variant-numeric:tabular-nums}
tr.reco td{background:var(--bleu-bg)}
tr.reco .num-box{border-color:var(--bleu);color:var(--bleu);font-weight:600}
.numeros{display:flex;flex-wrap:wrap;gap:4px;min-width:120px}
@media (max-width:820px){.opt{display:none}.num-box{min-width:20px;padding:1px 4px;font-size:11.5px}.bloc-pari td,.bloc-pari th{padding:6px 3px;font-size:12px}.bloc-pari .numeros{min-width:0;gap:3px}.bloc-pari th{font-size:10px;letter-spacing:.04em}}


.layout{max-width:1120px;margin:0 auto;display:grid;grid-template-columns:200px minmax(0,1fr);gap:24px;padding-top:20px}
nav.side{position:sticky;top:12px;align-self:start}
nav.side .grp{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:14px 10px 4px}
nav.side .grp:first-child{margin-top:0}
nav.side a{display:block;color:var(--muted);text-decoration:none;font-size:14px;padding:7px 10px;border-left:2px solid transparent}
nav.side a:hover,nav.side a:focus-visible{color:var(--text);border-left-color:var(--bleu)}
@media (max-width:820px){.layout{grid-template-columns:minmax(0,1fr)}.contenu{min-width:0}nav.side{position:static;display:flex;flex-wrap:wrap;gap:4px;min-width:0}nav.side .grp{display:none}nav.side a{border-left:0;border-bottom:2px solid transparent;padding:6px 8px}}
section{scroll-margin-top:16px}

.profil{padding-left:22px;margin:0}.profil li{margin-bottom:10px}

/* Raffinement : typographie fine et espacements précis */
body{font-feature-settings:"ss01","cv11";-webkit-font-smoothing:antialiased}
h1{font-size:21px;font-weight:600;letter-spacing:-.01em}
h2{font-size:15px;font-weight:600;letter-spacing:-.005em}
.label{font-size:11px;font-weight:600;letter-spacing:.09em}
.card{border-radius:6px;padding:18px 18px 16px;box-shadow:0 1px 1px rgba(16,24,40,.03)}
.card.accent-bleu,.card.accent-or,.card.accent-gris,.card.accent-violet{border-left-width:2px}
.pastille{min-width:40px;height:40px;font-size:15px;font-weight:600;border-radius:6px}
.note{font-size:12.5px;line-height:1.55}
table{font-size:13px}
th{font-size:10.5px;letter-spacing:.08em}
td,th{padding:8px 6px}
.tag{font-size:11px;padding:1px 7px;border-radius:3px;letter-spacing:.01em}
.hero{padding:18px 20px;box-shadow:0 1px 1px rgba(16,24,40,.04)}
.hero h1{font-size:19px;font-weight:600}
.chip{border-radius:3px;font-size:11.5px}
@media (max-width:820px){
  body{font-size:14px;padding-top:0}
  .layout{padding-top:12px;gap:14px}
  nav.side{display:flex;flex-wrap:nowrap;overflow-x:auto;gap:6px;margin:0 -16px;padding:2px 16px 8px;scrollbar-width:none;-webkit-overflow-scrolling:touch}
  nav.side::-webkit-scrollbar{display:none}
  nav.side a{flex:0 0 auto;border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:12.5px;background:var(--surface);white-space:nowrap}
  nav.side a:hover{border-color:var(--bleu);color:var(--bleu);border-left-color:var(--line)}
  .card{padding:16px 15px 14px;margin-bottom:12px}
  .pastille{min-width:36px;height:36px;font-size:14px}
  .ordre{gap:6px}
  .hero{padding:16px 16px;margin-bottom:12px}
  .hero h1{font-size:17px;line-height:1.3}
  .hero p{font-size:12.5px}
  .chips{gap:5px}
  td,th{padding:7px 4px;font-size:12.5px}
  .note{font-size:12px}
}
</style></head><body><main>

<section class="card accent-bleu">
  <div class="label">1 · Quinté+ : les 5 premiers</div>
  <h2>Ordre d'arrivée probable</h2>
  <div class="ordre">@@ordre@@</div>
  <p class="note">Le favori du modèle est <strong>n°@@fav_num@@ @@fav_nom@@</strong> : @@fav_win@@ de chances de gagner, @@fav_top3@@ dans les trois premiers. Les chevaux 2 à 5 sont proches : la course reste ouverte.</p>
</section>
<section class="card accent-gris wrap">
  <div class="label">2 · Analyse des chevaux</div>
  <h2>Probabilités par cheval</h2>
  <table>
    <thead><tr><th>#</th><th class="num">N°</th><th>Cheval</th><th>Driver</th><th class="num">Note</th><th>1er</th><th>Top 3</th><th class="num">Top 5</th></tr></thead>
    <tbody>@@lignes@@</tbody>
  </table>
</section>
<section class="card accent-bleu">
  <div class="label">3 · Tiercé, quarté et quinté</div>
  <div class="jeu-titre">@@jeu_type@@</div>
  <p class="note">@@jeu_sel@@</p>
  <h2 style="margin-top:14px">Ce que je jouerais par type de pari</h2>
  <div class="rec">@@recommandations@@</div>
  <p class="note">Recommandation : la taille de box la plus probable, dans une limite de @@budget@@ combinaisons par pari.</p>
</section>
<section class="card accent-violet">
  <div class="label">3.1 · Combinaisons en box</div>
  <h2>Tiercé, quarté et quinté en box</h2>
  <p class="note">Un box de k chevaux gagne si les N premiers de l'arrivée sont tous dans le box (désordre). Le nombre de combinaisons est C(k, N). Le quinté en box de 6 à 9 chevaux est le cas des « quintés de plus de 5 chevaux ». L'ordre exact du quinté reste très improbable.</p>
  @@combinaisons@@
  <p class="foot">Probabilités estimées par simulation. Elles ne tiennent pas compte des rapports (gains) : une combinaison très probable peut rapporter peu.</p>
</section>
<section class="card accent-gris wrap">
  <div class="label">4 · Couplés, simples placés et trios</div>
  <h2>Probabilités des jeux simples</h2>
  <table><thead><tr><th>Jeu</th><th class="num">Probabilité</th></tr></thead><tbody>@@jeux@@</tbody></table>
</section>
<section class="card accent-bleu">
  <div class="label">5 · Distinction du gagnant et du top 5</div>
  <h2>Distinction du gagnant et du top 5</h2>
  @@distinction@@
</section>
<section class="card accent-bleu">
  <div class="label">6 · Profil de la course et difficultés</div>
  <h2>Profil de la course et difficultés</h2>
  <p class="note">Ces éléments sont propres à cette course. « Mesuré » vient des données du jour ; « contexte » est une information de référence, non intégrée au calcul.</p>
  @@profil@@
</section>
<section class="card accent-bleu">
  <div class="label">7 · Analyse détaillée par cheval</div>
  <h2>Analyse par cheval</h2>
  <p class="note">Touchez un cheval pour voir ses critères, les commentaires Equidia et les faits de la fiche.</p>
  @@analyses@@
</section>
<section class="card accent-bleu">
  <div class="label">8.1 · Méthode</div>
  <h2>Comment le modèle choisit ses chevaux</h2>
  <ol class="etapes">
    <li><strong>Notes Equidia</strong> (aptitudes à la distance, forme, chronos, tandem driver-entraîneur, conditions, bruits d'écurie). Ce sont les seules données qui pèsent dans la note : la musique seule et les cotes ne sont pas utilisées.</li>
    <li><strong>Une note de 0 à 1</strong> par cheval, moyenne pondérée de ces critères. Une donnée absente compte pour la moyenne neutre (0,5).</li>
    <li><strong>Simulation de 200 000 arrivées</strong> : à chaque tirage, le cheval le mieux noté a le plus de chances de passer en premier, les autres suivent selon leur note (modèle Plackett-Luce, sensibilité K = 4).</li>
    <li><strong>Probabilités</strong> : on compte, sur les 200 000 arrivées simulées, combien de fois chaque cheval gagne, finit dans les 3 ou les 5 premiers, et combien de fois chaque combinaison de jeu sort.</li>
  </ol>
  <p class="note"><strong>Validation</strong> : le modèle a été choisi sur 20 quintés passés et testé sur 10 autres. Sur ces 10 courses, sa log-loss sur le gagnant est de 2,17, contre 2,62 pour un tirage au hasard. C'est mieux que le hasard, mais le petit nombre de courses limite la confiance. <strong>Ce qu'il ne prend pas en compte</strong> : la taille du peloton, le déferrage, le changement de driver, l'avis de l'entraîneur et le classement ELO de Turfin, faute de les avoir validés.</p>
</section>
<section class="card accent-bleu wrap">
  <div class="label">8.2 · Ce qui compte, ce qui est testé</div>
  <h2>Ce qui compte, ce qui est affiché, ce qui a été testé</h2>
  <table>
    <thead><tr><th>Critère</th><th>Statut dans la note</th><th>Résultat du test (log-loss, plus bas = mieux)</th></tr></thead>
    <tbody>
      <tr><td>Notes Equidia : aptitude à la distance, forme, chronos, tandem, conditions, bruits</td><td><span class="tag ok">Pris en compte</span></td><td>@@ll_notes@@ (hasard : @@ll_hasard@@)</td></tr>
      <tr><td>Distance du jour</td><td><span class="tag ok">Via l'aptitude à la distance</span></td><td>Inclus dans les notes</td></tr>
      <tr><td>Corde (plat, obstacle)</td><td><span class="tag info">Affiché seulement</span></td><td>@@ll_corde@@ si ajoutée au calcul</td></tr>
      <tr><td>Poids (plat, obstacle)</td><td><span class="tag info">Affiché seulement</span></td><td>@@ll_poids@@ si ajouté au calcul</td></tr>
      <tr><td>Déferrage, avis de l'entraîneur, classement ELO</td><td><span class="tag info">Affiché seulement</span></td><td>Pas de données historiques pour les tester</td></tr>
      <tr><td>Cotes</td><td><span class="tag ko">Jamais utilisées</span></td><td>Exclues par principe</td></tr>
    </tbody>
  </table>
  <p class="note">Les notes ont été validées sur 30 quintés passés, dont 12 de plat ou d'obstacle. Au trot, le poids n'existe pas, donc il n'est pas affiché.</p>
</section>
<section class="card accent-gris wrap">
  <div class="label">9 · Statistiques des chevaux</div>
  <h2>Statistiques des chevaux suivis</h2>
  @@statistiques@@
</section>



<p class="foot">Les cotes ne sont pas utilisées. Estimations, pas des garanties. Jouer comporte des risques : jeu responsable, interdit aux mineurs.</p>
</main></body></html>
"""

LIBELLES = {
    "aptitudes": "Aptitudes à la distance",
    "forme_cheval": "Forme",
    "chronos": "Chronos",
    "tandem": "Tandem driver-entraîneur",
    "conditions": "Conditions",
    "bruits_ecuries": "Bruits d'écurie",
}
COMMENTAIRES = {
    "aptitudes": "com_aptitudes", "forme_cheval": "com_forme_cheval", "chronos": "com_chronos",
    "tandem": "com_tandem", "conditions": "com_conditions",
}


def pct(x):
    return "%.1f %%" % (100 * x)


def _jeu_conseille(jeux):
    """Jeu le plus probable parmi les jeux simples, couplés et trios."""
    candidats = {k: v for k, v in jeux.items() if k.startswith(("Simple", "Couplé", "Trio désordre"))}
    nom, p = max(candidats.items(), key=lambda kv: kv[1])
    return nom, "Probabilité estimée : %s." % pct(p)


def _faits_partant(p, discipline=""):
    faits = []
    if discipline in ("Plat", "Obstacle"):
        if p.get("pds_calc_hand_partant") is not None:
            faits.append("Poids : %s kg (affiché, non pris en compte)." % p["pds_calc_hand_partant"])
        if p.get("place_corde_partant") is not None:
            faits.append("Place à la corde : %s (affiché, non pris en compte)." % p["place_corde_partant"])
    if p.get("libelle_avis_entraineur") and p["libelle_avis_entraineur"] != "Avis neutre":
        faits.append("Avis de l'entraîneur : %s." % p["libelle_avis_entraineur"].replace("Avis ", "").lower())
    if p.get("deferrer_partant_first_time"):
        faits.append("Premier déferrage de sa carrière sur cette fiche.")
    if p.get("oeil_partant_first_time"):
        faits.append("Première fois avec des œillères.")
    if p.get("oeil_partant") and p["oeil_partant"] not in ("N", ""):
        faits.append("Œillères : %s." % p["oeil_partant"])
    diff = p.get("diffDistPartant")
    if diff not in (None, 0, "0"):
        faits.append("Changement de distance : %s m." % diff)
    if p.get("bonnet"):
        faits.append("Porte un bonnet.")
    if p.get("attache_langue"):
        faits.append("Langue attachée.")
    return faits


def _analyse_cheval(l, p, discipline=""):
    notes = p.get("interne_note_partant") or {}
    lignes = []
    for cle, libelle in LIBELLES.items():
        v = l["composantes"].get(cle)
        if v is None:
            continue
        commentaire = notes.get(COMMENTAIRES.get(cle, ""), "") or ""
        texte = "<strong>%s</strong> : %.0f/100" % (libelle, 100 * v)
        if commentaire:
            texte += " — %s" % html.escape(commentaire)
        lignes.append("<li>%s</li>" % texte)
    for fait in _faits_partant(p, discipline):
        lignes.append("<li>%s</li>" % html.escape(fait))
    entete = "n°%d %s — %s" % (l["numero"], html.escape(l["nom"]), pct(l["score"]))
    return ("<details><summary>%s</summary><p class='note'>Driver : %s · Entraîneur : %s · "
            "Musique : %s</p><ul>%s</ul></details>" % (
                entete, html.escape(l["driver"] or "?"), html.escape(l.get("entraineur") or "?"),
                html.escape(l["musique"] or ""), "".join(lignes)))


ELO_FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "turfin", "classement-elo-2026-11-04.md")


def _charger_elo_trot_attele():
    """Classement ELO des drivers de trot attelé (instantané du 4 novembre 2026)."""
    elo = {}
    if not os.path.exists(ELO_FICHIER):
        return elo
    dans_section = False
    for ligne in open(ELO_FICHIER, encoding="utf-8"):
        if ligne.startswith("## "):
            dans_section = "Trot attelé" in ligne
            continue
        m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|", ligne)
        if dans_section and m:
            elo[m.group(2).upper()] = (int(m.group(1)), int(m.group(3)))
    return elo


# Coordonnées approximatives des hippodromes (pour la météo). Un hippodrome absent du dictionnaire n'a pas de météo.
HIPPODROMES = {
    "PARIS-VINCENNES": (48.8431, 2.4378), "VINCENNES": (48.8431, 2.4378),
    "AUTEUIL": (48.8489, 2.2506), "PARISLONGCHAMP": (48.8536, 2.2148), "SAINT-CLOUD": (48.8410, 2.2030),
    "CHANTILLY": (49.1936, 2.4600), "ENGHIEN": (48.9700, 2.3000), "MAISONS-LAFFITTE": (48.9480, 2.1420),
    "FONTAINEBLEAU": (48.4080, 2.6900), "DEAUVILLE": (49.3561, 0.0745), "CAEN": (49.1830, -0.3700),
    "LAVAL": (48.0600, -0.7700), "NANTES": (47.2360, -1.5000), "CAGNES-SUR-MER": (43.6664, 7.1490),
    "PAU": (43.3160, -0.3450), "AVIGNON": (43.9490, 4.8090), "TOULOUSE": (43.6050, 1.4330),
    "COMPIEGNE": (49.4180, 2.8260), "SEDAN": (49.7020, 4.9420), "AMIENS": (49.8940, 2.3000),
}


def _meteo_course(hippodrome, date):
    """Pluie, vent, température et terrain probable, à partir de la prévision Open-Meteo."""
    import json
    import urllib.request
    coord = HIPPODROMES.get((hippodrome or "").upper())
    if not coord:
        return None
    lat, lon = coord
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
           "&hourly=precipitation,temperature_2m,wind_speed_10m&past_days=7&forecast_days=2&timezone=Europe%%2FParis"
           % (lat, lon))
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    h = d["hourly"]
    temps = list(zip(h["time"], h["precipitation"], h["temperature_2m"], h["wind_speed_10m"]))
    jour = [x for x in temps if x[0].startswith(date)]
    avant = [x for x in temps if x[0] < date]
    pluie_7j = sum(x[1] or 0 for x in avant)
    pluie_48h = sum(x[1] or 0 for x in avant[-48:])
    pluie_jour = sum(x[1] or 0 for x in jour)
    vent_max = max((x[3] or 0) for x in jour) if jour else None
    temp = round(sum((x[2] or 0) for x in jour) / len(jour), 1) if jour else None
    if pluie_48h >= 10 or pluie_7j >= 30:
        terrain = "probablement lourd ou collant"
    elif pluie_7j >= 10:
        terrain = "probablement souple"
    else:
        terrain = "probablement bon"
    return {"pluie_7j": pluie_7j, "pluie_48h": pluie_48h, "pluie_jour": pluie_jour,
            "vent_max": vent_max, "temp": temp, "terrain": terrain}


def _profil_course(course, lignes, par_numero):
    """Profil de la course du jour : type, distance, peloton, poids, corde, monte, difficultés."""
    discipline = course.get("discipline") or ""
    distance = int(course["distance"])
    n = len(lignes)
    faits = []   # (titre, texte, nature) ; nature = "mesuré" ou "contexte"

    if distance < 1600:
        cat = "courte distance"
    elif distance < 2200:
        cat = "distance intermédiaire"
    else:
        cat = "longue distance"
    corde_txt = (" Corde : %s." % course["lib_corde_course"].replace("Corde ", "")) if course.get("lib_corde_course") else ""
    faits.append(("Type de course", "%s, %s m (%s).%s" % (discipline, distance, cat, corde_txt), "mesuré"))

    if n <= 8:
        taille = "petit peloton"
    elif n <= 12:
        taille = "peloton moyen"
    else:
        taille = "grand peloton"
    faits.append(("Taille du peloton", "%d partants : %s. Contexte Turfin : le favori gagne 44 %% en peloton de 8 ou moins, 20 %% à 16 partants et plus." % (n, taille), "contexte"))

    poids = [(par_numero[l["numero"]].get("pds_calc_hand_partant"), l) for l in lignes]
    poids = [(p, l) for p, l in poids if p is not None]
    if discipline in ("Plat", "Obstacle") and len(poids) >= 3:
        lourd = max(poids, key=lambda x: x[0])
        leger = min(poids, key=lambda x: x[0])
        faits.append(("Poids", "De %s kg (n°%d %s) à %s kg (n°%d %s), écart de %s kg. Affiché, non pris en compte dans la note." % (
            leger[0], leger[1]["numero"], leger[1]["nom"], lourd[0], lourd[1]["numero"], lourd[1]["nom"],
            lourd[0] - leger[0]), "mesuré"))
    elif discipline in ("Attelé", "Monté", "Trot attelé", "Trot monté"):
        faits.append(("Poids", "Pas de poids au trot : le handicap ne joue pas dans cette course.", "mesuré"))

    cordes = [(par_numero[l["numero"]].get("place_corde_partant"), l) for l in lignes]
    cordes = [(c, l) for c, l in cordes if c is not None]
    if discipline in ("Plat", "Obstacle") and cordes:
        exterieures = [l["numero"] for c, l in cordes if int(c) >= max(1, int(0.7 * n))]
        faits.append(("Corde", "Départs extérieurs (à partir de la place %d) : %s. Affiché, non pris en compte." % (
            max(1, int(0.7 * n)), ", ".join("n°%d" % x for x in exterieures) or "aucun"), "mesuré"))

    meteo = _meteo_course(course["reunion"]["hippodrome"]["name"], course["reunion"]["date_reunion"])
    if meteo:
        faits.append(("Météo et terrain", "Pluie : %.1f mm sur 7 jours, %.1f mm sur 48 h, %.1f mm prévus le jour de la course. "
                      "Vent max : %s km/h. Température moyenne : %s °C. Terrain estimé : %s (estimation à partir de la pluie, "
                      "non validée ; l'état officiel de la piste n'est pas accessible)." % (
                          meteo["pluie_7j"], meteo["pluie_48h"], meteo["pluie_jour"],
                          meteo["vent_max"], meteo["temp"], meteo["terrain"]), "contexte"))
    else:
        faits.append(("Météo et terrain", "Météo non disponible pour cet hippodrome.", "contexte"))

    elo = _charger_elo_trot_attele()
    monte = []
    for l in lignes:
        drv = (l["driver"] or "").upper()
        rang_elo = elo.get(drv)
        if rang_elo:
            monte.append("n°%d %s : %s (ELO %d, %se du classement)" % (
                l["numero"], l["nom"], l["driver"], rang_elo[1], rang_elo[0]))
    if discipline in ("Attelé", "Trot attelé"):
        faits.append(("Qui le monte", ("Drivers classés au top 20 ELO (instantané du 4 novembre 2026) : " + " ; ".join(monte))
                      if monte else "Aucun driver du jour dans le top 20 ELO.", "contexte"))

    premieres = [l["numero"] for l in lignes if par_numero[l["numero"]].get("deferrer_partant_first_time")]
    if premieres:
        faits.append(("Premiers déferrages", "n° %s : premier déferrage de leur fiche (Turfin : effet positif observé, non validé sur nos données)." % ", ".join(str(x) for x in premieres), "contexte"))

    ecart = lignes[0]["score"] - lignes[1]["score"]
    faits.append(("Difficulté principale", "Le 1er et le 2e sont à %.1f points d'écart : " % (100 * ecart) + (
        "un favori se détache." if ecart >= 0.08 else "course ouverte, plusieurs chevaux peuvent gagner."), "mesuré"))

    items = "".join("<li><strong>%s</strong> : %s <span class='tag %s'>%s</span></li>" % (
        html.escape(t), html.escape(x), "ok" if nat == "mesuré" else "info", nat) for t, x, nat in faits)
    return "<ol class='profil'>%s</ol>" % items


def _distinction(lignes, prob):
    """Rang par rang : probabilités et écart avec le cheval suivant. Marque le groupe de tête."""
    lignes_html = []
    for i, l in enumerate(lignes[:8], 1):
        n = l["numero"]
        suivant = lignes[i] if i < len(lignes) else None
        ecart = (l["score"] - suivant["score"]) * 100 if suivant else None
        serre = ecart is not None and ecart < 2.0
        dans_top5 = "Top 5" if i <= 5 else "Hors top 5"
        lignes_html.append(
            "<tr><td>%d</td><td class='num'>%s</td><td>%s</td><td class='num'>%s</td><td class='num'>%s</td>"
            "<td class='num'>%s</td><td><span class='tag %s'>%s</span></td></tr>" % (
                i, n, html.escape(l["nom"]), pct(prob["victoire"][n]), pct(prob["top5"][n]),
                ("%.1f pts" % ecart) if ecart is not None else "—",
                "info" if i <= 5 else "", dans_top5 + (" · groupe serré" if serre and i <= 5 else "")))
    return ("<div class='wrap'><table><thead><tr><th>Rang</th><th class='num'>N°</th><th>Cheval</th>"
            "<th class='num'>Gagner</th><th class='num'>Top 5</th><th class='num'>Écart avec le suivant</th>"
            "<th>Position</th></tr></thead><tbody>%s</tbody></table></div>"
            "<p class='note'>Un écart inférieur à 2 points signale deux chevaux que le modèle ne sépare pas. "
            "Dans ce cas, l'ordre entre eux est peu fiable.</p>") % "".join(lignes_html)


def _statistiques_chevaux(lignes):
    """Historique réel des chevaux de la course, lu dans le registre (hors tests rétroactifs)."""
    import csv
    fichier = os.path.join(os.path.dirname(os.path.abspath(__file__)), "journal", "chevaux.csv")
    noms = {l["nom"].upper() for l in lignes}
    if not os.path.exists(fichier):
        return "<p class='note'>Aucune course enregistrée pour l'instant. Les statistiques se remplissent après chaque arrivée.</p>"
    par = {}
    for x in csv.DictReader(open(fichier, encoding="utf-8"), delimiter=";"):
        if x["retroactif"] == "True" or x["nom"].upper() not in noms:
            continue
        par.setdefault(x["nom"], []).append(x)
    if not par:
        return "<p class='note'>Aucune course réelle enregistrée pour les chevaux de cette course. Les statistiques se remplissent après chaque arrivée.</p>"
    lignes_html = []
    for nom, lst in sorted(par.items()):
        classes = [int(x["place_reelle"]) for x in lst if x["place_reelle"]]
        top3 = sum(1 for x in lst if x["dans_top3"] == "True")
        pred = sum(float(x["p_top3_predit"]) for x in lst) / len(lst)
        lignes_html.append("<tr><td>%s</td><td class='num'>%d</td><td class='num'>%.1f</td><td class='num'>%d %%</td><td class='num'>%d %%</td></tr>" % (
            html.escape(nom), len(lst), sum(classes) / len(classes) if classes else float("nan"),
            round(100 * top3 / len(lst)), round(100 * pred)))
    return ("<table><thead><tr><th>Cheval</th><th class='num'>Courses</th><th class='num'>Place moy.</th>"
            "<th class='num'>Top 3 réel</th><th class='num'>Top 3 prédit</th></tr></thead><tbody>%s</tbody></table>" % "".join(lignes_html))


def _ajouter_navigation(page):
    """Identifiants de zone et colonne de navigation latérale."""
    zones = []
    morceaux = re.split(r'(?=<section class=)', page)
    sortie = []
    for mo in morceaux:
        m = re.search(r'<div class="label">([\d.]+) · ([^<]*)</div>', mo)
        if mo.startswith('<section class=') and m:
            ancre = "zone-" + m.group(1).replace(".", "-")
            zones.append((ancre, m.group(1), m.group(2)))
            mo = mo.replace('<section class=', '<section id="%s" class=' % ancre, 1)
        sortie.append(mo)
    page = "".join(sortie)
    groupes = [
        ("Pronostic", [("1", "Quinté+")]),
        ("Analyse", [("2", "Chevaux")]),
        ("Jeux", [("3", "Tiercé, quarté, quinté"), ("3.1", "Box"), ("4", "Couplés et simples"), ("5", "Distinction top 5")]),
        ("Détail", [("6", "Profil de course"), ("7", "Par cheval")]),
        ("Suivi", [("8.1", "Méthode"), ("9", "Statistiques")]),
    ]
    dispo = {n: a for a, n, _t in zones}
    corps = ""
    for titre, liens in groupes:
        items = "".join('<a href="#%s">%s</a>' % (dispo[n], html.escape(t)) for n, t in liens if n in dispo)
        if items:
            corps += '<div class="grp">%s</div>%s' % (titre, items)
    nav = '<nav class="side" aria-label="Sections">%s</nav>' % corps
    debut = page.find("<main>")
    fin = page.rfind("</main>")
    if debut < 0 or fin < 0:
        return page
    avant = page[:debut + len("<main>")]
    milieu = page[debut + len("<main>"):fin]
    apres = page[fin:]
    fin_hero = milieu.find("</section>") + len("</section>")
    hero, reste = milieu[:fin_hero], milieu[fin_hero:]
    return avant + hero + '<div class="layout">' + nav + '<div class="contenu">' + reste + '</div></div>' + apres


def _statistiques_chevaux(lignes):
    """Historique réel des chevaux de la course, lu dans le registre (hors tests rétroactifs)."""
    import csv
    fichier = os.path.join(os.path.dirname(os.path.abspath(__file__)), "journal", "chevaux.csv")
    noms = {l["nom"].upper() for l in lignes}
    if not os.path.exists(fichier):
        return "<p class='note'>Aucune course enregistrée pour l'instant. Les statistiques se remplissent après chaque arrivée.</p>"
    par = {}
    for x in csv.DictReader(open(fichier, encoding="utf-8"), delimiter=";"):
        if x["retroactif"] == "True" or x["nom"].upper() not in noms:
            continue
        par.setdefault(x["nom"], []).append(x)
    if not par:
        return "<p class='note'>Aucune course réelle enregistrée pour les chevaux de cette course. Les statistiques se remplissent après chaque arrivée.</p>"
    lignes_html = []
    for nom, lst in sorted(par.items()):
        classes = [int(x["place_reelle"]) for x in lst if x["place_reelle"]]
        top3 = sum(1 for x in lst if x["dans_top3"] == "True")
        pred = sum(float(x["p_top3_predit"]) for x in lst) / len(lst)
        lignes_html.append("<tr><td>%s</td><td class='num'>%d</td><td class='num'>%.1f</td><td class='num'>%d %%</td><td class='num'>%d %%</td></tr>" % (
            html.escape(nom), len(lst), sum(classes) / len(classes) if classes else float("nan"),
            round(100 * top3 / len(lst)), round(100 * pred)))
    return ("<table><thead><tr><th>Cheval</th><th class='num'>Courses</th><th class='num'>Place moy.</th>"
            "<th class='num'>Top 3 réel</th><th class='num'>Top 3 prédit</th></tr></thead><tbody>%s</tbody></table>" % "".join(lignes_html))


def _pastille(n, rang):
    classe = {1: "r1", 2: "r2"}.get(rang, "")
    return "<span class='pastille %s'>%d</span>" % (classe, n)


def _recommandation_html(type_pari, b):
    return ("<div class='bloc reco'><div class='label'>%s</div>"
            "<div class='gros'>Box %d</div>"
            "<p class='note'>Chevaux : %s</p>"
            "<p><span class='tag ok'>%d combinaison%s</span>"
            "<span class='tag info'>%s de chances</span></p></div>" % (
                type_pari, b["box"], ", ".join(str(x) for x in b["chevaux"]),
                b["combinaisons"], "" if b["combinaisons"] == 1 else "s", pct(b["probabilite"])))


def generer(chemin_page):
    course = ae.charger_etat(chemin_page)
    lignes = ae.analyser(course)
    ordres = ae.simuler(lignes)
    prob = ae.probabilites(ordres, lignes)
    jeux = ae.jeux(ordres, lignes)
    combis = ae.combinaisons_en_box(ordres, lignes)
    reco = ae.recommandation_par_type(combis)
    ordre = [l["numero"] for l in lignes[:5]]
    favori = lignes[0]
    par_numero = {p["num_partant"]: p for p in course["partants"]}

    titre = "Quinté : %s R%sC%s — %s" % (
        course["reunion"]["hippodrome"]["name"], course["reunion"]["num_reunion"],
        course["num_course_pmu"], course.get("libcourt_prix_course") or "")
    date = course["reunion"]["date_reunion"]
    meta = "%s · %s m · %s partants" % (course.get("discipline"), course["distance"], len(lignes))
    chips = "".join("<span class='chip'>%s</span>" % html.escape(c) for c in [
        date, course["reunion"]["hippodrome"]["name"], course.get("discipline"),
        "%s m" % course["distance"], "%d partants" % len(lignes)] if c)

    ordre_html = "".join(_pastille(n, i + 1) for i, n in enumerate(ordre))

    lignes_html = []
    for i, l in enumerate(lignes, 1):
        n = l["numero"]
        classe = "favori" if i == 1 else ("top2" if i <= 3 else "")
        barre = "<div class='barre'><span style='width:%.1f%%'></span></div>" % (100 * prob["top3"][n])
        lignes_html.append(
            "<tr class='%s'><td>%d</td><td class='num'>%s</td><td>%s</td><td>%s</td>"
            "<td class='num'>%.3f</td><td>%s %s</td><td>%s</td><td class='num'>%s</td></tr>"
            % (classe, i, n, html.escape(l["nom"]), html.escape(l["driver"] or ""), l["score"],
               barre, pct(prob["victoire"][n]), pct(prob["top3"][n]), pct(prob["top5"][n])))

    analyses_html = "".join(_analyse_cheval(l, par_numero[l["numero"]], course.get("discipline")) for l in lignes)
    jeux_html = "".join("<tr><td>%s</td><td class='num'>%s</td></tr>" % (html.escape(k), pct(v))
                        for k, v in sorted(jeux.items(), key=lambda kv: -kv[1]))

    blocs_combis = []
    for type_pari, liste in combis.items():
        reco_box = reco[type_pari]["box"] if type_pari in reco else None
        lignes_pari = []
        for b in liste:
            est_reco = b["box"] == reco_box
            numeros = "".join("<span class='num-box'>%d</span>" % x for x in b["chevaux"])
            libelle = ("<span class='tag box'>Recommandé</span>" if est_reco else "")
            lignes_pari.append(
                "<tr class='%s'><td class='num'>%d</td><td><div class='numeros'>%s</div></td>"
                "<td class='num'>%d</td><td class='num'>%s</td><td class='num opt'>%.3f %%</td><td>%s</td></tr>" % (
                    "reco" if est_reco else "", b["box"], numeros, b["combinaisons"],
                    pct(b["probabilite"]), 100 * b["par_combinaison"], libelle))
        rangs = {"Tiercé": 3, "Quarté": 4, "Quinté": 5}[type_pari]
        blocs_combis.append(
            "<div class='bloc-pari'><h3>%s · les %d premiers, dans un box</h3>"
            "<div class='wrap'><table><thead><tr><th class='num'>Box</th><th>Numéros</th>"
            "<th class='num'>Comb.</th><th class='num'>Chances</th>"
            "<th class='num opt'>Par combinaison</th><th></th></tr></thead>"
            "<tbody>%s</tbody></table></div></div>" % (type_pari, rangs, "".join(lignes_pari)))
    combis_html = blocs_combis
    recommandations = "".join(_recommandation_html(t, b) for t, b in reco.items())
    nom_jeu, phrase_jeu = _jeu_conseille(jeux)

    valeurs = {
        "titre": html.escape(titre),
        "titre_page": html.escape("Quinté %s R%sC%s" % (
            course["reunion"]["hippodrome"]["name"].title(), course["reunion"]["num_reunion"], course["num_course_pmu"])),
        "date": html.escape(date),
        "meta": html.escape(meta),
        "chips": chips,
        "ordre": ordre_html,
        "fav_num": favori["numero"],
        "fav_nom": html.escape(favori["nom"]),
        "fav_win": pct(prob["victoire"][favori["numero"]]),
        "fav_top3": pct(prob["top3"][favori["numero"]]),
        "jeu_type": html.escape(nom_jeu),
        "jeu_sel": html.escape(phrase_jeu),
        "recommandations": recommandations,
        "budget": ae.BUDGET_COMBINAISONS,
        "profil": _profil_course(course, lignes, par_numero),
        "distinction": _distinction(lignes, prob),
        "statistiques": _statistiques_chevaux(lignes),
        "ll_notes": "2,17", "ll_hasard": "2,62", "ll_corde": "2,18 (pire)", "ll_poids": "2,19 (pire)",
        "combinaisons": "".join(combis_html),
        "lignes": "".join(lignes_html),
        "analyses": analyses_html,
        "jeux": jeux_html,
    }
    page = GABARIT
    for cle, valeur in valeurs.items():
        page = page.replace("@@%s@@" % cle, str(valeur))
    return _ajouter_navigation(page)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(generer(sys.argv[1]))
    print("écrit :", sys.argv[2])
