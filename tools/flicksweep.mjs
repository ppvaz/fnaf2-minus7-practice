// What does the blind Golden Freddy flick actually buy?
//
// The mechanism is sourced: g336 spawns him only with the monitor up, g776
// makes a mask touch the only clear, g777 kills on a raise with him present
// and g778 kills on a hall flash. What is NOT sourced is the strategy the
// pilot wraps around it -- flicking the mask every single cycle because it
// cannot see whether he is there. A human just looks at the office.
//
// The flick is not free. It lands a mask-off animation immediately before the
// hall flash, and on the phone that is measurably what stops the flash
// lighting: graded over real runs, 3-5 visible beams out of about 12
// scheduled. This prices both sides in the simulator.
//
//   node tools/flicksweep.mjs [nights]
import { run } from './pilottest.mjs';
import * as C from '../src/config.js';

const N = +(process.argv[2] || 200);
const V = [
  ['flick, no BB response', { }],
  ['no flick, no BB response', { noFlick: true }],
  ['flick + BB response/4', { periodic: 4 }],
  ['no flick + BB response/4', { noFlick: true, periodic: 4 }],
];

console.log(`${N} nights per row.\n`);
console.log('variant                     golden   foxy   BB in office   median   best');
for (const [name, o] of V) {
  let gf = 0, foxy = 0, bbIn = 0;
  const depth = [];
  for (let i = 0; i < N; i++) {
    const r = run(Object.assign({ cycles: 80, sync: true }, o,
      { sim: { seed: (i * 2246822519) >>> 0 } }));
    const s = r.sim;
    depth.push(s.frame / C.FPS);
    if (s.won) continue;
    if (s.death.reason.startsWith('golden')) gf++;
    if (s.death.reason === 'foxy') foxy++;
    if (s.bb.inside) bbIn++;
  }
  depth.sort((a, b) => a - b);
  console.log(
    `${name.padEnd(26)} ${String(gf).padStart(6)}   ${String(foxy).padStart(4)}   ` +
    `${String(bbIn).padStart(12)}   ${depth[N >> 1].toFixed(0).padStart(5)}s   ` +
    `${depth[N - 1].toFixed(0).padStart(4)}s`);
}
