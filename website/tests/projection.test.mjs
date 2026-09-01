import test from 'node:test';
import assert from 'node:assert/strict';
import { project, ringPaths, views } from '../lib/projection.ts';

test('all views render the same 44 closed sampled rings', () => {
  for (const view of Object.keys(views)) {
    const rings = ringPaths(view);
    assert.equal(rings.length, 44);
    assert.equal(new Set(rings.map(r => r.id)).size, 44);
    for (const ring of rings) {
      assert.match(ring.d, /^M.* Z$/);
      assert.equal((ring.d.match(/L/g) || []).length, 64);
      assert.doesNotMatch(ring.d, /NaN|Infinity/);
    }
  }
});

test('projection changes positions without changing object geometry', () => {
  for (let u = 0; u < 6.28; u += .3) {
    for (let v = 0; v < 6.28; v += .3) {
      const originalNorm = (138 + 55 * Math.cos(v)) ** 2 + (55 * Math.sin(v)) ** 2;
      for (const { angle } of Object.values(views)) {
        const p = project(u, v, angle);
        assert.ok(Math.abs((p.x - 260) ** 2 + (p.y - 235) ** 2 + p.depth ** 2 - originalNorm) < 1e-8);
        assert.ok(p.x > 30 && p.x < 490 && p.y > 5 && p.y < 465);
      }
    }
  }
  assert.notDeepEqual(ringPaths('front'), ringPaths('side'));
  assert.notDeepEqual(ringPaths('front'), ringPaths('oblique'));
});
