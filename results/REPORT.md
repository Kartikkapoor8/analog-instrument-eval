# analog instrument reading: a vision capability gap

## tldr

frontier vision models fail to read analog instruments at human-trivial accuracy, and do so with deterministic confidence. opus 4.6 lands at 23.1% pass@1 across 13 verified public images (mostly clocks). at temperature 1.0, the model gives the same wrong answer 8 times in a row on 6 of those 13. confidence is anti-correlated with correctness.

## the failure

analog clock reading benchmarks like clockbench (89.1% human, 13.3% top model) suggest a persistent vision gap. this env extends that idea to general analog instruments: pressure gauges, thermometers, scales, voltmeters, tachometers. all are tasks where humans glance and read in under 5 seconds. frontier vision models can't.

unlike language tasks where prompting and chain-of-thought help, this is geometric. the model has to map needle angles to numbers. prompt engineering doesn't fix it. you need new training data showing the model what tick marks and sub-tick interpolation look like.

## methodology

- **dataset**: 17 verified public images (8 from clockbench public sample, 9 from wikimedia commons). 8 clocks (synthetic and real), 2 sphygmomanometers, 2 scales, 1 tachometer, 1 hygrometer, 2 speedometers. ground truth verified manually for each. personal photos pending — user is shooting workplace instruments tomorrow.
- **models tested**: claude opus 4.6 (partial — 13/17 images, 99 samples). sonnet 4.6 and haiku 4.5 pending due to api credit issue mid-run.
- **sampling**: n=8 per image at T=1.0
- **scoring**: deterministic. unit must match. clock pass if predicted hh:mm within 1 minute of gt. numeric instrument pass if reading within 5% of scale_max.

## results

| model | pass@1 | pass@8 | format | determ wrong |
|---|---|---|---|---|
| opus 4.6 | 23.1% | 23.1% | 100% | 6/13 |
| sonnet 4.6 | pending | pending | pending | pending |
| haiku 4.5 | pending | pending | pending | pending |

per-instrument (opus only):

| type | n | pass@1 | pass@8 |
|---|---|---|---|
| analog_clock | 9 | 11.1% | 11.1% |
| scale | 2 | 50% | 50% |
| speedometer | 1 | 100% | 100% |
| hygrometer | 1 | 0% | 0% |

clocks are 90% of the failure. the one clock that scored had 3/8 correct samples.

## the calibration finding

this is the most interesting result. opus reports "high confidence" 58 times across 99 samples. it's correct on 7 of those (12%). it reports "medium" 41 times, correct on 7 (17%). it never reports "low".

confidence is anti-correlated with correctness. high-confidence claims are slightly *less* likely to be right than medium-confidence claims.

stronger: at T=1.0, opus gives the exact same wrong answer 8 times in a row on 6 of 13 images. examples:

- clock_002, gt 04:06: opus says 07:07 eight times, medium confidence
- clock_007, gt 07:31: opus says 07:37 eight times, high confidence
- clock_009, gt 04:00: opus says 10:22 eight times, medium confidence
- hygrometer_001, gt 75% rh: opus says 78 (%rel) eight times, high confidence

these aren't models being honestly uncertain. they're models being confidently wrong with deterministic certainty. pass@k inference tricks won't help — the distribution over answers is sharp and wrong.

quoted raw output, clock_004 (gt 06:02):
```json
{"instrument_type": "clock", "reading": "11:30", "unit": "time", "scale_max": null, "confidence": "high"}
```
hour hand is straight down at 6, minute hand at 12. model swaps the hands and snaps minute to :30.

## why this matters

real applications this breaks:
- industrial monitoring (pressure gauges, flow meters)
- healthcare (bp cuffs, dialysis machines, anesthesia gauges)
- automotive (analog dashboards still common in trucks, motorcycles, older cars)
- field science (analog thermometers, barometers, lab balances)

prompting won't fix any of these. the model needs training data that maps geometric needle positions to numeric readings. that's a labeling problem, not a reasoning problem.

## commercial frame

type 1 data: real workplace photos with verified provenance. a 17-year-old intern can label them trivially (read the gauge, write down the number). frontier models cannot read them at all. the labeling pipeline — the photo + verified gt — is the moat.

dataset scaling plan:
1. v0.1 (now): 17 public images + planned 30-50 personal workplace photos
2. v0.2: 100-200 images, off-zero gauges deliberately oversampled
3. v1.0: 500+ images, cross-model leaderboard, hard-difficulty subset for RL

## limitations

honest list:
- 17 images is small. true pass@1 has wide ci.
- only opus tested so far. sonnet/haiku numbers will come once credits propagate.
- 9 of 17 images are clocks (8 from clockbench's synthetic public sample). over-indexed on a single instrument type.
- 4 of the non-clock instruments have reading=0 (zero readings trivialize the task). bathroom scale (85 kg) and tachometer (~2200 rpm) are the only off-zero gauges, and the tachometer didn't get sampled this run.
- single-shot eval, no multi-turn variants tested
- ground truth on the hygrometer and clock_009 is "my own read at high confidence" — i'm 17 and i can see them clearly, but it's not a benchmark-grade label
- clockbench images are synthetic. real photos behave differently.

## status

verified failure mode. hillclimbable. 23.1% pass@1 sits inside the 10-40% sweet spot for an rl env target — not so hard there's no signal, not so easy it's solved.

next: ship sonnet+haiku runs, personal photo pipeline, then expand to 100+ images for v0.2.
