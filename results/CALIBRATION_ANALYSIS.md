# calibration analysis

opus 4.6 only (sonnet/haiku pending credit fix). 13 images, 99 samples.

## the headline

confidence is **anti-correlated** with correctness on this task.

| outcome | high conf | medium conf | low conf |
|---|---|---|---|
| correct | 7 | 7 | 0 |
| wrong | 51 | 34 | 0 |

opus says "high" 58 times. it's right 7 of those (12%).
opus says "medium" 41 times. it's right 7 of those (17%).
opus never says "low" — across 99 vision-reading samples, the model never expresses doubt.

if the model were well-calibrated, "high confidence" predictions would be right at high rates. they're right at lower rates than medium. that's not random noise — that's confident wrongness as a default mode.

## deterministic wrong answers at T=1.0

6 of 13 images had this pattern: 8 samples, same wrong answer in all 8.

| image | gt | model said (all 8 samples) | confidence |
|---|---|---|---|
| clock_002.png | 04:06 | 07:07 | medium |
| clock_006.png | 05:21 | 07:22 | medium |
| clock_007.png | 07:31 | 07:37 | high |
| clock_009.jpg | 04:00 | 10:22 | medium |
| hygrometer_001.jpg | 75 | 78 (unit: "% rel.") | high |
| scale_002.jpg | 0 oz | 0 (unit: "lb") | high |

T=1.0 should make outputs vary. these don't. the model has a fixed internal read of each image and replays it.

note: clock_009 says 10:22 with medium confidence. the actual time on the wall-mounted clock is 4:00 (hour hand on 4, minute hand on 12). opus reads the same picture as 10:22, eight times, with medium confidence. minute hand and hour hand are clearly distinguishable from the photo. this isn't ambiguous parallax.

## near-deterministic cases

| image | unique readings across 8 samples |
|---|---|
| clock_001 | 2 |
| clock_003 | 6 |
| clock_004 | 2 |
| clock_005 | 4 |
| clock_008 | 5 |
| scale_001 | 1 (all correct) |
| speedometer_001 | 1 (all correct) |

even when there's some variance, it's small — usually 2-6 unique readings across 8 samples, not 8 unique. pass@k won't save us here. the model's distribution over readings is sharp.

## why this matters

if the goal of a vision RL env is to give the model a gradient signal, calibration failure is a feature, not a bug. but it changes the training strategy:

- pass@k inference-time tricks won't work (deterministic answers)
- confidence-weighted scoring won't work (high conf is anti-correlated with correctness)
- the model needs different reasoning, not more attempts
- training signal should be "you said high confidence and were wrong, penalty" rather than "try more times"

## limitations

- only one model, partial coverage
- "high" vs "medium" confidence label is self-reported by the model in the json output, not the model's actual logits. this is the model's surface-level admission of confidence, which may not match its internal distribution
- 99 samples is too small for fine-grained calibration curves
- 100% format compliance is unusual — model never breaks the json contract on this prompt

## tldr

opus says "high confidence" 58 times, is right 12% of those. it never says "low". confidence is anti-correlated with correctness. and at T=1.0, the model gives the same wrong answer 8 times in a row on 6 of 13 images. this is the failure pattern from the smoke test, holding on a larger N.
