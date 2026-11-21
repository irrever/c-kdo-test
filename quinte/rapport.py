#!/usr/bin/env python3
"""Génère la page HTML d'analyse et de pronostic d'une course Equidia.

Usage :
    python3 quinte/rapport.py page_equidia.html sortie.html

Réutilise le modèle de analyse_equidia.py (notes Equidia, sans cotes). Pour chaque cheval,
ajoute les raisons tirées de la fiche. Ajoute aussi le détail des combinaisons de
tiercé, quarté et quinté (y compris les quintés de plus de 5 chevaux).
"""
import glob
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyse_equidia as ae  # noqa: E402

GABARIT = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>@@titre_page@@</title>
@@fond_tete@@
<style>
:root{color-scheme:light;--bg:#f2f4f7;--card:#ffffff;--ink:#101828;--muted:#475467;--line:#e4e7ec;--accent:#1849a9;--accent-soft:#eaf1fd;--chip:#f2f4f7;--reco:#e6f4ea}
:root[data-theme="dark"]{color-scheme:dark;--bg:#0c111b;--card:#161e2e;--ink:#f2f4f7;--muted:#aeb8c8;--line:#2a3550;--accent:#7ca6ff;--accent-soft:#1d2b4d;--chip:#222d44;--reco:#18362a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;padding:0 max(16px,env(safe-area-inset-right,0px)) 40px max(16px,env(safe-area-inset-left,0px));overflow-wrap:break-word;-webkit-text-size-adjust:100%}
main{max-width:720px;margin:0 auto;padding-top:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px 18px;margin:0 0 14px}
.label{font-size:14px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);margin:0 0 6px}
h1{font-size:28px;line-height:1.2;margin:2px 0 10px;font-weight:800}
h2{font-size:22px;line-height:1.3;margin:0 0 10px;font-weight:750}
h3{font-size:18px;line-height:1.3;margin:20px 0 8px;font-weight:700}
p{margin:8px 0}
.note{font-size:16px;color:var(--muted);margin:8px 0}
.puces{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.puces span{font-size:15px;padding:6px 12px;border-radius:999px;background:var(--chip)}
.onglets{position:sticky;top:0;z-index:10;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;background:var(--bg);padding:8px 0 10px;margin:0 0 4px}
.onglets button{font-family:inherit;font-weight:600;font-size:17px;padding:13px 6px;border-radius:14px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
.onglets button[aria-selected="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.top5{display:grid;gap:8px;margin-top:12px}
.top5 > div{display:flex;align-items:center;gap:14px;background:var(--accent-soft);border-radius:14px;padding:10px 14px;min-width:0}
.top5 b{font-size:28px;line-height:1;color:var(--accent);min-width:36px}
.top5 small{font-size:17px;line-height:1.3;color:var(--ink);font-weight:600}
.boite{margin-top:14px;padding:14px;border-radius:14px;border:2px solid var(--accent);background:var(--card)}
.boite .numeros{font-size:21px;font-weight:750;margin:4px 0;line-height:1.4}
.liste-simple,.chevaux{list-style:none;margin:0;padding:0}
.liste-simple li{display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--line);font-size:18px}
.liste-simple li:last-child{border-bottom:0}
.chevaux{counter-reset:none}
.cheval{border-top:1px solid var(--line);padding:16px 0}
.cheval:first-child{border-top:0;padding-top:4px}
.cheval-tete{display:flex;align-items:center;gap:12px}
.rang{flex:0 0 38px;height:38px;border-radius:50%;background:var(--accent-soft);color:var(--accent);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:17px}
.nom{font-size:19px;font-weight:750;line-height:1.25}
.sous{font-size:15px;color:var(--muted)}
.mesures{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:12px}
.mesures > div{background:var(--bg);border-radius:12px;padding:8px 4px;text-align:center;min-width:0}
.mesures b{display:block;font-size:21px;line-height:1.2}
.mesures small{font-size:14px;color:var(--muted)}
.barre{height:8px;border-radius:999px;background:var(--line);overflow:hidden;margin-top:10px}
.barre span{display:block;height:100%;background:var(--accent)}
.tag{display:inline-block;font-size:14px;padding:2px 10px;border-radius:999px;background:var(--chip);margin:2px 4px 2px 0;vertical-align:middle}
.tag.np{background:#fde8e8;color:#8a1c1c}
.tag.box{background:var(--accent-soft);color:var(--accent);border:1px solid var(--accent)}
.wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;font-size:16px}
th{font-size:14px;color:var(--muted);font-weight:700;text-align:left;padding:8px 6px;border-bottom:1px solid var(--line)}
td{padding:10px 6px;border-bottom:1px solid var(--line);vertical-align:middle}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr.reco td{background:var(--reco)}
.num-box{display:inline-block;min-width:32px;text-align:center;padding:3px 6px;margin:2px 2px;border-radius:8px;background:var(--chip);font-weight:700}
.rec{display:grid;gap:10px;margin-top:10px}
.rec .bloc{border:1px solid var(--line);border-radius:14px;padding:12px}
.rec .bloc.reco{border-color:var(--accent);background:var(--accent-soft)}
.rec .gros{font-size:21px;font-weight:800}
.jeux{list-style:none;margin:0;padding:0}
.jeux li{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid var(--line);font-size:16px}
.jeux b{white-space:nowrap}
details{margin:0}
details > summary{cursor:pointer;list-style:none;font-size:18px;font-weight:700;padding:14px 0;display:flex;justify-content:space-between;align-items:center;gap:10px}
details > summary::-webkit-details-marker{display:none}
details > summary::after{content:"+";font-size:24px;line-height:1;color:var(--muted);font-weight:400}
details[open] > summary::after{content:"-"}
details details{margin-top:10px}
details ul,details ol{padding-left:20px;font-size:16px;margin:8px 0}
details li{margin:6px 0}
.etapes{padding-left:20px;font-size:16px}
.etapes li{margin:10px 0}
.arr-grand{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:12px 0}
.arr-grand .cell{background:var(--bg);border-radius:14px;padding:10px 4px;text-align:center;min-width:0}
.arr-grand .cell b{display:block;font-size:28px;line-height:1.1}
.arr-grand .cell .nom{display:block;font-size:14px;line-height:1.25}
.arr-grand .cell small{font-size:13px;color:var(--muted)}
.recherche-form{display:grid;gap:10px;grid-template-columns:minmax(0,1fr)}
.recherche-form label{font-size:16px;display:grid;gap:6px;min-width:0}
.recherche-form select,.rech-bouton{font-family:inherit;font-size:17px;padding:12px;border-radius:12px;border:1px solid var(--line);background:var(--card);color:var(--ink);width:100%;min-width:0;max-width:100%;text-overflow:ellipsis}
.rech-bouton{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:700}
.pied{margin-top:22px;font-size:15px;color:var(--muted)}
.fond-bouton{font-family:inherit;font-size:16px;font-weight:600;padding:12px 16px;border-radius:12px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
.phone-hide{display:none}
@media (min-width:640px){
  .phone-hide{display:table-cell}
  .top5{grid-template-columns:repeat(5,minmax(0,1fr))}
  .top5 > div{flex-direction:column;text-align:center;padding:10px 4px}
  .top5 b{font-size:34px;min-width:0}
  .top5 small{font-size:15px}
  .nom{font-size:20px}
  .recherche-form{grid-template-columns:minmax(0,1fr) minmax(0,2fr) auto;align-items:end}
}
</style></head><body><main>
<section class="card">
  <div class="label">@@libelle_jour@@</div>
  <h1>@@titre_h1@@</h1>
  <div class="puces">@@puces@@</div>
  <p class="note">@@statut@@</p>
</section>
<nav class="onglets" role="tablist" aria-label="Sections">@@onglets@@</nav>
<div class="vue" data-vue="pronostic">@@pronostic@@</div>
<div class="vue" data-vue="resultat" hidden>@@resultat@@</div>
@@recherche@@
<footer class="pied">
  <p>@@fond@@</p>
  <p>Estimations, pas des garanties. Jouer comporte des risques : jeu responsable, interdit aux mineurs.</p>
</footer>
</main>
<script>
(function(){
  var boutons = document.querySelectorAll('.onglets button');
  boutons.forEach(function(b){
    b.addEventListener('click', function(){
      boutons.forEach(function(x){ x.setAttribute('aria-selected', x === b ? 'true' : 'false'); });
      document.querySelectorAll('[data-vue]').forEach(function(v){ v.hidden = v.getAttribute('data-vue') !== b.getAttribute('data-cible'); });
      window.scrollTo({top: 0, behavior: 'smooth'});
    });
  });
})();
</script>
</body></html>"""

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
    return ("%.1f\u00a0%%" % (100 * x)).replace(".", ",")


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
    entete = "n°%d %s — note %d/100" % (l["numero"], html.escape(l["nom"]), round(100 * l["score"]))
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


def _statistiques_chevaux(course, lignes):
    """Statistiques Equidia de chaque partant : gains de carrière, réduction kilométrique, réussite sur la distance."""
    par_numero = {p["num_partant"]: p for p in course["partants"]}
    lignes_html = []
    for l in lignes:
        p = par_numero[l["numero"]]
        com = ""
        for c in ((p.get("interne_note_partant") or {}).get("comments") or []):
            if c.get("label") == "Aptitudes":
                com = c.get("comment") or ""
        m = re.search(r"(\d+)% de réussite dans les 5 premiers en (\d+) courses", com)
        top5 = ("%s %% (%s courses)" % (m.group(1), m.group(2))) if m else "—"
        try:
            gains = "{:,}".format(int(p.get("gains_carriere"))).replace(",", " ") + " €"
        except (TypeError, ValueError):
            gains = "—"
        chrono = p.get("reduction_km") or "—"
        lignes_html.append(
            "<tr><td>n°%d %s</td><td class='num'>%s</td><td class='num'>%s</td><td class='num'>%s</td></tr>" % (
                l["numero"], html.escape(l["nom"]), html.escape(gains), html.escape(str(chrono)), html.escape(top5)))
    return ("<table><thead><tr><th>Cheval</th><th class='num'>Gains de carrière</th>"
            "<th class='num'>Réduction km</th><th class='num'>Top 5 sur la distance</th></tr></thead>"
            "<tbody>%s</tbody></table>" % "".join(lignes_html))


def _entete_html(course, avec_cotes=False, fige_le=None):
    """En-tête du quinté : date, réunion, heure de départ, distance, discipline, partants."""
    import datetime as dt
    reunion = course.get("reunion", {})
    hippo = (reunion.get("hippodrome") or {}).get("name") or reunion.get("lib_reunion") or ""
    date_iso = reunion.get("date_reunion") or ""
    try:
        d = dt.date.fromisoformat(date_iso)
        jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
                "septembre", "octobre", "novembre", "décembre"]
        date_txt = "%s %d %s %d" % (jours[d.weekday()].capitalize(), d.day, mois[d.month - 1], d.year)
    except ValueError:
        date_txt = date_iso
    heure = course.get("heure_depart_course") or ""
    distance = course.get("distance")
    discipline = course.get("discipline") or ""
    partants = sum(1 for p in course.get("partants", []) if p.get("statut_part") != "NP")
    libelle = course.get("libcourt_prix_course") or ""
    corde = (course.get("lib_corde_course") or "").replace("Corde ", "corde ")
    numero = "R%s C%s" % (reunion.get("num_reunion"), course.get("num_course_pmu"))
    chips = [date_txt,
             ("Départ %s" % heure) if heure else "",
             ("%s m" % distance) if distance else "",
             discipline,
             ("%s partants" % partants) if partants else "",
             corde,
             _libelle_pronostic(course, avec_cotes, fige_le)]
    puces = "".join("<span>%s</span>" % html.escape(c) for c in chips if c)
    return ("<section class='card entete accent-bleu'>"
            "<div class='label'>Quinté+ du jour · %s</div>"
            "<h2>%s · %s</h2>"
            "<div class='puces'>%s</div></section>") % (
                html.escape(numero), html.escape(hippo), html.escape(libelle), puces)


def _rendre_depliable(page):
    """Chaque zone de l'onglet Analyse devient un bloc repliable (fermé par défaut, sauf le quinté)."""
    motif = re.compile(
        r'<section id="(zone-[^"]+)" class="([^"]*)">\s*<div class="label">([^<]*)</div>\s*'
        r'(<h2[^>]*>.*?</h2>)?(.*?)</section>', re.S)

    def remplace(m):
        zone_id, classes, libelle, titre, corps = m.group(1), m.group(2), m.group(3), m.group(4) or "", m.group(5)
        ouvert = " open" if zone_id == "zone-1" else ""
        return ('<details id="%s" class="%s zone-details"%s>'
                '<summary><span class="label">%s</span>%s</summary>%s</details>') % (
                    zone_id, classes, ouvert, libelle, titre, corps)

    return motif.sub(remplace, page)


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
    page = _rendre_depliable(page)
    groupes = [
        ("Pronostic", [("1", "Quinté+")]),
        ("Analyse", [("2", "Analyse des chevaux"), ("6", "Probabilités")]),
        ("Jeux", [("3", "Tiercé, quarté, quinté"), ("3.1", "Box"), ("4", "Couplés et simples"), ("5", "Distinction top 5")]),
        ("Détail", [("7", "Profil de course")]),
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
    milieu = page[debut + len("<main>"):fin]   # tout le contenu : onglets, vues, zones (équilibrés)
    apres = page[fin:]
    return avant + '<div class="layout">' + nav + '<div class="contenu">' + milieu + '</div></div>' + apres


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


JOURNAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "journal")


def _arrivee_page(course):
    """Arrivée officielle (liste des numéros classés), ou None si la course n'est pas terminée."""
    if course.get("type_statut_course_id") != "finished":
        return None
    arr = []
    for p in course["partants"]:
        rang = str(p.get("num_place_arrivee") or "").strip()
        if p.get("statut_part") == "DP" and rang.isdigit():
            arr.append((int(rang), p["num_partant"]))
    return [n for _, n in sorted(arr)] or None


def _journal_du_jour(date):
    """Pronostic figé avant la course (journal), ou None s'il n'existe pas. Quand un pronostic final de l'ancienne
    méthode existe, c'est le pronostic du soir qui est repris : celui qui est affiché sur la page."""
    chemin = os.path.join(JOURNAL_DIR, "%s.json" % date)
    if not os.path.exists(chemin):
        return None
    d = json.load(open(chemin, encoding="utf-8"))
    soir = d.get("pronostic_soir")
    if soir:
        d = dict(d, **soir)
    return d


def _lignes_rapports(chemin_page, arrivee):
    """Tableau des rapports essentiels, à partir de l'arrivée officielle."""
    brut = open(chemin_page, encoding="utf-8").read()
    combos = []
    for m in re.finditer(r'\{[^{}]*"combinaison_rap_def":"[^"]*"[^{}]*\}', brut):
        try:
            combos.append(json.loads(m.group(0)))
        except ValueError:
            pass

    def nombres(texte):
        return [int(x) for x in re.findall(r"\d+", texte or "")]

    def cherche(type_pari, nb, ordre, exige_gagnant=False):
        liste = arrivee[:nb]
        if len(liste) < nb:
            return None
        for c in combos:
            if c.get("type_reserve_rap_def") != type_pari:
                continue
            if exige_gagnant and c.get("gagnant") in (None, ""):
                continue
            n = nombres(c.get("combinaison_rap_def"))
            if (ordre and n == liste) or (not ordre and sorted(n) == sorted(liste)):
                return c
        return None

    specs = [
        ("Quinté+", "Quinté+ Ordre", 5, True, False, "ordre"),
        ("Quinté+", "Quinté+ Désordre", 5, False, False, "désordre"),
        ("Tiercé", "Tiercé Ordre", 3, True, False, "ordre"),
        ("Tiercé", "Tiercé Désordre", 3, False, False, "désordre"),
        ("Quarté+", "Quarté+ Ordre", 4, True, False, "ordre"),
        ("Quarté+", "Quarté+ Désordre", 4, False, False, "désordre"),
        ("Couplé gagnant", "Couplé", 2, False, True, "désordre"),
    ]
    lignes_html = []
    for nom_pari, type_pari, nb, ordre, exige, mode in specs:
        c = cherche(type_pari, nb, ordre, exige)
        combinaison = "-".join(str(x) for x in arrivee[:nb])
        if c is None:
            valeur = "pas encore publié"
        else:
            valeur = "%s €" % c.get("gagnant") if c.get("gagnant") not in (None, "") else "—"
        lignes_html.append(
            "<tr><td>%s</td><td>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (
                html.escape(nom_pari), html.escape(mode), html.escape(combinaison), html.escape(valeur)))
    publie = all(cherche(t, 5, o, False) is not None
                 for t, o in (("Quinté+ Ordre", True), ("Quinté+ Désordre", False)))
    return "".join(lignes_html), publie


def _forces_faiblesses(l):
    """Points forts (≥ 70 %) et points faibles (< 40 %) d'un cheval, d'après ses composantes."""
    forts, faibles = [], []
    for cle, libelle in LIBELLES.items():
        v = l["composantes"].get(cle)
        if v is None:
            continue
        if v >= 0.7:
            forts.append("%s (%d/100)" % (libelle.lower(), round(100 * v)))
        elif v < 0.4:
            faibles.append("%s (%d/100)" % (libelle.lower(), round(100 * v)))
    return forts, faibles


def _ordinal(n):
    """1 -> 1er, 2 -> 2e, ..."""
    return "1er" if n == 1 else "%de" % n


def _pourcent(x):
    """0.08 -> 8,0 % (virgule française)."""
    return ("%.1f %%" % (100 * x)).replace(".", ",")


def _reaction_html(lignes, arrivee, journal, disqualifies):
    """Explication de l'écart entre le choix du modèle et l'arrivée réelle, cheval par cheval."""
    rang_pred = {l["numero"]: i + 1 for i, l in enumerate(lignes)}
    par_num = {l["numero"]: l for l in lignes}
    rang_arr = {n: i + 1 for i, n in enumerate(arrivee)}
    pred5 = [l["numero"] for l in lignes[:5]]
    arr5 = arrivee[:5]
    bien = [n for n in pred5 if n in arr5]
    rates = [n for n in pred5 if n not in arr5]
    surprises = [n for n in arr5 if n not in pred5]

    def nom(n):
        return "n°%d %s" % (n, html.escape(par_num[n]["nom"])) if n in par_num else "n°%d" % n

    def arrive(n):
        return _ordinal(rang_arr[n]) if n in rang_arr else "non classé"

    def prevu(n):
        return _ordinal(rang_pred[n]) if n in rang_pred else "hors liste"

    def forces_txt(l):
        forts, faibles = _forces_faiblesses(l)
        return ", ".join(forts) or "aucun", ", ".join(faibles) or "aucun", faibles

    items = []
    items.append("<p class='concl'><strong>Notre choix</strong> : %s. <strong>L'arrivée</strong> : %s. "
                 "Nous avions %d %s sur 5 dans le bon cinq.</p>" % (
                     " – ".join(str(x) for x in pred5), " – ".join(str(x) for x in arr5),
                     len(bien), "cheval" if len(bien) == 1 else "chevaux"))
    if bien:
        items.append("<p class='concl'><strong>Bien vu</strong> : %s.</p>" % ", ".join(
            "%s (prévu %s, arrivé %s)" % (nom(n), prevu(n), arrive(n)) for n in bien))

    for n in rates:
        l = par_num[n]
        if n in disqualifies:
            items.append("<p class='concl'><strong>Raté</strong> : %s, prévu %s, n'a pas fini : disqualifié pour allure irrégulière. "
                         "Aucune note ne permet de prévoir ce type d'incident.</p>" % (nom(n), prevu(n)))
            continue
        forts, faibles, liste_faibles = forces_txt(l)
        texte = "<strong>Raté</strong> : %s, prévu %s, arrivé %s. Points forts du modèle : %s. Points faibles : %s." % (
            nom(n), prevu(n), arrive(n), forts, faibles)
        if any(f.startswith("forme") for f in liste_faibles):
            texte += " Sa forme récente était faible. Elle pèse 25 % de la note : les autres critères l'ont compensée."
        items.append("<p class='concl'>%s</p>" % texte)

    for n in surprises:
        l = par_num.get(n)
        if l is None:
            continue
        forts, faibles, liste_faibles = forces_txt(l)
        texte = ("<strong>Surprise</strong> : %s, arrivé %s alors que nous le prévoyions %s. "
                 "Points forts : %s. Points faibles : %s.") % (nom(n), arrive(n), prevu(n), forts, faibles)
        if any(f.startswith("chronos") for f in liste_faibles):
            texte += (" Ses chronos étaient faibles (critère à 20 % de la note) alors qu'il a bien fini : "
                      "notre note l'a probablement pénalisé à tort.")
        items.append("<p class='concl'>%s</p>" % texte)

    gagnant = arrivee[0] if arrivee else None
    if gagnant in rang_pred and rang_pred[gagnant] > 3:
        l = par_num[gagnant]
        forts, faibles, _ = forces_txt(l)
        p_gagnant = next((c["p_victoire"] for c in journal["chevaux"] if c["numero"] == gagnant), 0.0) if journal else 0.0
        items.append("<p class='concl'><strong>Le gagnant</strong> : %s était %s chez nous, avec %s de chances de gagner. "
                     "Points forts : %s. Points faibles : %s.</p>" % (
                         nom(gagnant), _ordinal(rang_pred[gagnant]), _pourcent(p_gagnant), forts, faibles))

    retenir = []
    tous = [n for n in rates + surprises if n in par_num and n not in disqualifies]
    if any(any(f.startswith("chronos") for f in forces_txt(par_num[n])[2]) for n in tous):
        retenir.append("Le critère chronos (20 % de la note) a pénalisé des chevaux qui ont bien fini : à vérifier sur les prochaines courses.")
    if any(any(f.startswith("forme") for f in forces_txt(par_num[n])[2]) for n in rates if n in par_num and n not in disqualifies):
        retenir.append("La forme récente (25 % de la note) a été sous-pesée pour un partant qui a tout de même bien couru : à surveiller.")
    if disqualifies:
        retenir.append("Les disqualifications ne se prévoient pas avec nos données.")
    retenir.append("Une seule course ne suffit pas à modifier le modèle : le bilan cumulé dans le journal reste la mesure à suivre.")
    items.append("<p class='concl'><strong>Ce que j'en retiens</strong></p><ul class='retenir'>%s</ul>" % "".join(
        "<li>%s</li>" % html.escape(r) for r in retenir))
    return "".join(items)


PRONOSTICS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pronostics")


def _date_fr(iso):
    """2026-11-05 -> jeudi 5 novembre 2026."""
    import datetime as dt
    try:
        d = dt.date.fromisoformat(iso)
    except ValueError:
        return iso
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
            "septembre", "octobre", "novembre", "décembre"]
    return "%s %d %s %d" % (jours[d.weekday()], d.day, mois[d.month - 1], d.year)


MARQUE_OFFICIEL_DEBUT = '<template id="bloc-officiel">'
MARQUE_OFFICIEL_FIN = "</template>"


def _dernier_quinte_couru(date):
    """Bloc officiel du dernier quinté couru avant `date` : (date, HTML), ou (None, None).

    Chaque page dont le quinté a son arrivée garde son bloc officiel dans un <template>. La page du quinté
    suivant le reprend tant que ses propres rapports Quinté+ ne sont pas publiés.
    """
    for f in sorted(glob.glob(os.path.join(PRONOSTICS_DIR, "????-??-??.html")), reverse=True):
        d = os.path.basename(f)[:-5]
        if d >= date:
            continue
        texte = open(f, encoding="utf-8").read()
        if MARQUE_OFFICIEL_DEBUT not in texte:
            continue
        i = texte.index(MARQUE_OFFICIEL_DEBUT) + len(MARQUE_OFFICIEL_DEBUT)
        return d, texte[i:texte.index(MARQUE_OFFICIEL_FIN, i)]
    return None, None


def _bandeau_dernier(d_prec, date):
    """Bandeau au-dessus du dernier quinté couru, tant que le quinté du jour n'a pas ses rapports."""
    jp = os.path.join(JOURNAL_DIR, "%s.json" % d_prec)
    cible = json.load(open(jp, encoding="utf-8")) if os.path.exists(jp) else {}
    quoi = "%s (%s)" % (cible.get("hippodrome", ""), cible.get("course", ""))
    return ("<section class='card accent-gris'><div class='label'>Dernier quinté couru</div>"
            "<h2>Résultats du quinté du %s</h2>"
            "<p class='note'>%s. Les rapports du quinté du %s ne sont pas encore publiés : ces résultats et rapports "
            "restent affichés jusqu'à leur publication.</p></section>") % (
        html.escape(_date_fr(d_prec)), html.escape(quoi), html.escape(_date_fr(date)))


def _bloc_officiel(course, lignes, date, arrivee, chemin_page):
    """Arrivée, comparaison, réaction du modèle et rapports d'un quinté couru.

    Renvoie (HTML, rapports Quinté+ publiés).
    """
    noms = {l["numero"]: l["nom"] for l in lignes}
    disq = {p["num_partant"] for p in course["partants"] if p.get("statut_part") == "AI"}
    grand = "".join(
        "<div class='cell'><b>%d</b><span class='nom'>%s</span><small>%s</small></div>" % (
            n, html.escape(noms.get(n, "")), ["1er", "2e", "3e", "4e", "5e"][i])
        for i, n in enumerate(arrivee[:5]))

    j = _journal_du_jour(date)
    for c in (j or {}).get("chevaux", []):  # un non-partant n'est plus dans la course : son nom vient du pronostic
        noms.setdefault(c["numero"], c["nom"])
    comparaison = ""
    if j is not None:
        pred = j["ordre_predit"]
        lignes_cmp = "".join(
            "<tr><td>%d</td><td>n°%d %s</td><td>n°%d %s</td></tr>" % (
                i + 1, pred[i], html.escape(noms.get(pred[i], "")),
                arrivee[i] if i < len(arrivee) else 0,
                html.escape(noms.get(arrivee[i], "")) if i < len(arrivee) else "")
            for i in range(min(5, len(pred))))
        comparaison = ("<table class='res-tab'><thead><tr><th>Rang</th><th>Notre choix</th><th>Arrivée</th></tr></thead>"
                       "<tbody>%s</tbody></table>" % lignes_cmp)
    reaction = _reaction_html(lignes, arrivee, j, disq) if j is not None else ""
    rapports, publie = _lignes_rapports(chemin_page, arrivee)

    bloc = (
        "<section class='card accent-bleu'><div class='label'>Résultat officiel</div>"
        "<h2>Arrivée</h2><div class='arr-grand'>%s</div>"
        "<h2 style='margin-top:18px'>Notre choix contre l'arrivée</h2>%s"
        "<h2 style='margin-top:18px'>Réaction du modèle</h2>%s"
        "</section>") % (grand, comparaison, reaction)
    return bloc, publie


def _resultat_html(course, lignes, date, chemin_page):
    """Partie affichée de l'onglet « Résultat et rapports », et bloc officiel du jour (ou None).

    Le quinté du jour remplace le dernier quinté couru seulement quand son arrivée et ses rapports Quinté+
    sont publiés. Avant, on affiche le dernier quinté couru, avec son bandeau.
    """
    arrivee = _arrivee_page(course)
    bloc, publie = (None, False)
    if arrivee:
        bloc, publie = _bloc_officiel(course, lignes, date, arrivee, chemin_page)
    if bloc is not None and publie:
        return bloc, bloc
    d_prec, bloc_prec = _dernier_quinte_couru(date)
    if bloc_prec is not None:
        return _bandeau_dernier(d_prec, date) + bloc_prec, bloc
    if bloc is not None:
        return bloc, bloc
    return ("<section class='card accent-bleu'><div class='label'>Résultat</div>"
            "<h2>Arrivée non encore connue</h2>"
            "<p class='note'>Le résultat officiel et les rapports apparaîtront ici dès l'arrivée. "
            "L'analyse ci-dessous reste celle faite avant la course.</p></section>"), None


def _partie_resultat(course, lignes, date, chemin_page):
    """HTML de la partie résultat, suivi du bloc officiel repris par le quinté suivant."""
    affiche, bloc = _resultat_html(course, lignes, date, chemin_page)
    if bloc is None:
        return affiche
    return affiche + MARQUE_OFFICIEL_DEBUT + bloc + MARQUE_OFFICIEL_FIN


DEBUT_RESULTAT = "<div class='vue' data-vue='resultat' hidden>"
FIN_RESULTAT = '<div class="vue" data-vue="analyse">'


MARQUE_SUIVI = '<p class="note">Suivi réel'


def _bloc_suivi(page):
    """Début et fin du paragraphe « Suivi réel » de la page, ou None."""
    i = page.find(MARQUE_SUIVI)
    if i < 0:
        return None
    return i, page.index("</p>", i) + len("</p>")


def fusionner_resultat(page_figee, page_live):
    """Page du jour : l'analyse vient de la page figée au pronostic ; l'entête, les onglets, le résultat,
    la recherche et le suivi réel viennent de la page actuelle."""
    j_f = page_figee.index(FIN_RESULTAT)
    j_l = page_live.index(FIN_RESULTAT)
    queue = page_figee[j_f:]
    s_f = _bloc_suivi(queue)
    s_l = _bloc_suivi(page_live)
    if s_f and s_l:
        queue = queue[:s_f[0]] + page_live[s_l[0]:s_l[1]] + queue[s_f[1]:]
    return page_live[:j_l] + queue


_JS_RECHERCHE = r"""(function(){
  var courses = JSON.parse(document.getElementById('journee-donnees').textContent).courses;
  var selR = document.getElementById('rech-reunion');
  var selC = document.getElementById('rech-course');
  var bouton = document.getElementById('rech-bouton');
  var out = document.getElementById('rech-resultat');
  function vider(el){ while (el.firstChild) { el.removeChild(el.firstChild); } }
  function option(sel, valeur, libelle){ var o = document.createElement('option'); o.value = valeur; o.textContent = libelle; sel.appendChild(o); }
  function fr(x, decimales){ return x.toFixed(decimales).replace('.', ','); }
  function paragraphe(classe, texte){ var p = document.createElement('p'); p.className = classe; p.textContent = texte; return p; }
  function etat(statut){ return statut === 'finished' ? 'terminée' : (statut === 'before' ? 'à venir' : 'en cours'); }
  var reunions = {};
  courses.forEach(function(x){ if (!reunions[x.r]) { reunions[x.r] = x.hippodrome; } });
  Object.keys(reunions).map(Number).sort(function(a, b){ return a - b; }).forEach(function(r){
    option(selR, r, 'R' + r + ' · ' + reunions[r]);
  });
  function changerReunion(){
    vider(selC);
    var r = Number(selR.value);
    courses.filter(function(x){ return x.r === r; }).forEach(function(x){
      option(selC, x.c, 'C' + x.c + ' · ' + (x.heure || '') + ' · ' + (x.libelle || ''));
    });
    afficher();
  }
  function libellePronostic(x){
    if (!x.final) { return 'Pronostic du soir.'; }
    var heure = x.final.fige_le.slice(11, 13) + ' h ' + x.final.fige_le.slice(14, 16);
    return 'Pronostic figé à ' + heure + '.';
  }
  function sansPronostic(x){
    var avant = x.statut === 'before';
    out.appendChild(paragraphe('rech-sans', 'Pas de pronostic'));
    out.appendChild(paragraphe('note', avant
      ? "Aucun cheval n'a encore couru. Sans musique ni notes Equidia, le modèle ne peut pas les départager : la page n'affiche donc ni ordre, ni pourcentages."
      : "Aucun cheval n'avait de musique ni de note Equidia : le modèle ne pouvait pas les départager, la page n'a donc affiché ni ordre ni pourcentages."));
    if (x.conditions) { out.appendChild(paragraphe('note', 'Conditions : ' + x.conditions)); }
  }
  function afficher(){
    vider(out);
    var r = Number(selR.value), c = Number(selC.value);
    var x = courses.filter(function(y){ return y.r === r && y.c === c; })[0];
    if (!x) { return; }
    var titre = document.createElement('h3');
    titre.textContent = 'R' + x.r + 'C' + x.c + ' · ' + x.hippodrome + ' · départ ' + (x.heure || '?');
    out.appendChild(titre);
    out.appendChild(paragraphe('note', [x.discipline, x.distance ? x.distance + ' m' : '', x.partants + ' partants', etat(x.statut)].filter(Boolean).join(' · ')));
    if (x.sans_donnees) {
      sansPronostic(x);
    } else if (x.ordre && x.ordre.length) {
      out.appendChild(paragraphe('rech-ordre', 'Pronostic : ' + x.ordre.join(' – ')));
      out.appendChild(paragraphe('note', libellePronostic(x)));
    } else {
      out.appendChild(paragraphe('note', 'Pas de pronostic : la course était déjà partie quand la journée a été calculée.'));
    }
    if (x.arrivee && x.arrivee.length) {
      out.appendChild(paragraphe('rech-arrivee', 'Arrivée : ' + x.arrivee.map(function(n){ return n + ' ' + (x.noms[n] || ''); }).join(' · ')));
      if (x.ordre && x.ordre.length) {
        var bons = x.ordre.filter(function(n){ return x.arrivee.indexOf(n) >= 0; }).length;
        out.appendChild(paragraphe('note', 'Dans les 5 premiers : ' + bons + (bons > 1 ? ' chevaux' : ' cheval') + ' sur les 5 pronostiqués.'));
      }
    }
    if (x.top && x.top.length) {
      var table = document.createElement('table');
      var tete = document.createElement('tr');
      ['N°', 'Cheval', 'Note', 'Gagner', 'Top 3'].forEach(function(t, i){
        var th = document.createElement('th'); th.textContent = t;
        if (i >= 2) { th.className = 'n'; }
        tete.appendChild(th);
      });
      table.appendChild(tete);
      x.top.forEach(function(h){
        var tr = document.createElement('tr');
        [String(h.numero), h.nom, h.note + '/100', fr(100 * h.p_victoire, 1) + ' %', fr(100 * h.p_top3, 0) + ' %'].forEach(function(t, i){
          var td = document.createElement('td'); td.textContent = t;
          if (i >= 2) { td.className = 'n'; }
          tr.appendChild(td);
        });
        table.appendChild(tr);
      });
      out.appendChild(table);
    }
  }
  selR.addEventListener('change', changerReunion);
  selC.addEventListener('change', afficher);
  bouton.addEventListener('click', afficher);
  changerReunion();
})();"""


def _recherche_html(journee):
    """Onglet Recherche : une réunion et une course de la même journée, avec leur pronostic et leur arrivée."""
    if not journee:
        return ("<section class='card accent-gris'><div class='label'>Recherche</div>"
                "<h2>Recherche indisponible</h2>"
                "<p class='note'>Le programme de cette journée n'est pas encore disponible.</p></section>")
    donnees = json.dumps({"courses": journee}, ensure_ascii=False).replace("</", "<\\/")
    return ("<section class='card accent-bleu recherche'>"
            "<div class='label'>Recherche · même journée</div>"
            "<h2>Trouver une course</h2>"
            "<p class='note'>Pronostics figés avant chaque départ. Une course déjà partie n'a que son arrivée. "
            "Seules les courses de cette journée sont proposées.</p>"
            "<div class='recherche-form'>"
            "<label>Réunion<select id='rech-reunion'></select></label>"
            "<label>Course<select id='rech-course'></select></label>"
            "<button type='button' id='rech-bouton' class='rech-bouton'>Rechercher</button>"
            "</div>"
            "<div id='rech-resultat' class='rech-resultat'></div>"
            "</section>"
            "<script type='application/json' id='journee-donnees'>" + donnees + "</script>"
            "<script>" + _JS_RECHERCHE + "</script>")


def _heure_paris(fige_le):
    """Heure de Paris (HH h MM) d'une heure de figement enregistrée en UTC."""
    import datetime as dt
    from zoneinfo import ZoneInfo
    t = dt.datetime.fromisoformat(fige_le).replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Paris"))
    return t.strftime("%H h %M")


FOND_TETE = ("<script>(function(){var t='light';try{if(localStorage.getItem('quinte-fond')==='dark'){t='dark';}}"
             "catch(e){}document.documentElement.setAttribute('data-theme',t);})();</script>")
FOND_CSS = (".fond-ligne{display:flex;justify-content:flex-end;margin:0 0 10px}\n"
            ".fond-bouton{font:inherit;font-size:13px;font-weight:600;padding:6px 14px;border:1px solid var(--line);"
            "border-radius:999px;background:var(--surface);color:var(--text);cursor:pointer}\n"
            ".fond-bouton:hover{border-color:var(--bleu);color:var(--bleu)}\n"
            ".fond-bouton:focus-visible{outline:2px solid var(--bleu);outline-offset:2px}\n")


def _bouton_fond_html():
    """Choix du fond de la page : blanc par défaut, ou noir. Le choix est gardé sur l'appareil."""
    return ("<button type='button' id='fond-bouton' class='fond-bouton'>Passer au fond noir</button>"
            "<script>(function(){var b=document.getElementById('fond-bouton');if(!b){return;}"
            "function appliquer(t){document.documentElement.setAttribute('data-theme',t);"
            "b.textContent=t==='dark'?'Passer au fond blanc':'Passer au fond noir';}"
            "appliquer(document.documentElement.getAttribute('data-theme')==='dark'?'dark':'light');"
            "b.addEventListener('click',function(){var t=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';"
            "appliquer(t);try{localStorage.setItem('quinte-fond',t);}catch(e){}});})();</script>")


def ajouter_fond(page):
    """Ajoute le choix du fond à une page déjà publiée, sans toucher au reste : même script, même style et même
    bouton que le gabarit. Une page qui l'a déjà reste inchangée."""
    if "id='fond-bouton'" in page:
        return page
    ancres = ("</title>", "</style></head><body><main>", "<div class='onglets' role='tablist'>")
    for a in ancres:
        if page.count(a) != 1:
            raise ValueError("ancre absente ou présente plusieurs fois : %s" % a)
    page = page.replace("</title>", "</title>\n" + FOND_TETE, 1)
    page = page.replace("</style></head><body><main>", FOND_CSS + "</style></head><body><main>", 1)
    return page.replace("<div class='onglets' role='tablist'>",
                        "<div class='fond-ligne'>" + _bouton_fond_html() + "</div>\n"
                        "<div class='onglets' role='tablist'>", 1)


def _avis_html(a):
    """Bloc « Notre avis combiné » : notre modèle en production et la logique de la presse, boîte de 6."""
    if not a:
        return ""
    from math import comb

    def liste(ns):
        return " · ".join(str(n) for n in ns) if ns else "aucun"

    lignes = []
    for x in a["lignes"]:
        n = x["numero"]
        if n in a["box"]:
            verdict = "Dans la boîte"
        elif n in a["a_jouer"]:
            verdict = "À jouer"
        elif n in a["a_eviter"]:
            verdict = "À éviter en base"
        else:
            verdict = "—"
        if x["pos"] is None:
            derniere = "incident" if x["excusee"] else "—"
        else:
            derniere = "np" if x["pos"] == 0 else str(x["pos"])
        top5 = "%d %%" % round(100 * x["top5"]) if x["top5"] is not None else "—"
        lignes.append("<tr><td class='num'>%d</td><td class='num'>%d</td><td>%s</td><td class='num'>%s</td>"
                      "<td>%s</td><td class='num'>%s</td><td>%s</td></tr>" % (
                          x["rang"], n, html.escape(x["nom"]), top5, html.escape(x["categorie"]), derniere, verdict))
    presse_txt = "" if a["presse_disponible"] else "<p class='note'>Pas de sélection de la presse : notre top 6 seul.</p>"
    return ("<div class='bloc-pari'><h3>Notre avis combiné</h3>"
            "<p class='note'>Notre modèle en production, confronté à la logique de la presse. Règles fixées à l'avance.</p>"
            + presse_txt +
            "<ul><li><b>Notre top 5 :</b> %s.</li>"
            "<li><b>Écartés par la presse, dernière course forte :</b> %s.</li>"
            "<li><b>Retenus par la presse, dernière course hors des 4 premières :</b> %s.</li></ul>"
            "<p><b>Notre choix :</b> boîte de %d : %s, soit %d combinaisons.</p>"
            "<div class='wrap'><table><thead><tr><th class='num'>Rang</th><th class='num'>N°</th><th>Cheval</th>"
            "<th class='num'>Top 5</th><th>Presse</th><th class='num'>Dernière</th><th>Verdict</th></tr></thead>"
            "<tbody>%s</tbody></table></div></div>"
            ) % (liste(a["top5"]), liste(a["a_jouer"]), liste(a["a_eviter"]), len(a["box"]), liste(a["box"]),
                 comb(len(a["box"]), 5), "".join(lignes))


def _critere_cheval(l, p, discipline=""):
    """Critères d'un cheval, commentaires Equidia et faits de la fiche, dans un bloc replié."""
    notes = p.get("interne_note_partant") or {}
    items = []
    for cle, libelle in LIBELLES.items():
        v = l["composantes"].get(cle)
        if v is None:
            continue
        commentaire = notes.get(COMMENTAIRES.get(cle, ""), "") or ""
        texte = "<b>%s</b> : %.0f/100" % (libelle, 100 * v)
        if commentaire:
            texte += " — %s" % html.escape(commentaire)
        items.append("<li>%s</li>" % texte)
    for fait in _faits_partant(p, discipline):
        items.append("<li>%s</li>" % html.escape(fait))
    return ("<details><summary>Critères et commentaires</summary>"
            "<p class='note'>Musique : %s</p><ul>%s</ul></details>") % (
                html.escape(l.get("musique") or ""), "".join(items))


def _boites_html(combis, reco):
    """Tableaux des boîtes de tiercé, quarté et quinté. La boîte recommandée est mise en évidence."""
    rangs = {"Tiercé": 3, "Quarté": 4, "Quinté": 5}
    blocs = []
    for type_pari, liste in combis.items():
        reco_box = reco[type_pari]["box"] if type_pari in reco else None
        lignes = []
        for b in liste:
            est = b["box"] == reco_box
            numeros = " ".join("<span class='num-box'>%s</span>" % x for x in b["chevaux"])
            lignes.append(
                "<tr class='%s'><td class='num'>%d</td><td>%s</td><td class='num'>%d</td>"
                "<td class='num'>%s</td><td class='num phone-hide'>%.3f %%</td></tr>" % (
                    "reco" if est else "", b["box"], numeros, b["combinaisons"], pct(b["probabilite"]),
                    100 * b["par_combinaison"]))
        blocs.append(
            "<h3>%s : les %d premiers, dans une boîte</h3><div class='wrap'><table>"
            "<thead><tr><th class='num'>Boîte</th><th>Chevaux</th><th class='num'>Comb.</th>"
            "<th class='num'>Chances</th><th class='num phone-hide'>Par comb.</th></tr></thead>"
            "<tbody>%s</tbody></table></div>" % (type_pari, rangs.get(type_pari, 0), "".join(lignes)))
    return "".join(blocs)


def _jeux_simples_html(jeux):
    """Les huit jeux simples les plus probables (simples, couplés, trios), du plus probable au moins probable."""
    lignes = "".join("<li><span>%s</span><b>%s</b></li>" % (html.escape(k), pct(v))
                     for k, v in sorted(jeux.items(), key=lambda kv: -kv[1])[:8])
    return "<ul class='jeux'>%s</ul>" % lignes


def _methode_html():
    """Explication du modèle, avec ses poids et sa sensibilité, telle qu'elle est en production."""
    poids = "".join("<li><b>%s</b> : %s %%</li>" % (
        html.escape(LIBELLES.get(k, k)), ("%g" % (100 * v)).replace(".", ",")) for k, v in ae.POIDS.items())
    return ("<p>Le modèle note chaque cheval de 0 à 100, à partir de sept critères. Voici leur poids :</p>"
            "<ul>%s</ul>"
            "<ol class='etapes'>"
            "<li>La note est une moyenne pondérée. Une donnée absente compte pour la moyenne neutre (0,5).</li>"
            "<li>Simulation de 200 000 arrivées : à chaque tirage, le cheval le mieux noté a le plus de chances de "
            "passer en premier, les autres suivent selon leur note (sensibilité %s).</li>"
            "<li>Chances : part des simulations où chaque cheval gagne, finit dans les trois premiers ou dans les "
            "cinq premiers.</li>"
            "<li>Le pronostic est celui du soir, figé vers 23 h, et il ne change plus. Un non-partant déclaré après ce "
            "figement reste signalé dans la liste.</li>"
            "</ol>"
            "<p class='note'><b>Validation</b> : les réglages (poids de la musique, sensibilité) ont été choisis sur "
            "48 courses terminées d'octobre–novembre 2026. Le résultat est donc optimiste : le suivi des courses "
            "suivantes, ci-dessous, donne la mesure indépendante.</p>"
            "<p class='note'><b>Ce qui n'est pas pris en compte</b> : la taille du peloton, le déferrage, le changement "
            "de driver, l'avis de l'entraîneur et le classement ELO de Turfin, faute de les avoir validés.</p>"
            "<p class='note'>%s</p>") % (
                "".join(poids), ("%g" % ae.SENSIBILITE), _suivi_reel_html())


def _resume_final_html(final):
    """Historique : le pronostic final figé une heure avant le départ, selon l'ancienne méthode. None si absent."""
    if not final:
        return ""
    items = "".join("<li><span class='rang'>%d</span><span class='nom'>n°%s %s</span></li>" % (
        i, k, html.escape(final["noms"].get(k, ""))) for i, k in enumerate(final["ordre"][:5], start=1))
    return ("<section class='card'><div class='label'>Pronostic final · ancienne méthode</div>"
            "<h2>Figé à %s</h2>"
            "<p class='note'>Ce pronostic a été figé une heure avant le départ, selon l'ancienne méthode. Il reste "
            "affiché pour l'historique.</p><ul class='liste-simple'>%s</ul></section>") % (
                _heure_paris(final["fige_le"]), items)


def _suivi_reel_html():
    """Suivi réel : perte moyenne du vainqueur du modèle et du hasard, sur les courses déjà arrivées."""
    import suivi
    lignes, moyennes = suivi.comparaison_reelle()
    if not lignes:
        return "Suivi réel : aucune course arrivée n'est encore enregistrée."

    def f(v):
        return ("%.2f" % v).replace(".", ",") if v is not None else "—"

    n = len(lignes)
    return ("Suivi réel sur %d course%s arrivée%s, perte moyenne du vainqueur : modèle %s, hasard %s. "
            "Plus c'est bas, mieux c'est." % (n, "" if n == 1 else "s", "" if n == 1 else "s",
                                             f(moyennes["modele"][0]), f(moyennes["hasard"][0])))


def _libelle_pronostic(course, avec_cotes=False, fige_le=None):
    """Statut du pronostic affiché : le pronostic du soir, ou l'heure de son figement le jour même (heure de Paris)."""
    if not fige_le:
        return "Pronostic du soir"
    import datetime as dt
    from zoneinfo import ZoneInfo
    paris = dt.datetime.fromisoformat(fige_le).replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Paris"))
    jour_course = (course.get("reunion") or {}).get("date_reunion") or ""
    if paris.date().isoformat() < jour_course:
        return "Pronostic du soir"
    return "Pronostic figé le jour même à %s" % paris.strftime("%H h %M")


def generer(chemin_page, avec_cotes=False, journee=None, fige_le=None, vigilance=None, modele=None, avis=None,
            soir=None, final=None):
    """Page du quinté. Le pronostic affiché est celui du soir, figé : sans journal, il est calculé à partir de la page
    de la course. Les cotes n'entrent plus dans la page : avec_cotes, vigilance et modele sont acceptés pour
    compatibilité et ignorés. final : pronostic final historique (ancienne méthode), s'il existe."""
    course = ae.charger_etat(chemin_page)
    lignes_live = ae.analyser(course)
    ordres = ae.simuler(lignes_live)
    prob_live = ae.probabilites(ordres, lignes_live)
    combis_live = ae.combinaisons_en_box(ordres, lignes_live)
    par_numero = {p["num_partant"]: p for p in course["partants"]}
    par_live = {l["numero"]: l for l in lignes_live}
    if soir and soir.get("chevaux"):
        figes = {c["numero"]: c for c in soir["chevaux"]}
        classement = sorted(figes, key=lambda n: (-figes[n]["score"], n))
        noms = {n: figes[n]["nom"] for n in figes}
        prob = {"victoire": {n: figes[n]["p_victoire"] for n in figes},
                "top3": {n: figes[n]["p_top3"] for n in figes},
                "top5": {n: figes[n]["p_top5"] for n in figes}}
        combis = soir.get("combinaisons") or combis_live
        ordre = list(soir.get("ordre_predit") or classement[:5])
    else:
        classement = [l["numero"] for l in lignes_live]
        noms = {l["numero"]: l["nom"] for l in lignes_live}
        prob, combis = prob_live, combis_live
        ordre = classement[:5]
    lignes = [par_live[n] for n in classement if n in par_live]
    jeux = ae.jeux(ordres, lignes) if len(lignes) >= 2 else {}
    reco = ae.recommandation_par_type(combis)
    np_set = {n for n, p in par_numero.items() if p.get("statut_part") == "NP"}
    favori = classement[0]

    reunion = course.get("reunion") or {}
    hippo = (reunion.get("hippodrome") or {}).get("name") or ""
    libelle = course.get("libcourt_prix_course") or ""
    num_reunion = reunion.get("num_reunion")
    num_course = course.get("num_course_pmu")
    date_iso = reunion.get("date_reunion") or ""
    partants = sum(1 for p in course["partants"] if p.get("statut_part") != "NP")
    puces = [_date_fr(date_iso),
             ("Départ %s" % course["heure_depart_course"]) if course.get("heure_depart_course") else "",
             ("%s m" % course["distance"]) if course.get("distance") else "",
             course.get("discipline") or "",
             "%d partants" % partants,
             (course.get("lib_corde_course") or "").replace("Corde ", "corde ")]
    puces_html = "".join("<span>%s</span>" % html.escape(c) for c in puces if c)

    chevaux_html = []
    for i, n in enumerate(classement, start=1):
        p = par_numero.get(n, {})
        l = par_live.get(n)
        driver = (l or {}).get("driver") or (p.get("monte") or {}).get("nom_monte") or ""
        entraineur = (l or {}).get("entraineur") or (p.get("entraineur") or {}).get("nom_entraineur") or ""
        np_tag = " <span class='tag np'>non-partant</span>" if n in np_set else ""
        detail = _critere_cheval(l, p, course.get("discipline")) if (l and n not in np_set) else ""
        chevaux_html.append(
            "<li class='cheval'><div class='cheval-tete'><span class='rang'>%d</span><div>"
            "<div class='nom'>n°%s %s%s</div><div class='sous'>%s · %s</div></div></div>"
            "<div class='mesures'><div><b>%s</b><small>gagner</small></div>"
            "<div><b>%s</b><small>top 3</small></div><div><b>%s</b><small>top 5</small></div></div>"
            "<div class='barre'><span style='width:%.1f%%'></span></div>%s</li>" % (
                i, n, html.escape(noms.get(n, "")), np_tag, html.escape(driver or "—"),
                html.escape(entraineur or "—"),
                pct(prob["victoire"].get(n, 0)), pct(prob["top3"].get(n, 0)), pct(prob["top5"].get(n, 0)),
                100 * prob["top3"].get(n, 0), detail))

    top5 = "".join("<div><b>%d</b><small>%s%s</small></div>" % (
        n, html.escape(noms.get(n, "")), " (non-partant)" if n in np_set else "") for n in ordre[:5])
    fav_txt = ("Le favori du modèle est <b>n°%s %s</b> : %s de chances de gagner, %s dans les trois premiers." % (
        favori, html.escape(noms.get(favori, "")), pct(prob["victoire"].get(favori, 0)),
        pct(prob["top3"].get(favori, 0))))
    q = reco.get("Quinté")
    boite = ""
    if q:
        boite = ("<div class='boite'><div class='label'>Quinté désordre · boîte conseillée</div>"
                 "<div class='numeros'>%s</div><p class='note'>%d combinaison%s · chances estimées : %s</p></div>") % (
            " · ".join(str(x) for x in q["chevaux"]), q["combinaisons"], "" if q["combinaisons"] == 1 else "s",
            pct(q["probabilite"]))
    recos = "".join(_recommandation_html(t, b) for t, b in reco.items())

    pronostic = (
        "<section class='card'><div class='label'>Notre choix</div><h2>Les cinq premiers</h2>"
        "<div class='top5'>%s</div><p class='note'>%s</p>%s</section>"
        "%s"
        "<section class='card'><div class='label'>Les chevaux</div><h2>Classement du modèle</h2>"
        "<p class='note'>Touchez un cheval pour voir ses critères et les commentaires Equidia.</p>"
        "<ol class='chevaux'>%s</ol></section>"
        "<section class='card'><div class='label'>Jeux</div><h2>Tiercé, quarté, quinté</h2>"
        "<p class='note'>Recommandé : la taille de boîte la plus probable, dans une limite de %d combinaisons par pari.</p>"
        "<div class='rec'>%s</div><details><summary>Toutes les boîtes</summary>%s</details></section>"
        "<section class='card'><div class='label'>Jeux simples</div><h2>Couplés, simples et trios</h2>%s</section>"
        "<section class='card'><div class='label'>Distinction</div><h2>Le gagnant et le top 5</h2>%s</section>"
        "<details class='card'><summary>Profil de la course et difficultés</summary>%s</details>"
        "%s"
        "<details class='card'><summary>Méthode et suivi</summary>%s</details>"
        "<details class='card'><summary>Statistiques Equidia</summary>%s</details>"
    ) % (top5, fav_txt, boite, _resume_final_html(final), "".join(chevaux_html),
         ae.BUDGET_COMBINAISONS, recos, _boites_html(combis, reco), _jeux_simples_html(jeux),
         _distinction(lignes, prob), _profil_course(course, lignes, par_numero),
         ("<details class='card'><summary>Avis combiné : presse et notre modèle</summary>%s</details>" % _avis_html(avis))
         if avis else "",
         _methode_html(), _statistiques_chevaux(course, lignes))

    onglets = ("<button type='button' role='tab' data-cible='pronostic' aria-selected='true'>Pronostic</button>"
               "<button type='button' role='tab' data-cible='resultat' aria-selected='false'>Résultat</button>")
    if journee:
        onglets += "<button type='button' role='tab' data-cible='recherche' aria-selected='false'>Recherche</button>"

    valeurs = {
        "titre_page": html.escape("Quinté %s R%sC%s" % (hippo.title(), num_reunion, num_course)),
        "libelle_jour": html.escape("Quinté+ du jour · R%s C%s" % (num_reunion, num_course)),
        "titre_h1": html.escape(("%s · %s" % (hippo, libelle)).strip(" ·")),
        "puces": puces_html,
        "statut": html.escape(_libelle_pronostic(course, False, fige_le)),
        "onglets": onglets,
        "pronostic": pronostic,
        "resultat": _partie_resultat(course, lignes, date_iso, chemin_page),
        "recherche": ("<div class='vue' data-vue='recherche' hidden>" + _recherche_html(journee) + "</div>")
                     if journee else "",
        "fond": _bouton_fond_html(),
        "fond_tete": FOND_TETE,
    }
    page = GABARIT
    for cle, valeur in valeurs.items():
        page = page.replace("@@%s@@" % cle, str(valeur))
    return page


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(generer(sys.argv[1]))
    print("écrit :", sys.argv[2])
