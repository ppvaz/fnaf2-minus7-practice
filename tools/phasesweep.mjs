// Where should the Minus 7 cycle sit against the game's 5 s clock?
//
// Minus 7 is clocked, not reactive. The human's Balloon Boy defence is not an
// observation at all -- MINUS-7-STRATEGY.md 6 Phase A is "the interval passes
// with cams down -> BB cannot move", because g417, his hop into the opening,
// is his only monitor-gated edge. So the question is not what the pilot can
// see, it is where the cams-down window sits.
//
// The engine's movement opportunities are `f % MO_FRAMES == 0` counted from
// frame 0, so a cycle starting at `base` puts them at cycle phase
// (-base) mod 5000. This sweeps that phase and reports what it costs.
//
//   node tools/phasesweep.mjs [nights]
import { run } from './pilottest.mjs';
import * as C from '../src/config.js';

const N = +(process.argv[2] || 200);
// Phase alignment only protects Balloon Boy's hop if the monitor is actually
// in the state the schedule thinks it is. A sourced forcedown (g141/g262) can
// drop it underneath an open-loop table, after which the next "cams down"
// toggle raises instead -- and hands him the interval the phase was chosen to
// deny him. --sync makes the two monitor actions intents rather than presses.
const SYNC = process.argv.includes('--sync');
const rows = [];
for (let base = 5200; base <= 10000; base += 200) {
  let foxy = 0, bbIn = 0, chain = 0, survived = 0;
  const depth = [];
  const causes = {};
  for (let i = 0; i < N; i++) {
    const r = run({ cycles: 80, base, sync: SYNC,
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
  const phase = ((-base % 5000) + 5000) % 5000;
  rows.push({ base, phase, foxy, bbIn, chain, survived,
    median: depth[N >> 1], best: depth[N - 1],
    top: Object.entries(causes).sort((a, b) => b[1] - a[1])[0] });
}

console.log(`${N} nights per row. "phase" is where the 5 s movement interval`);
console.log('falls inside the cycle; the cams are down from 0 to about 1550 ms.\n');
console.log('base   phase   BB in office   foxy   chain   median   best   dominant death');
for (const r of rows) {
  const camsDown = r.phase < 1550 ? ' *' : '  ';
  console.log(
    `${String(r.base).padStart(5)}${camsDown} ${String(r.phase).padStart(5)}   ` +
    `${String(r.bbIn).padStart(10)}   ${String(r.foxy).padStart(4)}   ` +
    `${String(r.chain).padStart(5)}   ${r.median.toFixed(0).padStart(5)}s   ` +
    `${r.best.toFixed(0).padStart(4)}s   ${r.top ? r.top[0] + ' ' + r.top[1] : '-'}`);
}
console.log('\n* = the movement interval lands while the cams are down');
