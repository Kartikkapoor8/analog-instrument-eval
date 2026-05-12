# analog instrument reading: a vision capability gap

## tldr

frontier vision models can't read analog instruments at human-trivial accuracy, and they fail with deterministic confidence. opus 4.6 hits 23.1% pass@1 on 13 of 17 v0.1 images (99 samples). at T=1.0, opus gives the same wrong answer eight times in a row on 6 of those 13. it says "high confidence" 58 times and is correct on 7. confidence is anti-correlated with correctness.

## the intent through-line

this is the same question meeting_intent asked: do models miss things humans read trivially? meeting_intent tested dialogue (do models filter parking-lot commitments from real ones?). that signal got disproved by ablation — the rubric canonicalization was carrying most of the lift, not model capability.

analog instrument reading is the same question on a different sensory channel: vision instead of dialogue. it's cleaner because numbers compare to numbers — no canonicalization tricks possible. the rubric is bulletproof: needle position within 5% of scale, time within 1 minute. either you got it or you didn't.

## the failure

clockbench published 89.1% human accuracy vs 13.3% top-model accuracy on synthetic clocks. that's a known frontier gap. this env extends to general analog instruments: clocks, pressure gauges, thermometers, scales, voltmeters, tachometers, sphygmomanometers. all human-trivial. all model-hard.

different from meeting_intent in two ways:
1. **pixel-level geometric reasoning.** prompting can't fix it. the model needs to map needle angles to numbers. that's a perception problem, not a reasoning problem.
2. **no canonicalization issue.** the rubric compares a number to a number. there's no edge case where the model "kinda got it" because of how the metric handles strings.

## methodology

- **dataset**: 30 verified public images
  - 16 analog clocks (8 clockbench synthetic + 8 real wall/wristwatch photos from wikimedia)
  - 2 pressure gauges (off-zero)
  - 2 tachometers
  - 3 speedometers
  - 2 sphygmomanometers
  - 2 scales (1 bathroom at 85kg, 1 postal at 0oz)
  - 2 barometers
  - 1 hygrometer at 75% rh
  - personal photos folder exists but is empty (i don't have workplace access)
- **models intended**: claude opus 4.6, sonnet 4.6, haiku 4.5
- **models actually run**: opus 4.6 on 13 of 17 v0.1 images (99 samples). sonnet/haiku pending — api key hit "credit balance too low" mid-run and the error has persisted. v0.2 expansion to 30 images is not yet evaluated. transparent about this below.
- **sampling**: n=8 per image at T=1.0
- **scoring**: deterministic. unit must canonicalize and match. instrument type must canonicalize and match. clock pass if within 1 minute. numeric pass if within 5% of scale_max.

## results

opus 4.6 (partial — 13 of 17 v0.1 images, 99 samples):

| metric | value |
|---|---|
| pass@1 | 23.1% (3/13) |
| pass@8 | 23.1% (3/13) |
| sample accuracy | 14.1% (14/99) |
| format compliance | 100% |
| deterministic wrong | 6/13 images |

per type (opus):

| type | n | pass@1 | pass@8 |
|---|---|---|---|
| analog_clock | 9 | 11.1% | 11.1% |
| scale | 2 | 50% | 50% |
| speedometer | 1 | 100% | 100% |
| hygrometer | 1 | 0% | 0% |

sonnet/haiku: pending credit fix.

## the unique calibration finding

this is the part you can't get from clockbench.

opus says "high" 58 times across 99 samples. it's correct on 7 (12%).
opus says "medium" 41 times. correct on 7 (17%).
opus says "low" 0 times.

confidence is **anti-correlated** with correctness. high-confidence reads are slightly less reliable than medium ones.

at T=1.0, opus gives the exact same wrong answer 8 times in a row on 6 of 13 images:

- clock_002 (gt 04:06): "07:07" × 8
- clock_006 (gt 05:21): "07:22" × 8
- clock_007 (gt 07:31): "07:37" × 8 (high confidence)
- clock_009 (gt 04:00): "10:22" × 8
- hygrometer_001 (gt 75% rh): 78 ("% rel.") × 8 (high confidence)
- scale_002 (gt 0 oz): 0 ("lb") × 8 (high confidence)

sampling tricks won't help. pass@k won't help. the model's distribution over each image is sharp and wrong, not wide-and-unsure. that's a different failure mode than what most evals measure.

this matters for training data design. if confidence is uncorrelated, the training signal isn't "more attempts" or "better prompting." it's "penalize confident wrongness." that requires a dataset with verified ground truths, which is what this env builds.

see CALIBRATION_ANALYSIS.md for the full breakdown.

## commercial frame

type 1 data: real photos with verified provenance. labeling requires a 17-year-old who can read a gauge. doesn't require an expert. doesn't require an LLM (frontier models can't self-label this task).

phase 1 (this version): 30 public verified images. proves the failure mode. validates the rubric. shows the calibration finding.

phase 2 (next): 500 student-sourced photos across industrial, healthcare, automotive, lab, home contexts. $1000 in bounties, 6 weeks. see SOURCING_METHODOLOGY.md.

buyers:
- vision-training data companies (scale ai, surge, etc) — they sell exactly this kind of labeled real-world data
- physical AI labs working on robotics-with-cameras (boston dynamics-adjacent groups have flagged analog dashboard reading as an unsolved skill)
- telehealth (BP cuffs, glucose meters, peak flow meters all use analog dials in legacy devices)
- industrial monitoring saas

## hillclimbability

23.1% pass@1 sits inside the 10-40% sweet spot for an RL env. not so hard there's no signal, not so easy the env is solved.

what training data closes the gap:
- needle-on-scale photos with verified geometric ground truth
- multi-scale instruments (force the model to pick the right scale before reading)
- sub-tick precision examples (needle between marks)
- confidence calibration: pairs where the model should say "high" and pairs where it should say "low"

per instrument the gap is uneven. scales: 50%, speedometers: 100% (zero-readings), clocks: 11%. the biggest gain comes from clocks at sub-tick precision and gauges with off-zero needles.

## limitations

honest list:

- **phase 1 dataset is public-only.** i don't have personal access to workplace instruments (yet — see SOURCING_METHODOLOGY for how to get there). no industrial/healthcare/automotive shots beyond what wikimedia has.
- **partial cross-model.** sonnet and haiku didn't run. claim of "frontier failure" is opus-only. honest.
- **n is 30 v0.1 images.** commercial-grade is 500+. this is the proof-of-failure, not the deployable dataset.
- **opus eval only covered 13/17 of v0.1.** the v0.2 expansion (30 images including 13 new) is not yet evaluated. when credits come back i'll run all three models on all 30.
- **the calibration finding needs replication.** opus on 99 samples is suggestive. universal frontier claim requires sonnet, haiku, gpt-5.5, gemini 3, etc.
- **clockbench's public set is synthetic.** 8 of the 9 clocks opus saw are synthetic. 1 real clock (clock_009) opus got wrong. that's not enough real-clock data to be confident about the synthetic-vs-real gap.
- **ground truth for some images is "my own read at high confidence."** for clocks and well-labeled gauges this is fine. for ambiguous edge cases i skipped, so the public set skews toward easy reads.

## status

- v0.2 on prime intellect hub: `kartikkapoor/analog_instrument`
- 30 verified public images
- 29/29 rubric tests passing
- opus calibration finding documented
- sourcing methodology written
- pending: sonnet/haiku runs (credit issue), personal photos (no access yet), 500-image scale (phase 2)

ready for direction decision.
