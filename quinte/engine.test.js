// Tests du moteur d'analyse. Lancer avec : node --test quinte/
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const E = require('./engine.js');

const exemple = JSON.parse(fs.readFileSync(path.join(__dirname, 'exemple-course.json'), 'utf8'));

test('scorePlace : 1er = 1, dernier = 0, non classé = 0', () => {
  assert.equal(E.scorePlace(1, 10), 1);
  assert.equal(E.scorePlace(10, 10), 0);
  assert.equal(E.scorePlace('D', 10), 0);
  assert.equal(E.scorePlace('T', 10), 0);
  assert.ok(Math.abs(E.scorePlace(5, 10) - (1 - 4 / 9)) < 1e-9);
});

test('groupeTerrain : regroupe les libellés PMU', () => {
  assert.equal(E.groupeTerrain('Collant'), 'lourd');
  assert.equal(E.groupeTerrain('très souple'), 'intermediaire');
  assert.equal(E.groupeTerrain('Bon léger'), 'sec');
  assert.equal(E.groupeTerrain(''), '');
});

test('analyse : un bon cheval sur le bon terrain et la bonne distance passe devant', () => {
  const course = {
    distance: 2100, terrain: 'lourd', corde: 'droite', hippodrome: 'X', date: '2026-11-01',
    partants: [
      { numero: 1, nom: 'Bon', historique: [
        { date: '2026-10-20', hippodrome: 'X', distance: 2100, terrain: 'lourd', corde: 'droite', place: 1, partants: 8 },
        { date: '2026-10-01', hippodrome: 'X', distance: 2100, terrain: 'lourd', corde: 'droite', place: 2, partants: 8 },
        { date: '2026-09-01', hippodrome: 'X', distance: 2100, terrain: 'lourd', corde: 'droite', place: 1, partants: 8 },
      ] },
      { numero: 2, nom: 'Mauvais', historique: [
        { date: '2026-10-20', hippodrome: 'Y', distance: 1600, terrain: 'bon', corde: 'gauche', place: 9, partants: 10 },
        { date: '2026-10-01', hippodrome: 'Y', distance: 1600, terrain: 'bon', corde: 'gauche', place: 8, partants: 10 },
        { date: '2026-09-01', hippodrome: 'Y', distance: 1600, terrain: 'bon', corde: 'gauche', place: 10, partants: 10 },
      ] },
    ],
  };
  const r = E.analyserCourse(course);
  assert.equal(r.chevaux[0].numero, 1);
  assert.equal(r.chevaux[0].rang, 1);
  assert.ok(r.chevaux[0].score > r.chevaux[1].score);
});

test('analyse : les cotes sont ignorées', () => {
  const base = JSON.parse(JSON.stringify(exemple));
  const avec = JSON.parse(JSON.stringify(exemple));
  avec.partants.forEach((p, i) => { p.cote = i === 0 ? 1.5 : 90; p.cote_pmu = 99; });
  const a = E.analyserCourse(base).chevaux.map(c => [c.numero, c.score]);
  const b = E.analyserCourse(avec).chevaux.map(c => [c.numero, c.score]);
  assert.deepEqual(a, b);
});

test('analyse : exemple complet, quinté et jeu cohérents', () => {
  const r = E.analyserCourse(exemple);
  assert.equal(r.chevaux.length, 8);
  assert.equal(r.ordreProbable.length, 5);
  assert.equal(new Set(r.ordreProbable).size, 5);
  assert.ok(r.jeu.type);
  assert.ok(r.jeu.selection.length >= 1);
  // Le cheval sans historique ne doit pas être classé en tête.
  const hotel = r.chevaux.find(c => c.numero === 8);
  assert.equal(hotel.confiance, 'faible');
  assert.equal(hotel.rang > 1, true);
  // Chaque cheval a un commentaire non vide.
  r.chevaux.forEach(c => assert.ok(c.commentaire.length > 20));
});

test('analyse : favori net -> simple gagnant', () => {
  const hist = (p) => [1, 2, 1, 1, 2].map((pl, i) => ({ date: `2026-10-${10 + i}`, hippodrome: 'X', distance: 2100, terrain: 'souple', corde: 'droite', place: pl, partants: 10 }));
  const course = { date: '2026-11-01', hippodrome: 'X', distance: 2100, terrain: 'souple', corde: 'droite', partants: [
    { numero: 1, nom: 'Top', historique: hist() },
    { numero: 2, nom: 'Moyen', historique: [5, 6, 4, 7].map((pl, i) => ({ date: `2026-10-${10 + i}`, hippodrome: 'Y', distance: 1600, terrain: 'bon', corde: 'gauche', place: pl, partants: 10 })) },
    { numero: 3, nom: 'Faible', historique: [9, 10, 8].map((pl, i) => ({ date: `2026-10-${10 + i}`, hippodrome: 'Y', distance: 1600, terrain: 'bon', corde: 'gauche', place: pl, partants: 10 })) },
  ] };
  const r = E.analyserCourse(course);
  assert.equal(r.chevaux[0].numero, 1);
  assert.equal(r.jeu.type, 'Simple gagnant');
  assert.deepEqual(r.jeu.selection, [1]);
});

test('valider : rejette une course sans partants', () => {
  assert.throws(() => E.analyserCourse({ partants: [] }), /au moins 2 partants/);
  assert.throws(() => E.analyserCourse({ partants: [{ numero: 1 }, { numero: 2, nom: 'B' }] }), /nom/);
  assert.throws(() => E.analyserCourse({ partants: [{ nom: 'A' }, { numero: 2, nom: 'B' }] }), /numero/);
  assert.throws(() => E.analyserCourse({ partants: [{ numero: 1, nom: 'A' }, { numero: 1, nom: 'B' }] }), /deux fois/);
});
