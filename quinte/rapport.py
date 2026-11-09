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

GABARIT = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@titre_page@@</title>
@@fond_tete@@
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

.zone-details{padding:0;border-bottom:none;margin-bottom:14px}
.zone-details > summary{list-style:none;cursor:pointer;display:block;padding:18px 44px 16px 18px;position:relative}
.zone-details > summary::-webkit-details-marker{display:none}
.zone-details > summary::after{content:"+";position:absolute;right:18px;top:14px;font-size:22px;line-height:1;color:var(--muted);font-weight:400}
.zone-details[open] > summary::after{content:"\2212"}
.zone-details > summary:focus-visible{outline:2px solid var(--bleu);outline-offset:-2px;border-radius:8px}
.zone-details > summary .label{display:block}
.zone-details > summary h2{margin:4px 0 0}
.zone-details > :not(summary){margin-left:18px;margin-right:18px}
.zone-details > :last-child{margin-bottom:18px}


.entete h2{font-size:18px;margin:2px 0 10px;font-weight:600}
.puces{display:flex;flex-wrap:wrap;gap:6px}
.puces span{display:inline-block;font-size:12.5px;padding:3px 9px;border:1px solid var(--line);border-radius:4px;color:var(--text);background:var(--gris-bg)}


.arr-grand{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 4px}
.arr-grand .cell{flex:1 1 110px;min-width:96px;padding:16px 10px;border:1px solid var(--line);border-radius:8px;text-align:center;background:var(--surface)}
.arr-grand .cell b{display:block;font-size:40px;font-weight:700;line-height:1;color:var(--bleu)}
.arr-grand .cell .nom{display:block;font-size:12.5px;font-weight:600;margin-top:8px}
.arr-grand .cell small{display:block;font-size:11px;color:var(--muted);margin-top:2px}
.retenir{margin:6px 0 0 18px;padding:0;font-size:13.5px}
.retenir li{margin-bottom:4px}
.res-tab td.n,.res-tab th.n{text-align:right}


