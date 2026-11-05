#!/usr/bin/env python3
"""Collecte des données Equidia (courses, fiches chevaux) avec cache local.

Sources publiques de equidia.fr, lues dans le bloc JSON embarqué (serverApp-state) :
- page d'une course : partants, musique, driver, entraîneur, notes internes, arrivée ;
- page d'un cheval (/chevaux/<slug>) : 10 dernières courses avec date, hippodrome,
  distance, corde, driver et place.

Les cotes (cote_*, rapports, enjeux) ne sont jamais lues.
"""
import concurrent.futures as cf
import hashlib
import json
import os
import re
import time
import urllib.request

BASE = "https://www.equidia.fr"
CACHE = os.environ.get("EQUIDIA_CACHE", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache"))
UA = "Mozilla/5.0 (analyse-quinte; usage personnel)"
PAUSE = 0.15  # secondes entre requêtes, par fil


def _cache_path(url):
    os.makedirs(CACHE, exist_ok=True)
    return os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".html")


def get_html(url, fresh=False):
    chemin = _cache_path(url)
    if fresh and os.path.exists(chemin):
        os.remove(chemin)
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        html = r.read().decode("utf-8", errors="replace")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(html)
    time.sleep(PAUSE)
    return html


def etat(html):
    m = re.search(r'<script id="serverApp-state" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return None
    return json.loads(m.group(1))


def _chercher(o, cle_test):
    if isinstance(o, dict):
        if cle_test(o):
            yield o
        for v in o.values():
            yield from _chercher(v, cle_test)
    elif isinstance(o, list):
        for v in o:
            yield from _chercher(v, cle_test)


def course(date, r, c, fresh=False):
    """Renvoie la course (dict PMU) ou None si la page n'a pas de course. fresh=True : ignore le cache."""
    url = "%s/courses/%s/R%d/C%d" % (BASE, date, r, c)
    s = etat(get_html(url, fresh=fresh))
    if not s:
        return None
    trouves = [x for x in _chercher(s, lambda o: "partants" in o and "num_course_pmu" in o and o.get("guid") and o.get("distance"))]
    return trouves[0] if trouves else None


def statuts_reunion(date, r=1):
    """Liste des courses d'une réunion avec le flag is_quinte_plus."""
    url = "%s/courses/%s/R%d/C1" % (BASE, date, r)
    s = etat(get_html(url))
    if not s:
        return []
    out = []
    for x in _chercher(s, lambda o: "status_courses" in o):
        out = x["status_courses"]
        break
    return out


def quinte_du_jour(date):
    """Trouve la course Quinté+ d'une date (cherche dans R1, R2, R3)."""
    for r in (1, 2, 3):
        for st in statuts_reunion(date, r):
            if st.get("is_quinte_plus"):
                return r, st["num_course_pmu"]
    return None


def fiche_cheval(slug):
    """Dernières courses d'un cheval (liste de dicts simplifiés)."""
    if not slug:
        return []
    url = "%s/chevaux/%s" % (BASE, slug)
    s = etat(get_html(url))
    if not s:
        return []
    cle = [k for k in s if k.startswith("v2/chevaux/") and "/history" in k]
    if not cle:
        return []
    runs = []
    for r in s[cle[0]].get("results", []):
        reunion = r.get("reunion", {})
        partant_cible = None
        for p in r.get("partants", []):
            if (p.get("cheval") or {}).get("slug") == slug:
                partant_cible = p
                break
        if not partant_cible:
            continue
        runs.append({
            "date": reunion.get("date_reunion"),
            "hippodrome": (reunion.get("hippodrome") or {}).get("name") or reunion.get("lib_reunion"),
            "distance": r.get("distance"),
            "corde": r.get("lib_corde_course"),
            "discipline": r.get("discipline"),
            "driver": (partant_cible.get("monte") or {}).get("nom_monte"),
            "place_texte": partant_cible.get("texte_place_arrivee") or partant_cible.get("num_place_arrivee"),
            "nb_partants": r.get("nbdeclare_course"),
            "guid": r.get("guid"),
        })
    return runs


def fiches_en_parallele(slugs, workers=8):
    slugs = sorted({s for s in slugs if s})
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(zip(slugs, ex.map(lambda s: fiche_cheval_sans_erreur(s), slugs)))


def fiche_cheval_sans_erreur(slug):
    try:
        return fiche_cheval(slug)
    except Exception as e:  # réseau instable : on signale et on continue
        return {"erreur": str(e)}
