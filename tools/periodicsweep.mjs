// Can a blind, clocked schedule keep Balloon Boy out of the office?
//
// The device cannot take the observation. A device-side vent-light read
// measured 230 ms at best, and in a live trial it never once completed inside
// the cams-down window: fourteen probes, fourteen "unavailable". Minus 7 is a
// clocked strategy, so the question is whether the mask response can be run on
// the clock instead of on a cue.
//
// BB walks five hops at 75% per 5 s interval, so he needs about 6.7 intervals
// to reach the opening, and g417's latched A = 2 means cams-down defers his
// hop rather than cancelling it -- he arrives eventually no matter how the
// cycle is phased. A periodic response has to come round faster than that.
//
//   node tools/periodicsweep.mjs [nights]
import { run } from './pilottest.mjs';
import * as C from '../src/config.js';

const N = +(process.argv[2] || 200);
console.log(`${N} nights per row. "every" is how often the mask response runs,`);
console.log('in cycles; each response costs about two cycles of the stall sweep.\n');
console.log('every   BB in office   foxy   BB->foxy   median   best   dominant death');

for (const periodic of [0, 3, 4, 5, 6, 7, 8, 10, 12]) {
  let foxy = 0, bbIn = 0, chain = 0, survived = 0;
  const depth = [];
  const causes = {};
  for (let i = 0; i < N; i++) {
    const r = run({ cycles: 80, sync: true, periodic,
      sim: { seed: (i * 2246822519) >>> 0 } });
    const s = r.sim;
    depth.push(s.frame / C.FPS);
    if (s.won) { survived++; continue; }
    causes[s.death.reason] = (causes[s.death.reason] || 0) + 1;
    if (s.death.reason === 'foxy') foxy++;
    if (s.bb.inside) bbIn++;
    if (s.bb.inside && s.death.reason === 'foxy') chain++;
  }
  depth.sort((a, b) => a - b);
  const top = Object.entries(causes).sort((a, b) => b[1] - a[1])[0];
  const label = periodic ? String(periodic) : 'never';
  console.log(
    `${label.padStart(5)}   ${String(bbIn).padStart(10)}   ` +
    `${String(foxy).padStart(4)}   ${String(chain).padStart(8)}   ` +
    `${depth[N >> 1].toFixed(0).padStart(5)}s   ${depth[N - 1].toFixed(0).padStart(4)}s   ` +
    `${top ? top[0] + ' ' + top[1] : '-'}` +
    (survived ? `   SURVIVED ${survived}` : ''));
}
