#!/usr/bin/env python3
"""Génère la page HTML du pronostic d'une course Equidia.

Usage :
    python3 quinte/rapport.py page_equidia.html sortie.html

Réutilise le modèle de analyse_equidia.py (notes Equidia, sans cotes).
"""
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyse_equidia as ae  # noqa: E402

GABARIT = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quinté Vincennes R1C1 5 novembre</title>
<style>
:root{color-scheme:light dark;--bg:#f6f6f8;--surface:#fff;--line:#e2e2e7;--text:#1c1c21;--muted:#6b6b76;--accent:#2f5da8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111113;--surface:#1b1b20;--line:#2a2a2e;--text:#f4f4f5;--muted:#8e8e93;--accent:#9cc6ff}}
:root[data-theme="dark"]{--bg:#111113;--surface:#1b1b20;--line:#2a2a2e;--text:#f4f4f5;--muted:#8e8e93;--accent:#9cc6ff}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif;padding:0 max(16px,env(safe-area-inset-right,0px)) 32px max(16px,env(safe-area-inset-left,0px))}
main{max-width:920px;margin:0 auto;padding-top:24px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:0 0 10px}
.meta{color:var(--muted);margin:0 0 16px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px}
.ordre{display:flex;flex-wrap:wrap;gap:6px}
.pastille{min-width:38px;height:38px;display:inline-flex;align-items:center;justify-content:center;border-radius:8px;background:var(--accent);color:#fff;font-weight:700}
.jeu{font-size:18px;font-weight:700}
.wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:8px 6px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.note{color:var(--muted);font-size:13px}
</style></head><body><main>
<h1>Pronostic quinté — @@titre@@</h1>
<p class="meta">@@date@@ · @@meta@@</p>

<section class="card"><h2>Ordre d'arrivée probable</h2>
<div class="ordre">@@ordre@@</div>
<p class="note">Favori du modèle : n°@@fav_num@@ @@fav_nom@@ (note @@fav_score@@). L'ordre exact est très peu probable : @@p_ordre@@.</p></section>

<section class="card"><h2>Jeu le plus probable</h2>
<div class="jeu">@@jeu_type@@</div>
<p class="note">@@jeu_sel@@</p>
<p class="note">Quinté désordre en box 7 (n°@@box7@@) : @@p_box7@@.</p></section>

<section class="card wrap"><h2>Chevaux et probabilités</h2>
<table><thead><tr><th>#</th><th class="num">N°</th><th>Cheval</th><th>Driver</th><th class="num">Note</th><th class="num">1er</th><th class="num">Top 3</th><th class="num">Top 5</th></tr></thead>
<tbody>@@lignes@@</tbody></table></section>

<section class="card wrap"><h2>Probabilités des jeux</h2>
<table><thead><tr><th>Jeu</th><th class="num">Probabilité</th></tr></thead><tbody>@@jeux@@</tbody></table>
<p class="note">Estimations par simulation (200 000 ordres). Le modèle a été validé sur 30 quintés passés : meilleur que le hasard, mais sur un petit échantillon. Les cotes ne sont pas utilisées. Jeu responsable.</p></section>
</main></body></html>
"""


def pct(x):
    return "%.1f %%" % (100 * x)


def _jeu_conseille(jeux):
    """Jeu le plus probable parmi les jeux simples, couplés et trios."""
    candidats = {k: v for k, v in jeux.items() if k.startswith(("Simple", "Couplé", "Trio désordre"))}
    nom, p = max(candidats.items(), key=lambda kv: kv[1])
    return nom, "Probabilité estimée : %s." % pct(p)


def generer(chemin_page):
    course = ae.charger_etat(chemin_page)
    lignes = ae.analyser(course)
    ordres = ae.simuler(lignes)
    prob = ae.probabilites(ordres, lignes)
    jeux = ae.jeux(ordres, lignes)
    ordre = [l["numero"] for l in lignes[:5]]
    box7 = [l["numero"] for l in lignes[:7]]
    favori = lignes[0]

    titre = "%s R%sC%s — %s" % (
        course["reunion"]["hippodrome"]["name"], course["reunion"]["num_reunion"],
        course["num_course_pmu"], course.get("libcourt_prix_course") or "")
    date = course["reunion"]["date_reunion"]
    meta = "%s · %s m · %s partants" % (course.get("discipline"), course["distance"], len(lignes))

    lignes_html = []
    for i, l in enumerate(lignes, 1):
        n = l["numero"]
        lignes_html.append(
            "<tr><td>%d</td><td class='num'>%s</td><td>%s</td><td>%s</td>"
            "<td class='num'>%.3f</td><td class='num'>%s</td><td class='num'>%s</td><td class='num'>%s</td></tr>"
            % (i, n, html.escape(l["nom"]), html.escape(l["driver"] or ""), l["score"],
               pct(prob["victoire"][n]), pct(prob["top3"][n]), pct(prob["top5"][n])))

    jeux_html = "".join("<tr><td>%s</td><td class='num'>%s</td></tr>" % (html.escape(k), pct(v))
                        for k, v in sorted(jeux.items(), key=lambda kv: -kv[1]))

    nom_jeu, phrase_jeu = _jeu_conseille(jeux)
    cle_ordre = "Quinté ordre %s" % "-".join(str(x) for x in ordre)
    valeurs = {
        "titre": html.escape(titre),
        "date": html.escape(date),
        "meta": html.escape(meta),
        "ordre": "".join("<span class='pastille'>%d</span>" % n for n in ordre),
        "fav_num": favori["numero"],
        "fav_nom": html.escape(favori["nom"]),
        "fav_score": "%.3f" % favori["score"],
        "p_ordre": pct(jeux.get(cle_ordre, 0.0)),
        "jeu_type": html.escape(nom_jeu),
        "jeu_sel": html.escape(phrase_jeu),
        "box7": ", ".join(str(x) for x in box7),
        "p_box7": pct(jeux.get("Quinté désordre box 7", 0.0)),
        "lignes": "".join(lignes_html),
        "jeux": jeux_html,
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
