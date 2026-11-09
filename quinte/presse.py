#!/usr/bin/env python3
"""Le pronostic de la presse, comparé au nôtre et au marché, quinté par quinté.

Procédure, pour chaque quinté :
1. Avant le départ : `presse.py capturer AAAA-MM-JJ` relève le pronostic publié par Equidia et notre classement du
   moment, et l'écrit dans quinte/journal/presse-AAAA-MM-JJ.json, avec l'heure de la capture (UTC). Un fichier
   existant n'est jamais réécrit : c'est le pré-enregistrement.
2. Après la course : `presse.py constat AAAA-MM-JJ` compare les arrivants à la presse, à notre classement et au marché
   (cote de départ), et imprime le tableau. `presse.py cumul` totalise tous les quintés enregistrés.

Une course déjà courue, sans capture avant le départ, s'enregistre avec `presse.py retro AAAA-MM-JJ R C` : elle est
marquée « retroactif » et ne vaut pas pré-enregistrement.

Comparaison commune à tous les quintés : la boîte des 8 premiers de chaque classement. Le classement de la presse est
celui de ses catégories, dans l'ordre affiché : bases, belles chances, outsiders, délaissés.
"""
import datetime
import html as H
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
JOURNAL = os.path.join(HERE, "journal")
BOITE = 8
FIN_DU_PRONOSTIC = ("Notre avis", "Arrivée définitive", "Arrivées Rapports", "LES PARTANTS")
# (libellé affiché, clé dans le fichier, nom de la catégorie), dans l'ordre du classement de la presse
CATEGORIES = [("Bases", "bases", "base"), ("Belles chances", "belles", "belle"),
              ("Outsiders", "outsiders", "outsider"), ("Délaissés", "delaisses", "délaissé")]


def chemin(date):
    return os.path.join(JOURNAL, "presse-%s.json" % date)


def texte(page_html):
    """Le texte visible d'une page : sans scripts ni balises."""
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page_html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", H.unescape(t))


def lire_pronostic(page_html):
    """Le pronostic publié par Equidia sur une page de course, ou None s'il n'y en a pas.

    Renvoie 'parier' (la boîte « Parier avec », si elle existe), sinon 'cinq' (les cinq chevaux du pronostic), et
    'bases', 'belles', 'outsiders', 'delaisses' (numéros dans l'ordre affiché). Lève ValueError si un numéro
    apparaît deux fois.
    """
    t = texte(page_html)
    debut = t.find("Pronostic Quinté")
    if debut < 0:
        return None
    bloc = t[debut:]
    fins = [bloc.find(m) for m in FIN_DU_PRONOSTIC if bloc.find(m) > 0]
    if fins:
        bloc = bloc[:min(fins)]
    b = bloc.find("Bases :")
    if b < 0:
        return None
    tete, groupes = bloc[:b], bloc[b:]
    nums = [int(x) for x in re.findall(r"(?:^|\s)(\d{1,2})\s+(?=[A-Z])", tete)]
    out = {"parier": None, "cinq": None}
    if "Parier avec" in tete:
        out["parier"] = nums
    else:
        out["cinq"] = nums
    marques = []
    for libelle, cle, _ in CATEGORIES:
        m = re.search(re.escape(libelle) + r"\s*:", groupes)
        if m:
            marques.append((m.start(), m.end(), cle))
    marques.sort()
    for k, (_, fin_libelle, cle) in enumerate(marques):
        fin = marques[k + 1][0] if k + 1 < len(marques) else len(groupes)
        out[cle] = [int(x) for x in re.findall(r"\d{1,2}", groupes[fin_libelle:fin])]
    for _, cle, _ in CATEGORIES:
        out.setdefault(cle, [])
    tous = out["bases"] + out["belles"] + out["outsiders"] + out["delaisses"]
    if len(tous) != len(set(tous)):
        raise ValueError("numéro en double dans le pronostic de la presse : %s" % tous)
    return out


def ordre_presse(p):
    """Le classement de la presse : bases, belles chances, outsiders, délaissés, dans l'ordre affiché."""
    return p["bases"] + p["belles"] + p["outsiders"] + p["delaisses"]


def categorie(p, numero):
    for _, cle, nom in CATEGORIES:
        if numero in p[cle]:
            return nom
    return "—"


def mesures(ordre, arrivants):
    """Pour un classement : combien d'arrivants dans la boîte de 8, et le rang du dernier arrivant (couverture)."""
    pos = {n: i + 1 for i, n in enumerate(ordre)}
    return len(set(ordre[:BOITE]) & set(arrivants)), max(pos[n] for n in arrivants)


