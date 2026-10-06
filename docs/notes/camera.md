# Camera

## Functions

| Address | Name | Status | Notes |
|---|---|---|---|
| `0x7100A328B0` | `Camera::UpdateView` | wip | LookAt: forward = eye - target, right = cross(up, forward), builds `mWorld` then `mView` |
| `0x7100A32B50` | `Camera::UpdateProjection` | decompiled | Perspective path understood; orthographic branch (`mFlags` bit 0) still to do |
| `0x7100A32DB0` | `Camera::Set` | **matching** | Byte-identical with clang 5.0.1 / 6.0.x, `-O2 -g -mcpu=cortex-a57` |
| `0x7100A32EA0` | `Camera::SetDeferred` | nonmatching (95%) | Same stores as `Set`, then sets both dirty flags. One store is scheduled one slot later than the game |

The four functions sit next to each other in the binary. Compilers usually emit a class's methods together, so nearby functions are good candidates for more Camera methods.

## Struct

See `docs/reference/Camera.h`. Key offsets:

| Offset | Field | Meaning |
|---|---|---|
| `0x10` / `0x20` / `0x30` | `mEye` / `mTarget` / `mUp` | Where the camera is, what it looks at, which way is up |
| `0x40` | `mWorld` | Camera orientation, built by `UpdateView` |
| `0x80` | `mView` | World to camera |
| `0xC0` | `mProj` | Camera to screen. `0xC0` = horizontal scale, `0xD4` = vertical scale |
| `0x100` | `mViewProj` | `mView * mProj` |
| `0x148` / `0x14C` | `mFovY` / `mAspect` | The two values the 4:3 Vert+ patch adjusts |
| `0x160` / `0x161` | `mViewDirty` / `mProjDirty` | Rebuild flags |

## Findings

- **Vec4 copies are two 8-byte halves.** `Set` copies `zw` then `xy`; `SetDeferred` copies `xy` then `zw`. With the right compiler the order follows the source, so the two functions really were written differently: `Set` uses `operator=` (zw first) and `SetDeferred` copies the halves explicitly.
- **The matrix multiply is NEON**, one output row at a time (`vmulq_laneq_f32` then `vfmaq_laneq_f32` ×3). Ghidra shows it as `CONCAT44` soup.
- **`SQRT` + `NAN` + `sqrtf` in Ghidra** is the compiler's inlined square root (fast instruction plus an error-path library call). The source just said `sqrtf(x)`.
- **Compiler: LLVM 5.0.1 / 6.0.x with `-O2 -g -mcpu=cortex-a57`.** Tested 19 public builds from 3.8 to 12: only 3.9.1, 5.0.1 and 6.0.x byte-match `Set`, and only with `-g` (debug info changes LLVM 5/6's instruction scheduling). 5.0.1/6.0.x also give the best `SetDeferred`. NintendoSDK 6.5.0 is from mid-2018, when LLVM 6.0 was current.

## Exercise: SetDeferred

Done! Nat wrote it. With `Vec4::operator=` copying `zw` first (to match `Set`), `SetDeferred` needs its copies spelled out low half first: `mEye.xy = eye->xy; mEye.zw = eye->zw;` and so on. That reaches **95%**.

### Why it's stuck at 95%

After the last vector load (`ldr x8, [x3, #8]`) the CPU has to wait a few cycles before it can store `x8`. The scheduler fills that wait with the independent float stores. **The game fits five float stores in the gap; every public clang fits four**, so `mAspect` spills to after `mov w8, #0x101`.

Ruled out (about 8,600 builds, all landing at 95% or lower):

- **Copy type / aliasing:** float32x2_t halves, u64 halves, memcpy, vld1/vst1, per-float, temporaries, inlined helpers. All fields hang off the same `this` pointer at different offsets, so the compiler already knows they can't overlap; types don't change anything.
- **Debug-info perturbation:** locals, inlined helper functions, `-gline-tables-only`, `-gdwarf-2/4`.
- **Statement order:** ~3,000 random orderings of the 13 statements. Always exactly four floats in the gap.
- **Flags:** `-fno-strict-aliasing`, `-O3`, `-Os`, `-fPIC`, `-ffast-math`, `-fno-omit-frame-pointer`.
- **CPU models and scheduler options:** 13 `-mcpu` targets × 18 `-mllvm` scheduler options. Other models give 0, 3 or 4 floats in the gap, never 5.
- **Compiler versions:** all 19 public builds from 3.8 to 12. Every one gives four.

Conclusion: the "four" comes from the compiler's Cortex-A57 timing model, not the source. Nintendo's clang fork most likely has a slightly different model or scheduler tweak. Treat `SetDeferred` as **nonmatching (equivalent)**: same behavior, one instruction scheduled differently. If more functions turn up with the same one-slot slip after a load, that's further evidence for the fork theory.

## Next leads

- Finish `UpdateView`: find the second cross product (the true "up" axis) and where `mView` is written.
- `UpdateProjection`'s orthographic branch.
- Who calls `Set`? Each caller is a different camera in the game (battle, monastery, cutscenes).
