// What does Night 6 ask of the pilot, compared with 10/20?
//
// Beating 6th Night is the unlock for Custom Night, which is where 10/20
// lives, so it is the first thing the device pilot has to actually do rather
// than approximate. Most of the sourced model is night-indexed -- the value25
// entry streak is 20 - 2*night seconds, Toy Bonnie's cooldown is
// 1000 - 100*night frames, the mask fuse runs 100 down to 45, Foxy's exposure
// threshold is 100*night, and the battery is 3000 frames from night 5 on -- so
// night 6 is a materially easier problem, not the same one shifted.
//
//   node tools/nightsweep.mjs [nights]
import { run } from './pilottest.mjs';
import * as C from '../src/config.js';

const N = +(process.argv[2] || 200);
const V = [
  ['blind (as shipped)', {}],
  ['blind + sync', { sync: true }],
  ['BB response/4 + sync', { periodic: 4, sync: true }],
  ['vent check + sync', { vent: true, sync: true }],
];

for (const night of [6, 7]) {
  console.log(`\n=== night ${night} ${night === 7 ? '(10/20)' : '(6th Night)'} ` +
    `-- entry streak ${(C.entryStreakFrames(night) / C.FPS).toFixed(0)}s, ` +
    `mask fuse ${C.maskGraceFrames(night)}f, ` +
    `Foxy exposure ${C.foxyExposureFrames(night)}f ===`);
  console.log('variant                   survived   foxy   BB in office   median   best');
  for (const [name, o] of V) {
    let foxy = 0, bbIn = 0, survived = 0;
    const depth = [];
    for (let i = 0; i < N; i++) {
      const r = run(Object.assign({ cycles: 90 }, o,
        { sim: { seed: (i * 2246822519) >>> 0, night } }));
      const s = r.sim;
      depth.push(s.frame / C.FPS);
      if (s.won) { survived++; continue; }
      if (s.death.reason === 'foxy') foxy++;
      if (s.bb.inside) bbIn++;
    }
    depth.sort((a, b) => a - b);
    console.log(
      `${name.padEnd(24)} ${String(survived).padStart(6)}/${N}   ` +
      `${String(foxy).padStart(4)}   ${String(bbIn).padStart(12)}   ` +
      `${depth[N >> 1].toFixed(0).padStart(5)}s   ${depth[N - 1].toFixed(0).padStart(4)}s`);
  }
}