def _marche(lignes):
    """Le classement du marché (cote de départ, à défaut la cote du registre). None si une cote manque.
    Renvoie aussi les cotes, par numéro."""
    cote = {}
    for l in lignes:
        for champ in ("cote_depart", "cote"):
            try:
                v = float(l[champ])
            except (TypeError, ValueError):
                continue
            if v > 0:
                cote[int(l["numero"])] = v
                break
    ordre = sorted(cote, key=lambda n: (cote[n], n)) if len(cote) == len(lignes) else None
    return ordre, cote


def _ecrire(date, donnees):
    os.makedirs(JOURNAL, exist_ok=True)
    with open(chemin(date), "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _url(date, r, c):
    import equidia as eq
    return "%s/courses/%s/R%d/C%d" % (eq.BASE, date, r, c)


def capturer(date):
    """Pré-enregistre, avant le départ, le pronostic de la presse et notre classement. Ne réécrit jamais un fichier."""
    import equidia as eq
    import analyse_equidia as ae
    if os.path.exists(chemin(date)):
        return "Déjà pré-enregistré : %s. Rien n'est réécrit." % chemin(date)
    q = eq.quinte_du_jour(date)
    if not q:
        return "Aucun quinté trouvé pour %s." % date
    r, c = q
    url = _url(date, r, c)
    presse = lire_pronostic(eq.get_html(url, fresh=True))
    if presse is None:
        return "Pas de pronostic de la presse sur %s." % url
    course = eq.course(date, r, c, fresh=True)
    if course.get("type_statut_course_id") != "before":
        return "La course n'est plus avant le départ : pas de pré-enregistrement."
    lignes = ae.analyser(course)
    probas = ae.probabilites(ae.simuler(lignes), lignes)
    notre = sorted(lignes, key=lambda l: (-l["score"], int(l["numero"])))
    donnees = {
        "date": date, "r": r, "c": c, "url": url,
        "hippodrome": ((course.get("reunion") or {}).get("hippodrome") or {}).get("name"),
        "heure_depart": course.get("heure_depart_course"),
        "retroactif": False,
        "capture_le_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "presse": presse,
        "notre": [{"numero": int(l["numero"]), "nom": l["nom"], "score": round(l["score"], 4), "rang": i + 1,
                   "p_victoire": round(probas["victoire"][int(l["numero"])], 4),
                   "p_top5": round(probas["top5"][int(l["numero"])], 4)} for i, l in enumerate(notre)],
    }
    _ecrire(date, donnees)
    return "Pré-enregistré : %s (%d partants)." % (chemin(date), len(lignes))


def retro(date, r, c):
    """Enregistre une course déjà courue : le pronostic de la presse lu sur la page, et notre classement du registre."""
    import equidia as eq
    import registre
    if os.path.exists(chemin(date)):
        return "Déjà enregistré : %s." % chemin(date)
    url = _url(date, r, c)
    presse = lire_pronostic(eq.get_html(url))
    if presse is None:
        return "Pas de pronostic de la presse sur %s." % url
    lignes = [l for l in registre.lire() if l["date"] == date and l["r"] == str(r) and l["c"] == str(c)]
    notre = sorted(lignes, key=lambda l: int(l["rang"]))
    donnees = {
        "date": date, "r": r, "c": c, "url": url,
        "hippodrome": lignes[0]["hippodrome"] if lignes else None,
        "heure_depart": None, "retroactif": True, "capture_le_utc": None, "presse": presse,
        "notre": [{"numero": int(l["numero"]), "nom": l["nom"], "score": float(l["score"]), "rang": int(l["rang"]),
                   "p_victoire": float(l["p_victoire"]) if l["p_victoire"] else None, "p_top5": None}
                  for l in notre],
    }
    _ecrire(date, donnees)
    return "Enregistré a posteriori : %s." % chemin(date)


def _charger(date):
    """Le pré-enregistrement d'un quinté, les lignes du registre pour cette course, et les arrivées (numéro -> rang)."""
    import registre
    with open(chemin(date), encoding="utf-8") as f:
        d = json.load(f)
    lignes = [l for l in registre.lire() if l["date"] == date and l["r"] == str(d["r"]) and l["c"] == str(d["c"])]
    arrivee = {int(l["numero"]): int(l["arrivee"]) for l in lignes if l["arrivee"].isdigit()}
    return d, lignes, arrivee


def _arrivants(arrivee):
    """Les cinq premiers, dans l'ordre d'arrivée ; None si l'arrivée n'est pas complète."""
    if len(arrivee) < 5 or min(arrivee.values()) != 1:
        return None
    return [n for n, a in sorted(arrivee.items(), key=lambda t: t[1]) if a <= 5]


def constat(date):
    """Compare les arrivants à la presse, à notre classement et au marché. Renvoie un texte en français."""
    d, lignes, arrivee = _charger(date)
    arr5 = _arrivants(arrivee)
    if arr5 is None:
        return "Pas encore d'arrivée complète pour %s." % date
    nom = {int(l["numero"]): l["nom"] for l in lignes}
    notre = [x["numero"] for x in d["notre"]]
    presse_ordre = ordre_presse(d["presse"])
    presse_ordre += [n for n in notre if n not in presse_ordre]
    marche, cote = _marche(lignes)

    L = ["## Quinté du %s · %s · R%dC%d" % (date, d.get("hippodrome") or "?", d["r"], d["c"]), "",
         "Arrivée : %s." % "-".join(str(n) for n in arr5),
         ("Retroactif : enregistré après la course, pas avant le départ." if d["retroactif"]
          else "Pré-enregistré le %s (UTC), avant le départ." % d["capture_le_utc"]), ""]
    if d["presse"]["cinq"]:
        L.append("- Presse, pronostic à 5 : %s, soit %d/5." % (
            "-".join(map(str, d["presse"]["cinq"])), len(set(d["presse"]["cinq"]) & set(arr5))))
    if d["presse"]["parier"]:
        pb = d["presse"]["parier"]
        L.append("- Presse, boîte « Parier avec » de %d : %d/5 dans la boîte, boîte complète : %s." % (
            len(pb), len(set(pb) & set(arr5)), "oui" if set(arr5) <= set(pb) else "non"))
    L.append("- Notre classement (sans cotes), top 5 : %d/5 ; boîte de %d : %d/5." % (
        len(set(notre[:5]) & set(arr5)), BOITE, mesures(notre, arr5)[0]))
    if marche:
        L.append("- Marché (cote de départ), top 5 : %d/5 ; boîte de %d : %d/5." % (
            len(set(marche[:5]) & set(arr5)), BOITE, mesures(marche, arr5)[0]))
    k_m = mesures(marche, arr5)[1] if marche else "—"
    L.append("- Couverture (rang du dernier arrivant) : presse %d, notre classement %d, marché %s." % (
        mesures(presse_ordre, arr5)[1], mesures(notre, arr5)[1], k_m))
    L += ["", "| n° | cheval | arrivée | presse | notre rang | marché | cote |", "|---:|---|---:|---|---:|---:|---:|"]
    pos_marche = {n: i + 1 for i, n in enumerate(marche)} if marche else {}
    for n in notre:
        a = arrivee.get(n)
        dans_boite = " (boîte)" if d["presse"]["parier"] and n in d["presse"]["parier"] else ""
        L.append("| %d | %s | %s | %s%s | %d | %s | %s |" % (
            n, nom.get(n, ""), a if a else "—", categorie(d["presse"], n), dans_boite, notre.index(n) + 1,
            pos_marche.get(n, "—"), ("%g" % cote[n]).replace(".", ",") if n in cote else "—"))
    return "\n".join(L) + "\n"


def cumul():
    """Totaux sur tous les quintés enregistrés dont l'arrivée est connue : arrivants dans la boîte de 8 et boîtes
    complètes, pour la presse, notre classement et le marché."""
    fichiers = sorted(f for f in os.listdir(JOURNAL) if f.startswith("presse-") and f.endswith(".json"))
    lignes = []
    for f in fichiers:
        date = f[len("presse-"):-len(".json")]
        d, rows, arrivee = _charger(date)
        arr5 = _arrivants(arrivee)
        if arr5 is None:
            continue
        notre = [x["numero"] for x in d["notre"]]
        presse_ordre = ordre_presse(d["presse"])
        presse_ordre += [n for n in notre if n not in presse_ordre]
        marche, _ = _marche(rows)
        lignes.append((date, mesures(presse_ordre, arr5), mesures(notre, arr5),
                       mesures(marche, arr5) if marche else None))
    if not lignes:
        return "Aucun quinté avec arrivée enregistré."
    n = len(lignes)
    avec_m = [x[3] for x in lignes if x[3]]
    texte_ = ("Sur %d quinté(s) avec arrivée, boîte de %d : arrivants dans la boîte en moyenne, presse %.2f, notre "
              "classement %.2f" % (n, BOITE, sum(x[1][0] for x in lignes) / n, sum(x[2][0] for x in lignes) / n))
    if avec_m:
        texte_ += ", marché %.2f (sur %d quinté(s))" % (sum(m[0] for m in avec_m) / len(avec_m), len(avec_m))
    texte_ += ". Boîte complète (5 sur 5) : presse %d, notre classement %d" % (
        sum(1 for x in lignes if x[1][1] <= BOITE), sum(1 for x in lignes if x[2][1] <= BOITE))
    if avec_m:
        texte_ += ", marché %d" % sum(1 for m in avec_m if m[1] <= BOITE)
    return texte_ + "."


def _categories(p):
    """La catégorie de la presse pour chaque numéro : base, belle, outsider ou délaissé."""
    return {n: nom for _, cle, nom in CATEGORIES for n in p[cle]}


def erreurs(selection, arr5):
    """Ce que la presse a raté : les arrivants hors de sa sélection, et les sélectionnés hors du top 5."""
    return sorted(set(arr5) - set(selection)), sorted(set(selection) - set(arr5))


def _valeurs(date, r, c):
    """La valeur de handicap de chaque partant, quand Equidia la publie pour cette course. Sinon, rien."""
    try:
        import equidia as eq
        course = eq.course(date, r, c)
    except Exception:
        return {}
    out = {}
    for p in (course or {}).get("partants", []):
        v = p.get("valeur")
        if v in (None, ""):
            v = (p.get("cheval") or {}).get("valeur")
        try:
            out[int(p["num_partant"])] = float(v)
        except (TypeError, ValueError):
            pass
    return out


def diagnostic(date):
    """Ce que la presse a fait, cheval par cheval : sa catégorie, nos six notes Equidia, notre musique, la valeur de
    handicap quand elle existe, notre rang. Après la course : ce qu'elle a raté, ce qu'elle a eu en trop, et le taux
    de réussite de chaque catégorie."""
    d, lignes, arrivee = _charger(date)
    p = d["presse"]
    cat = _categories(p)
    selection = p["parier"] or p["cinq"] or []
    valeur = _valeurs(date, d["r"], d["c"])
    comp = {int(l["numero"]): l for l in lignes}
    colonnes = ["n_musique", "n_aptitudes", "n_forme_cheval", "n_conditions", "n_bruits_ecuries"]
    L = ["## Diagnostic · quinté du %s · R%dC%d" % (date, d["r"], d["c"]), "",
         "| n° | cheval | presse | valeur | musique | aptitudes | forme | conditions | bruits | notre rang | arrivée |",
         "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    arr5 = _arrivants(arrivee)
    for x in d["notre"]:
        n = x["numero"]
        notes = []
        for col in colonnes:
            v = comp.get(n, {}).get(col)
            notes.append(("%.2f" % float(v)).replace(".", ",") if v else "—")
        val = ("%g" % valeur[n]).replace(".", ",") if n in valeur else "—"
        L.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %d | %s |" % (
            n, comp.get(n, {}).get("nom", ""), cat.get(n, "—"), val, notes[0], notes[1], notes[2], notes[3],
            notes[4], x["rang"], arrivee.get(n) or "—"))
    if arr5 is not None:
        hors, en_trop = erreurs(selection, arr5)
        L += ["", "Dans le top 5, hors de la sélection de la presse : %s." % (", ".join(map(str, hors)) or "aucun"),
              "Dans la sélection de la presse, hors du top 5 : %s." % (", ".join(map(str, en_trop)) or "aucun")]
        libelles = {"base": "bases", "belle": "belles chances", "outsider": "outsiders", "délaissé": "délaissés"}
        taux = []
        for nom in ["base", "belle", "outsider", "délaissé"]:
            horses = [n for n, k in cat.items() if k == nom]
            if horses:
                taux.append("%s %d/%d" % (libelles[nom], sum(1 for n in horses if n in arr5), len(horses)))
        L.append("Dans le top 5, par catégorie de la presse : %s." % " ; ".join(taux))
    return "\n".join(L) + "\n"


def main(argv):
    aide = "usage : presse.py capturer AAAA-MM-JJ | constat AAAA-MM-JJ | diagnostic AAAA-MM-JJ | retro AAAA-MM-JJ R C | cumul"
    if len(argv) < 2:
        print(aide)
        return 2
    cmd = argv[1]
    if cmd == "capturer" and len(argv) == 3:
        print(capturer(argv[2]))
    elif cmd == "constat" and len(argv) == 3:
        print(constat(argv[2]))
    elif cmd == "retro" and len(argv) == 5:
        print(retro(argv[2], int(argv[3]), int(argv[4])))
    elif cmd == "diagnostic" and len(argv) == 3:
        print(diagnostic(argv[2]))
    elif cmd == "cumul" and len(argv) == 2:
        print(cumul())
    else:
        print(aide)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
