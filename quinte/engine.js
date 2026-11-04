/*
 * Moteur d'analyse de course (quinté du jour).
 *
 * Principe : on note uniquement la PERFORMANCE des chevaux (résultats passés,
 * adéquation au terrain, à la distance, à la corde, à l'hippodrome, fraîcheur).
 * Les cotes ne sont jamais utilisées : le moteur les ignore même si elles sont
 * présentes dans les données.
 *
 * Fonction principale : analyserCourse(course) -> analyse complète.
 * Module sans dépendance : utilisable dans le navigateur (window.QuinteEngine)
 * et sous Node (require).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.QuinteEngine = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Poids des critères (somme quelconque : on normalise).
  var POIDS = {
    forme: 0.30,
    regularite: 0.10,
    terrain: 0.15,
    distance: 0.15,
    corde: 0.10,
    hippodrome: 0.05,
    fraicheur: 0.05
  };

  var LIBELLES = {
    forme: 'Forme récente',
    regularite: 'Régularité',
    terrain: 'Adéquation terrain',
    distance: 'Adéquation distance',
    corde: 'Adéquation corde',
    hippodrome: 'Connaissance de l\'hippodrome',
    fraicheur: 'Fraîcheur'
  };

  var TOLERANCE_DISTANCE = 150;   // mètres de tolérance pour « même distance »
  var NB_COURSES_FORME = 8;       // nombre de courses prises en compte pour la forme
  var DECROISSANCE = 0.85;        // poids de la récence (1re course = 1, puis x0.85, ...)
  var FACTEUR_AUTRE_DISCIPLINE = 0.5;
  var SEUIL_MARGE_NETTE = 0.08;   // écart 1er / 2e au-delà duquel un favori se détache
  var SCORE_NEUTRE = 0.5;         // valeur utilisée quand une donnée est absente

  // Regroupement des terrains en 3 familles.
  var TERRAIN_GROUPES = {
    sec: ['tres bon', 'bon', 'bon leger', 'leger', 'sec'],
    intermediaire: ['assez souple', 'bon souple', 'souple', 'tres souple'],
    lourd: ['collant', 'lourd', 'tres lourd', 'profond']
  };

  function norm(s) {
    return String(s == null ? '' : s)
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .toLowerCase().trim().replace(/\s+/g, ' ');
  }

  function groupeTerrain(t) {
    var n = norm(t);
    if (!n) return '';
    for (var g in TERRAIN_GROUPES) {
      if (TERRAIN_GROUPES[g].indexOf(n) !== -1) return g;
    }
    return 'autre:' + n;
  }

  function pct(x) { return Math.round(x * 100); }
  function arrondi(x) { return Math.round(x * 1000) / 1000; }

  /**
   * Note d'une arrivée entre 0 et 1 (1 = victoire, 0 = non classé / disqualifié).
   * place : numéro d'arrivée ; toute valeur non numérique (D, T, A, Arr...) vaut 0.
   */
  function scorePlace(place, nbPartants) {
    var s = String(place == null ? '' : place).trim();
    if (!/^\d+$/.test(s)) return 0;
    var p = parseInt(s, 10);
    var n = Math.max(parseInt(nbPartants, 10) || 0, p);
    if (n <= 1) return 1;
    return 1 - (p - 1) / (n - 1);
  }

  function scoreCourse(run) {
    return scorePlace(run.place, run.partants);
  }

  function memeDiscipline(run, course) {
    return !run.discipline || !course.discipline || norm(run.discipline) === norm(course.discipline);
  }

  function moyenne(items) {
    if (!items.length) return null;
    var s = 0;
    for (var i = 0; i < items.length; i++) s += items[i];
    return s / items.length;
  }

  function jours(dateA, dateB) {
    var a = Date.parse(dateA), b = Date.parse(dateB);
    if (isNaN(a) || isNaN(b)) return null;
    return Math.round((b - a) / 86400000);
  }

  function scoreFraicheur(j) {
    if (j === null) return null;
    if (j < 0) return null;            // date future : incohérente, on ignore
    if (j < 7) return 0.7;
    if (j <= 14) return 0.9;
    if (j <= 60) return 1;
    if (j <= 90) return 0.75;
    if (j <= 150) return 0.5;
    return 0.3;
  }

  /** Une composante = { valeur: 0..1 ou null, nb: nombre de courses utilisées, detail: texte }. */
  function composante(valeur, nb, detail) {
    return { valeur: valeur === null ? null : arrondi(valeur), nb: nb, detail: detail };
  }

  function evaluerCheval(cheval, course) {
    var runs = (cheval.historique || []).slice().sort(function (a, b) {
      return String(b.date || '').localeCompare(String(a.date || ''));
    });
    var comp = {};

    // 1. Forme récente : moyenne pondérée par la récence, discipline comparable prioritaire.
    var recent = runs.slice(0, NB_COURSES_FORME);
    var sumW = 0, sumV = 0;
    recent.forEach(function (r, i) {
      var w = Math.pow(DECROISSANCE, i) * (memeDiscipline(r, course) ? 1 : FACTEUR_AUTRE_DISCIPLINE);
      sumW += w;
      sumV += w * scoreCourse(r);
    });
    var forme = sumW ? sumV / sumW : null;
    comp.forme = composante(forme, recent.length,
      recent.length
        ? 'Dernières ' + recent.length + ' course(s) : ' + recent.map(function (r) { return String(r.place); }).join(', ')
        : 'aucune course connue');

    // 2. Régularité : part des arrivées dans le top 3 (hors non-classés).
    var top3 = recent.filter(function (r) { return /^\d+$/.test(String(r.place)) && parseInt(r.place, 10) <= 3; }).length;
    comp.regularite = composante(recent.length ? top3 / recent.length : null, recent.length,
      recent.length ? top3 + ' podium(s) sur ' + recent.length : 'aucune course connue');

    // 3. Terrain : mêmes familles de terrain que la course.
    var gCourse = groupeTerrain(course.terrain);
    if (gCourse) {
      var terr = runs.filter(function (r) { return groupeTerrain(r.terrain) === gCourse; });
      var vT = moyenne(terr.map(scoreCourse));
      comp.terrain = composante(vT, terr.length, terr.length
        ? terr.length + ' course(s) sur terrain ' + norm(course.terrain)
        : 'aucune course sur terrain ' + norm(course.terrain));
    } else {
      comp.terrain = composante(null, 0, 'terrain de la course non renseigné');
    }

    // 4. Distance : courses à ± TOLERANCE_DISTANCE mètres.
    if (course.distance) {
      var dist = runs.filter(function (r) {
        return r.distance && Math.abs(Number(r.distance) - Number(course.distance)) <= TOLERANCE_DISTANCE;
      });
      var vD = moyenne(dist.map(scoreCourse));
      comp.distance = composante(vD, dist.length, dist.length
        ? dist.length + ' course(s) sur ' + course.distance + ' m (± ' + TOLERANCE_DISTANCE + ' m)'
        : 'aucune course sur cette distance');
    } else {
      comp.distance = composante(null, 0, 'distance de la course non renseignée');
    }

    // 5. Corde.
    if (norm(course.corde)) {
      var cordes = runs.filter(function (r) { return norm(r.corde) === norm(course.corde); });
      comp.corde = composante(moyenne(cordes.map(scoreCourse)), cordes.length, cordes.length
        ? cordes.length + ' course(s) à la corde ' + norm(course.corde)
        : 'aucune course à la corde ' + norm(course.corde));
    } else {
      comp.corde = composante(null, 0, 'corde non renseignée');
    }

    // 6. Hippodrome.
    if (norm(course.hippodrome)) {
      var hippo = runs.filter(function (r) { return norm(r.hippodrome) === norm(course.hippodrome); });
      comp.hippodrome = composante(moyenne(hippo.map(scoreCourse)), hippo.length, hippo.length
        ? hippo.length + ' course(s) à ' + course.hippodrome
        : 'jamais couru à ' + course.hippodrome);
    } else {
      comp.hippodrome = composante(null, 0, 'hippodrome non renseigné');
    }

    // 7. Fraîcheur : jours depuis la dernière course.
    var jDerniere = runs.length && course.date ? jours(runs[0].date, course.date) : null;
    var vF = scoreFraicheur(jDerniere);
    comp.fraicheur = composante(vF, runs.length ? 1 : 0,
      jDerniere === null ? 'date de dernière course inconnue' : 'dernière course il y a ' + jDerniere + ' jour(s)');

    // Score global : moyenne pondérée, donnée absente = neutre (0,5).
    var total = 0, poidsTotal = 0, donnees = 0;
    Object.keys(POIDS).forEach(function (k) {
      var v = comp[k].valeur;
      if (v !== null) donnees++;
      total += POIDS[k] * (v === null ? SCORE_NEUTRE : v);
      poidsTotal += POIDS[k];
    });
    var score = total / poidsTotal;

    // Points forts / faibles, uniquement sur les composantes renseignées.
    var forces = [], faiblesses = [];
    Object.keys(POIDS).forEach(function (k) {
      var v = comp[k].valeur;
      if (v === null) return;
      if (v >= 0.7) forces.push(LIBELLES[k]);
      else if (v < 0.4) faiblesses.push(LIBELLES[k]);
    });

    var confiance = (runs.length >= 5 && donnees >= 5) ? 'élevée'
      : (runs.length >= 3 ? 'moyenne' : 'faible');

    return {
      numero: cheval.numero,
      nom: cheval.nom,
      score: arrondi(score),
      confiance: confiance,
      nbCourses: runs.length,
      composantes: comp,
      forces: forces,
      faiblesses: faiblesses,
      commentaire: commentaire(cheval, comp, score, confiance, forces, faiblesses)
    };
  }

  function commentaire(cheval, comp, score, confiance, forces, faiblesses) {
    var morceaux = [];
    morceaux.push(cheval.nom + ' : note ' + pct(score) + '/100, confiance ' + confiance + '.');
    Object.keys(POIDS).forEach(function (k) {
      morceaux.push(LIBELLES[k] + ' : ' + comp[k].detail + (comp[k].valeur === null ? '' : ' (' + pct(comp[k].valeur) + '/100)') + '.');
    });
    if (forces.length) morceaux.push('Points forts : ' + forces.join(', ') + '.');
    if (faiblesses.length) morceaux.push('Points faibles : ' + faiblesses.join(', ') + '.');
    return morceaux.join(' ');
  }

  /** Vérifie les données et renvoie la liste des avertissements (lève une erreur si inutilisable). */
  function valider(course) {
    if (!course || typeof course !== 'object') throw new Error('Données de course invalides (objet JSON attendu).');
    if (!Array.isArray(course.partants) || course.partants.length < 2) {
      throw new Error('Il faut au moins 2 partants dans "partants".');
    }
    var avert = [];
    var numeros = {};
    course.partants.forEach(function (c, i) {
      if (!c || typeof c.nom !== 'string' || !c.nom.trim()) throw new Error('Partant ' + (i + 1) + " : champ \"nom\" manquant.");
      if (c.numero == null) throw new Error('Partant ' + (i + 1) + ' (' + c.nom + ') : champ "numero" manquant.');
      if (numeros[c.numero]) throw new Error('Numéro ' + c.numero + ' présent deux fois.');
      numeros[c.numero] = true;
      if (!Array.isArray(c.historique) || c.historique.length === 0) {
        avert.push(c.nom + " : pas d'historique, note neutre.");
      }
    });
    if (!course.terrain) avert.push('Terrain non renseigné : critère terrain ignoré.');
    if (!course.distance) avert.push('Distance non renseignée : critère distance ignoré.');
    if (!course.corde) avert.push('Corde non renseignée : critère corde ignoré.');
    if (course.partants.length < 5) avert.push('Moins de 5 partants : pas de quinté complet.');
    return avert;
  }

  /** Choix du jeu conseillé selon la netteté du favori. */
  function choisirJeu(chevaux) {
    var marge = chevaux[0].score - (chevaux[1] ? chevaux[1].score : 0);
    var n1 = chevaux[0];
    if (marge >= SEUIL_MARGE_NETTE && n1.score >= 0.6) {
      return {
        type: 'Simple gagnant',
        selection: [n1.numero],
        alternative: chevaux[1] ? 'Couplé ordre n°' + n1.numero + ' – n°' + chevaux[1].numero : null,
        justification: 'Un cheval se détache nettement (écart de ' + pct(marge) + ' points entre le 1er et le 2e).'
      };
    }
    var box = chevaux.slice(0, Math.min(4, chevaux.length)).map(function (c) { return c.numero; });
    return {
      type: 'Trio désordre (box ' + box.length + ')',
      selection: box,
      alternative: chevaux.length >= 5 ? 'Quinté+ désordre sur les 5 premiers : n°' + chevaux.slice(0, 5).map(function (c) { return c.numero; }).join(' – n°') : null,
      justification: 'Course ouverte : écart de ' + pct(marge) + ' points seulement entre le 1er et le 2e, on couvre les 4 premiers.'
    };
  }

  /** Analyse complète d'une course. */
  function analyserCourse(course) {
    var avertissements = valider(course);
    var chevaux = course.partants.map(function (c) { return evaluerCheval(c, course); });
    chevaux.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      var fa = a.composantes.forme.valeur || 0, fb = b.composantes.forme.valeur || 0;
      if (fb !== fa) return fb - fa;
      return Number(a.numero) - Number(b.numero);
    });
    chevaux.forEach(function (c, i) { c.rang = i + 1; });

    var marge = chevaux[0].score - (chevaux[1] ? chevaux[1].score : 0);
    var ordre = chevaux.slice(0, Math.min(5, chevaux.length)).map(function (c) { return c.numero; });
    var jeu = choisirJeu(chevaux);

    return {
      course: {
        date: course.date || null,
        hippodrome: course.hippodrome || null,
        libelle: course.libelle || null,
        discipline: course.discipline || null,
        distance: course.distance || null,
        terrain: course.terrain || null,
        corde: course.corde || null
      },
      avertissements: avertissements,
      chevaux: chevaux,
      ordreProbable: ordre,
      aSurveiller: chevaux.slice(5, 7).map(function (c) { return c.numero; }),
      margeFavori: arrondi(marge),
      jeu: jeu,
      note: 'Analyse fondée sur la performance uniquement : les cotes ne sont pas prises en compte.'
    };
  }

  return {
    analyserCourse: analyserCourse,
    evaluerCheval: evaluerCheval,
    scorePlace: scorePlace,
    groupeTerrain: groupeTerrain,
    valider: valider,
    POIDS: POIDS,
    LIBELLES: LIBELLES
  };
});
