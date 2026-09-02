import test from 'node:test';
import assert from 'node:assert/strict';
import {
  chinese,
  english,
  getCopy,
  languageFromPath,
  languagePath,
} from '../lib/copy.ts';

function entries(value, path = '') {
  return Object.entries(value).flatMap(([key, child]) =>
    typeof child === 'string'
      ? [[`${path}.${key}`, child]]
      : entries(child, `${path}.${key}`),
  );
}
test('English covers every Chinese copy field with no untranslated Chinese', () => {
  const zh = entries(chinese),
    en = entries(english);
  assert.deepEqual(
    en.map(([key]) => key),
    zh.map(([key]) => key),
  );
  for (const [key, value] of en) {
    assert.ok(
      value.trim().length > 0 || key === '.observation.titlePrefix',
      key,
    );
    assert.doesNotMatch(value, /[\u3400-\u9fff]/u, key);
  }
});
test('language paths are explicit and do not leak to similar route names', () => {
  assert.equal(languageFromPath('/'), 'zh');
  assert.equal(languageFromPath('/en'), 'en');
  assert.equal(languageFromPath('/en/'), 'en');
  assert.equal(languageFromPath('/english'), 'zh');
  for (const language of ['zh', 'en'])
    assert.equal(languageFromPath(languagePath(language)), language);
  assert.equal(getCopy('en'), english);
  assert.equal(getCopy('zh'), chinese);
});
test('English retains all focus areas, examples, process steps, limits and projection labels', () => {
  assert.equal(english.interests.length, 4);
  assert.equal(english.examples.length, 3);
  assert.deepEqual(
    english.examples.map(({ kind }) => kind),
    ['brownian', 'gravity', 'symmetry'],
  );
  assert.equal(english.steps.length, 4);
  assert.equal(english.boundaries.length, 3);
  assert.deepEqual(Object.keys(english.observation.views), [
    'oblique',
    'front',
    'side',
  ]);
  assert.match(english.methodLimit, /not a demonstrated advantage/);
  assert.match(english.boundaries[2].body, /stop decisions stand/);
  assert.match(english.observation.disclaimer, /not experimental data/);
});