.onglets{display:flex;gap:6px;margin:0 0 14px;flex-wrap:wrap}
.onglets button{font:inherit;font-size:13.5px;font-weight:600;padding:8px 16px;border:1px solid var(--line);border-radius:6px;background:var(--surface);color:var(--muted);cursor:pointer}
.onglets button[aria-selected="true"]{background:var(--bleu);border-color:var(--bleu);color:#ffffff}
.onglets button:focus-visible{outline:2px solid var(--bleu);outline-offset:2px}
[hidden]{display:none!important}


.partie{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:22px 2px 10px;padding-bottom:6px;border-bottom:2px solid var(--line)}
.partie.resultat{color:var(--bleu);border-bottom-color:var(--bleu)}
.res-tab{width:100%;border-collapse:collapse;font-size:13.5px}
.res-tab th,.res-tab td{padding:7px 6px;border-bottom:1px solid var(--line);text-align:left}
.res-tab td.n,.res-tab th.n{text-align:right;font-variant-numeric:tabular-nums}
.ok-txt{color:var(--text);font-weight:600}
.concl{border-left:3px solid var(--bleu);padding:4px 0 4px 12px;margin:8px 0;font-size:13.5px}


@media (max-width:820px){
  .bloc-pari thead{display:none}
  .bloc-pari table,.bloc-pari tbody{display:block;width:100%}
  .bloc-pari tr{display:grid;grid-template-columns:1fr auto;grid-template-areas:"box tag" "nums nums" "comb chance";gap:6px 8px;border:1px solid var(--line);border-radius:6px;padding:10px 12px;margin-bottom:8px;background:var(--surface)}
  .bloc-pari tr.reco{border-color:var(--bleu)}
  .bloc-pari td{border:0;padding:0;text-align:left;font-size:13px;background:transparent}
  .bloc-pari td:nth-child(1){grid-area:box;font-weight:600}
  .bloc-pari td:nth-child(1)::before{content:"Box "}
  .bloc-pari td:nth-child(2){grid-area:nums}
  .bloc-pari td:nth-child(3){grid-area:comb;color:var(--muted)}
  .bloc-pari td:nth-child(3)::after{content:" combinaison(s)"}
  .bloc-pari td:nth-child(4){grid-area:chance;text-align:right;font-weight:600}
  .bloc-pari td:nth-child(6){grid-area:tag;text-align:right}
  .bloc-pari td.opt{display:none}
}


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
.recherche-form{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0 14px}
.recherche-form label{display:flex;flex-direction:column;gap:4px;flex:1 1 160px;font-size:13px;color:var(--muted)}
.recherche-form select{font:inherit;font-size:14px;padding:9px;border:1px solid var(--line);border-radius:6px;background:var(--surface);color:var(--text);width:100%}
.rech-resultat h3{font-size:16px;margin:12px 0 4px}
.rech-ordre{font-size:16px;font-weight:600;margin:8px 0}
.rech-resultat table{width:100%;border-collapse:collapse;font-size:13px}
.rech-resultat th,.rech-resultat td{padding:6px 4px;border-bottom:1px solid var(--line);text-align:left}
.rech-resultat th.n,.rech-resultat td.n{text-align:right;font-variant-numeric:tabular-nums}
.rech-bouton{font:inherit;font-size:14px;font-weight:600;padding:9px 16px;border:1px solid var(--bleu);background:var(--bleu);color:#ffffff;border-radius:6px;cursor:pointer;align-self:flex-end}
.rech-arrivee{font-size:15px;font-weight:600;margin:8px 0 2px}
.vigilance-liste, .modele-liste { margin: 8px 0 0; padding-left: 20px; display: grid; gap: 6px; font-size: 14px; }
.modele-liste { list-style: none; padding-left: 0; }
.modele-liste li { display: grid; grid-template-columns: 26px minmax(0, 1fr) auto; gap: 10px; align-items: center; }
.vigilance-groupe { display: grid; gap: 6px; margin-top: 12px; }
.tag.alerte-rouge { color: var(--rouge); background: var(--rouge-bg); }
.tag.alerte-gris { color: var(--gris); background: var(--gris-bg); }
/* Refonte reprise de la maquette : palette sarcelle, titres en serif, cartes arrondies, mode sombre */
:root{color-scheme:light;
  --bg:#f5f4ef;--surface:#ffffff;--line:#e2e0d8;--text:#1c1f24;--muted:#5f656d;
  --or:#0d6a5b;--or-bg:#d6ebe5;--bleu:#0d6a5b;--bleu-bg:#d6ebe5;
  --vert:#0d6a5b;--vert-bg:#d6ebe5;--violet:#0d6a5b;--violet-bg:#d6ebe5;
  --rouge:#9a4a00;--rouge-bg:#f8e6d2;--gris:#5f656d;--gris-bg:#ebe9e2;}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;
  --bg:#14161a;--surface:#1c1f24;--line:#2d3238;--text:#ececea;--muted:#a3a9b1;
  --or:#6fd6bf;--or-bg:#1d3a34;--bleu:#6fd6bf;--bleu-bg:#1d3a34;
  --vert:#6fd6bf;--vert-bg:#1d3a34;--violet:#6fd6bf;--violet-bg:#1d3a34;
  --rouge:#f2b36b;--rouge-bg:#3a2a1a;--gris:#a3a9b1;--gris-bg:#2a2e34;}}
:root[data-theme="dark"]{color-scheme:dark;
  --bg:#14161a;--surface:#1c1f24;--line:#2d3238;--text:#ececea;--muted:#a3a9b1;
  --or:#6fd6bf;--or-bg:#1d3a34;--bleu:#6fd6bf;--bleu-bg:#1d3a34;
  --vert:#6fd6bf;--vert-bg:#1d3a34;--violet:#6fd6bf;--violet-bg:#1d3a34;
  --rouge:#f2b36b;--rouge-bg:#3a2a1a;--gris:#a3a9b1;--gris-bg:#2a2e34;}
h1{font-family:ui-serif,Georgia,"Times New Roman",serif;font-size:26px;font-weight:600;line-height:1.2;letter-spacing:0;text-wrap:balance}
h2{font-family:ui-serif,Georgia,"Times New Roman",serif;font-size:20px;font-weight:600;line-height:1.25;letter-spacing:0;margin:0 0 8px;text-wrap:balance}
.hero h1{font-size:24px}
.entete h2{font-size:22px;font-weight:600;margin:2px 0 10px}
.card{border-radius:14px;padding:16px;box-shadow:none;border:1px solid var(--line)}
.card.accent-bleu,.card.accent-or,.card.accent-gris,.card.accent-violet,.card.accent-vert,.hero{border-left:1px solid var(--line)}
.label{font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.badge{display:inline-block;font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--bleu);background:var(--bleu-bg);border-radius:6px;padding:3px 8px;margin:0 0 6px}
.badge.gris{color:var(--muted);background:var(--gris-bg)}
.badge.alerte{color:var(--rouge);background:var(--rouge-bg)}
.sous{margin:2px 0 8px;font-size:14px;color:var(--muted)}
.puces span{border-radius:999px;background:transparent;color:var(--muted);font-size:12.5px;padding:3px 10px}
.tag{border-radius:6px;padding:2px 8px;font-size:12px;font-weight:600;letter-spacing:.01em}
.onglets button{border-radius:8px}
.barre{height:8px;border-radius:999px;background:var(--gris-bg);min-width:0}
.barre span{background:var(--bleu)}
.final-liste,.modele-liste{list-style:none;margin:8px 0 0;padding:0;display:grid;gap:10px}
.final-liste li{display:grid;grid-template-columns:24px minmax(0,1fr) minmax(0,40%);align-items:center;gap:10px}
.modele-liste li{display:grid;grid-template-columns:24px minmax(0,1fr) auto;align-items:center;gap:10px}
.rang{font-variant-numeric:tabular-nums;color:var(--muted)}
.nom{min-width:0;overflow-wrap:anywhere}
.nom small{display:block;font-size:12.5px;color:var(--muted)}
.mesure{display:grid;gap:4px;justify-items:end;min-width:0;font-variant-numeric:tabular-nums}
.mesure .barre{width:100%}
.ecarts{margin:8px 0 0;padding-left:18px;display:grid;gap:8px;font-size:14px}
.vigilance-groupe{display:grid;gap:6px;margin-top:12px}
.formule{margin:0;font-size:14px;color:var(--muted);border-top:1px solid var(--line);padding-top:10px}
.rech-sans{width:fit-content;font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--rouge);background:var(--rouge-bg);border-radius:6px;padding:3px 8px;margin:4px 0}
.rech-soustitre{font-weight:600;margin:10px 0 2px}
.rech-cotes{list-style:none;margin:6px 0 0;padding:0;font-size:14px}
.rech-cotes li{display:flex;justify-content:space-between;gap:8px;border-bottom:1px dotted var(--line);padding:4px 0}
.rech-cotes b{font-variant-numeric:tabular-nums;white-space:nowrap}
.rech-favori{font-weight:600;margin:8px 0 0}
@@fond_css@@</style></head><body><main>

@@entete@@
<div class='fond-ligne'>@@fond@@</div>
@@onglets@@
@@partie_resultat@@
@@partie_recherche@@
<div class="vue" data-vue="analyse">
@@blocs_final@@
<section class="card accent-bleu">
  <div class="label">1 · Quinté+ : les 5 premiers</div>
  <h2>Ordre d'arrivée probable</h2>
  <div class="ordre">@@ordre@@</div>
  <p class="note">Le favori du modèle est <strong>n°@@fav_num@@ @@fav_nom@@</strong> : @@fav_win@@ de chances de gagner, @@fav_top3@@ dans les trois premiers. Les chevaux 2 à 5 sont proches : la course reste ouverte.</p>
</section>
<section class="card accent-bleu">
  <div class="label">2 · Analyse des chevaux</div>
  <h2>Analyse par cheval</h2>
  <p class="note">Touchez un cheval pour voir ses critères, les commentaires Equidia et les faits de la fiche.</p>
  @@analyses@@
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
<section class="card accent-gris wrap">
  <div class="label">6 · Probabilités par cheval</div>
  <h2>Probabilités par cheval</h2>
  <table>
    <thead><tr><th>#</th><th class="num">N°</th><th>Cheval</th><th>Driver</th><th class="num">Note</th><th>1er</th><th>Top 3</th><th class="num">Top 5</th></tr></thead>
    <tbody>@@lignes@@</tbody>
  </table>
</section>
<section class="card accent-bleu">
  <div class="label">7 · Profil de la course et difficultés</div>
  <h2>Profil de la course et difficultés</h2>
  <p class="note">Ces éléments sont propres à cette course. « Mesuré » vient des données du jour ; « contexte » est une information de référence, non intégrée au calcul.</p>
  @@profil@@
</section>
<section class="card accent-bleu">
  <div class="label">8.1 · Méthode</div>
  <h2>Comment le modèle choisit ses chevaux</h2>
  <ol class="etapes">
    <li><strong>Musique et notes Equidia</strong> : la musique (les performances passées) pèse 40 % de la note, et les notes Equidia (aptitudes à la distance, forme, chronos, tandem driver-entraîneur, conditions, bruits d'écurie) 60 %.</li>
    <li><strong>Une note de 0 à 1</strong> par cheval, moyenne pondérée de ces critères. Une donnée absente compte pour la moyenne neutre (0,5).</li>
    <li><strong>Simulation de 200 000 arrivées</strong> : à chaque tirage, le cheval le mieux noté a le plus de chances de passer en premier, les autres suivent selon leur note (modèle Plackett-Luce, sensibilité K = 4 depuis le 9 novembre, K = 8 avant).</li>
    <li><strong>Probabilités</strong> : on compte, sur les 200 000 arrivées simulées, combien de fois chaque cheval gagne, finit dans les 3 ou les 5 premiers, et combien de fois chaque combinaison de jeu sort.</li>
    <li><strong>Pronostic du soir, puis pronostic final</strong> : le soir, le pronostic est publié sans cotes. Une heure avant le départ, il est recalculé et figé avec les cotes du moment : 70 % de cotes et 30 % de notre analyse. C'est ce pronostic final qui est gardé pour le bilan.</li>
  </ol>
  <p class="note"><strong>Validation</strong> : les réglages (poids de la musique, sensibilité, part des cotes) ont été choisis sur 48 courses terminées d'octobre–novembre 2026. Ces mêmes courses ont servi à les choisir : le résultat est donc optimiste. Seul le suivi des prochaines courses, ci-dessous, donnera une mesure indépendante. <strong>Ce qu'il ne prend pas en compte</strong> : la taille du peloton, le déferrage, le changement de driver, l'avis de l'entraîneur et le classement ELO de Turfin, faute de les avoir validés.</p>
</section>
<section class="card accent-bleu wrap">
  <div class="label">8.2 · Ce qui compte, ce qui est testé</div>
  <h2>Ce qui compte, ce qui est affiché, ce qui a été testé</h2>
  <table>
    <thead><tr><th>Critère</th><th>Statut dans la note</th><th>Résultat du test (log-loss, plus bas = mieux)</th></tr></thead>
    <tbody>
      <tr><td>Musique (performances passées)</td><td><span class="tag ok">Pris en compte, 40 %</span></td><td>2,34 avec la musique, 2,43 sans (ancien modèle)</td></tr>
      <tr><td>Notes Equidia : aptitude à la distance, forme, chronos, tandem, conditions, bruits</td><td><span class="tag ok">Pris en compte, 60 %</span></td><td>Incluses dans le 2,34</td></tr>
      <tr><td>Distance du jour</td><td><span class="tag ok">Via l'aptitude à la distance</span></td><td>Incluse dans les notes</td></tr>
      <tr><td>Corde (plat, obstacle)</td><td><span class="tag info">Affiché seulement</span></td><td>Non ajoutée au calcul</td></tr>
      <tr><td>Poids (plat, obstacle)</td><td><span class="tag info">Affiché seulement</span></td><td>Non ajouté au calcul</td></tr>
      <tr><td>Déferrage, avis de l'entraîneur, classement ELO</td><td><span class="tag info">Affiché seulement</span></td><td>Pas de données historiques pour les tester</td></tr>
      <tr><td>Cotes du jour</td><td><span class="tag info">Dans le pronostic final, à 70 %</span></td><td>2,11 seules, 2,12 mélangées à 70 %, 2,63 au hasard</td></tr>
    </tbody>
  </table>
  <p class="note">Vérifié sur 48 courses terminées (octobre–novembre 2026), perte moyenne du vainqueur : hasard 2,63 ; ancien modèle sans musique 2,43 ; nouveau modèle avec musique 2,34 ; cotes seules 2,11 ; mélange retenu 2,12. Au trot, le poids n'existe pas, donc il n'est pas affiché.</p>
  <p class="note">@@suivi_reel@@</p>
</section>
<section class="card accent-gris wrap">
  <div class="label">9 · Statistiques des chevaux</div>
  <h2>Statistiques Equidia de chaque cheval</h2>
  @@statistiques@@
</section>




<p class="foot">Le pronostic final mélange les cotes du jour (70 %) et notre analyse (30 %). Estimations, pas des garanties. Jouer comporte des risques : jeu responsable, interdit aux mineurs.</p>
</div>
</main>
<script>
(function(){
  var boutons=document.querySelectorAll(".onglets button");
  boutons.forEach(function(b){
    b.addEventListener("click",function(){
      boutons.forEach(function(x){x.setAttribute("aria-selected", x===b ? "true" : "false");});
      document.querySelectorAll("[data-vue]").forEach(function(v){ v.hidden = (v.getAttribute("data-vue") !== b.getAttribute("data-cible")); });
    });
  });
  document.querySelectorAll("nav.side a").forEach(function(a){
    a.addEventListener("click", function(){
      var cible = document.getElementById(a.getAttribute("href").slice(1));
      if (cible && cible.tagName === "DETAILS") { cible.open = true; }
    });
  });
})();
</script>
</body></html>
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


def _libelle_pronostic(course, avec_cotes, fige_le):
    """« Pronostic du soir » s'il a été figé la veille ; sinon l'heure réelle du figement (heure de Paris)."""
    if avec_cotes:
        return "Pronostic final, figé une heure avant le départ"
    if not fige_le:
        return "Pronostic du soir, sans les cotes"
    import datetime as dt
    from zoneinfo import ZoneInfo
    paris = dt.datetime.fromisoformat(fige_le).replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Paris"))
    jour_course = (course.get("reunion") or {}).get("date_reunion") or ""
    if paris.date().isoformat() < jour_course:
        return "Pronostic du soir, sans les cotes"
    return "Pronostic figé le jour même à %s, sans les cotes" % paris.strftime("%H h %M")


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
    """Pronostic figé avant la course (journal), ou None s'il n'existe pas."""
    chemin = os.path.join(JOURNAL_DIR, "%s.json" % date)
    if not os.path.exists(chemin):
        return None
    return json.load(open(chemin, encoding="utf-8"))


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
        "<h2 style='margin-top:18px'>Rapports essentiels (mise de base 2 €)</h2>"
        "<div class='wrap'><table class='res-tab'><thead><tr><th>Pari</th><th>Mode</th><th class='n'>Combinaison</th><th class='n'>Rapport</th></tr></thead>"
        "<tbody>%s</tbody></table></div></section>") % (grand, comparaison, reaction, rapports)
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


def _suivi_reel_html():
    """Suivi réel : perte moyenne du vainqueur sur les courses déjà arrivées, par méthode."""
    import suivi
    lignes, moyennes = suivi.comparaison_reelle()
    if not lignes:
        return "Suivi réel : aucune course arrivée n'est encore enregistrée."

    def f(v):
        return ("%.2f" % v).replace(".", ",") if v is not None else "—"

    n = len(lignes)
    m, mc, mm, mh = moyennes["modele"], moyennes["cotes"], moyennes["melange"], moyennes["hasard"]
    return ("Suivi réel sur %d course%s arrivée%s, perte moyenne du vainqueur : modèle %s (%d), "
            "cotes seules %s (%d), mélange %s (%d), hasard %s. Plus c'est bas, mieux c'est." % (
                n, "" if n == 1 else "s", "" if n == 1 else "s",
                f(m[0]), m[1], f(mc[0]), mc[1], f(mm[0]), mm[1], f(mh[0])))


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
  function cote(v){ return String(Math.round(v * 10) / 10).replace('.', ','); }
  function libellePronostic(x){
    if (!x.final) { return 'Notre analyse, figée le soir, sans les cotes.'; }
    var heure = x.final.fige_le.slice(11, 13) + ' h ' + x.final.fige_le.slice(14, 16);
    var part = Math.round(100 * x.final.part_cotes);
    if (part <= 0) { return 'Notre analyse, figée à ' + heure + ', sans les cotes.'; }
    if (part >= 100) { return 'Avec les cotes seules (trot), figé à ' + heure + '.'; }
    return 'Avec les cotes : ' + part + ' % de marché, ' + (100 - part) + ' % de modèle, figé à ' + heure + '.';
  }
  function sansPronostic(x){
    var avant = x.statut === 'before';
    out.appendChild(paragraphe('rech-sans', 'Pas de pronostic'));
    out.appendChild(paragraphe('note', avant
      ? "Aucun cheval n'a encore couru. Sans musique ni notes Equidia, le modèle ne peut pas les départager : la page n'affiche donc ni ordre, ni pourcentages."
      : "Aucun cheval n'avait de musique ni de note Equidia : le modèle ne pouvait pas les départager, la page n'a donc affiché ni ordre ni pourcentages."));
    if (x.conditions) { out.appendChild(paragraphe('note', 'Conditions : ' + x.conditions)); }
    var heure = x.cotes_releve ? x.cotes_releve.slice(11, 13) + ' h ' + x.cotes_releve.slice(14, 16) : '';
    out.appendChild(paragraphe('rech-soustitre', avant
      ? 'Cotes' + (heure ? ' à ' + heure : '') + ", à titre d'information"
      : "Dernières cotes avant le départ, à titre d'information"));
    out.appendChild(paragraphe('note', "Elles viennent du marché, pas du modèle. Liste dans l'ordre des numéros."));
    if (x.cotes && x.cotes.length) {
      var liste = document.createElement('ul');
      liste.className = 'rech-cotes';
      x.cotes.forEach(function(h){
        var li = document.createElement('li');
        var nom = document.createElement('span');
        nom.textContent = 'n°' + h.numero + ' ' + h.nom;
        var valeur = document.createElement('b');
        valeur.textContent = cote(h.cote);
        li.appendChild(nom);
        li.appendChild(valeur);
        liste.appendChild(li);
      });
      out.appendChild(liste);
      var favori = x.cotes.reduce(function(a, b){ return b.cote < a.cote ? b : a; });
      out.appendChild(paragraphe('rech-favori', 'Favori des cotes : n°' + favori.numero + ' ' + favori.nom + ', à ' + cote(favori.cote) + '.'));
    } else {
      out.appendChild(paragraphe('note', 'Cotes non encore publiées.'));
    }
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


def _cote_fr(x):
    return ("%g" % x).replace(".", ",") if x else "—"


def _resume_final_html(v):
    """Le pronostic final, avec les cotes : les cinq premiers, avec la part de chacun."""
    if not v:
        return ""
    maxi = max(v["melange"].values()) or 1
    lignes = ""
    for i, k in enumerate(v["ordre_final"][:5], start=1):
        lignes += ("<li><span class='rang'>%d</span><span class='nom'><b>n°%s</b> %s<small>cote %s</small></span>"
                   "<span class='mesure'><span class='barre'><span style='width:%.0f%%'></span></span><b>%s</b></span></li>") % (
            i, k, html.escape(v["noms"].get(k, "")), _cote_fr(v["cotes"].get(k)),
            100 * v["melange"][k] / maxi, pct(v["melange"][k]))
    return ("<section class='card'><span class='badge'>Référence</span><h2>Pronostic final</h2>"
            "<p class='sous'>Notre analyse, sans les cotes. Figée à %s.</p>"
            "<ol class='final-liste'>%s</ol></section>") % (_heure_paris(v["fige_le"]), lignes)


def _modele_seul_html(m):
    """Le pronostic du matin, sans cotes, gardé à côté du pronostic final pour comparer."""
    if not m:
        return ""
    lignes = "".join(
        "<li><span class='rang'>%d</span><span class='nom'><b>n°%s</b> %s</span><span class='note'>%d/100</span></li>" % (
            i, numero, html.escape(m["noms"].get(numero, "")), round(100 * m["notes"].get(numero, 0)))
        for i, numero in enumerate(m["ordre"], start=1))
    return ("<section class='card'><span class='badge gris'>Avis indépendant</span><h2>Modèle seul</h2>"
            "<p class='sous'>Sans cotes, figé à %s. Gardé pour comparer.</p>"
            "<ol class='modele-liste'>%s</ol></section>") % (_heure_paris(m["fige_le"]), lignes)


def _pourquoi_html(v):
    """Les trois chevaux dont le rang change le plus entre le modèle seul et le pronostic final."""
    if not v or not v.get("rang_soir"):
        return ""
    communs = [k for k in v["ordre_final"] if k in v["rang_soir"]]
    if not communs:
        return ""
    choisis = sorted(communs, key=lambda k: -abs(v["rang_soir"][k] - v["rang_final"][k]))[:3]
    items = ""
    for k in choisis:
        rs, rf, rm = v["rang_soir"][k], v["rang_final"][k], v["rang_marche"][k]
        suite = "Le marché le soutient." if rf < rs else "Le marché le juge moins probable."
        items += ("<li><b>n°%s %s</b> : %s pour le modèle, %s au final. Le marché le classe %s (cote %s). %s</li>") % (
            k, html.escape(v["noms"].get(k, "")), _ordinal(rs), _ordinal(rf), _ordinal(rm),
            _cote_fr(v["cotes"].get(k)), suite)
    return ("<section class='card'><h2>Pourquoi les deux diffèrent</h2>"
            "<ul class='ecarts'>%s</ul>"
            "</section>") % items


def _vigilance_html(v):
    """Zones de vigilance du pronostic final : chevaux où le modèle et le marché sont à deux fois d'écart."""
    if not v:
        return ""

    def liste(numeros):
        if not numeros:
            return "<p class='note'>Aucun cheval dans cette zone.</p>"
        items = ""
        for k in numeros:
            items += "<li><b>n°%s %s</b> : modèle %s, marché %s (cote %s)</li>" % (
                k, html.escape(v["noms"].get(k, "")), pct(v["pm"][k]), pct(v["pk"][k]), _cote_fr(v["cotes"].get(k)))
        return "<ul class='ecarts'>%s</ul>" % items

    return ("<section class='card'><h2>Zones de vigilance</h2>"
            "<p class='sous'>Chevaux où notre modèle et le marché sont à deux fois d'écart au moins, et qui ont au moins 6\u00a0%% de chances dans l'un des deux avis. Le marché sait peut-être quelque chose que nous ignorons.</p>"
            "<div class='vigilance-groupe'><span class='badge alerte'>Méfiance</span>"
            "<p class='note'>Le modèle y croit au moins deux fois plus que le marché.</p>%s</div>"
            "<div class='vigilance-groupe'><span class='badge gris'>À surveiller</span>"
            "<p class='note'>Le marché y croit au moins deux fois plus que le modèle.</p>%s</div>"
            "<p class='note'>Repère simple, pas encore validé sur nos courses. Ces écarts sont donnés à titre d'information : ils ne modifient pas notre pronostic.</p></section>") % (liste(v["mefiance"]), liste(v["surveiller"]))


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


def generer(chemin_page, avec_cotes=False, journee=None, fige_le=None, vigilance=None, modele=None):
    course = ae.charger_etat(chemin_page)
    lignes = ae.analyser(course)
    cotes = ae.cotes_de(course) if avec_cotes else None
    avec = bool(cotes)
    if avec:
        lignes = ae.melanger_cotes(lignes, cotes)
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
        "statistiques": _statistiques_chevaux(course, lignes),
        "ll_notes": "2,34", "ll_hasard": "2,63", "ll_corde": "—", "ll_poids": "—",
        "suivi_reel": _suivi_reel_html(),
        "partie_recherche": ("<div class='vue' data-vue='recherche' hidden>" + _recherche_html(journee) + "</div>") if journee else "",
        "combinaisons": "".join(combis_html),
        "lignes": "".join(lignes_html),
        "entete": _entete_html(course, avec, fige_le),
        "fond": _bouton_fond_html(),
        "fond_tete": FOND_TETE,
        "fond_css": FOND_CSS,
        "blocs_final": _resume_final_html(vigilance) + _modele_seul_html(modele) + _pourquoi_html(vigilance) + _vigilance_html(vigilance),
        "partie_resultat": "<div class='vue' data-vue='resultat' hidden>" + _partie_resultat(course, lignes, date, chemin_page) + "</div>",
        "onglets": "<div class='onglets' role='tablist'><button type='button' role='tab' data-cible='analyse' aria-selected='true'>Analyse</button><button type='button' role='tab' data-cible='resultat' aria-selected='false'>Résultat et rapports</button>"
                    + ("<button type='button' role='tab' data-cible='recherche' aria-selected='false'>Recherche</button>" if journee else "") + "</div>",
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
