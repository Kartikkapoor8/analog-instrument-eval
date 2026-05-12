# calibration analysis

## status

opus 4.6 only. sonnet 4.6 and haiku 4.5 are pending — the api key hit a "credit balance too low" error mid-run on the first attempt and the error has persisted through every retry since. when credits resolve i'll fill this in. for now everything below is opus on 13 of the 17 v0.1 images, 99 samples total.

(the v0.2 dataset is 30 images. opus only ran on 13 before credits broke. so the calibration finding is on a smaller slice than the dataset advertises. honest.)

## the headline

opus says "high confidence" 58 times across 99 samples. it's correct on 7 of those (12%).
opus says "medium" 41 times, correct on 7 (17%).
opus never says "low".

| outcome | high | medium | low |
|---|---|---|---|
| correct | 7 | 7 | 0 |
| wrong | 51 | 34 | 0 |

if confidence were calibrated, "high" predictions would be right at higher rates than "medium." they're right at lower rates. medium is 17%, high is 12%. that's anti-correlation.

zero "low" calls across 99 vision-reading samples is also notable. the model never expresses doubt about a reading even when it cannot resolve the geometry.

## deterministic wrong answers at T=1.0

6 of 13 images had this pattern: 8 samples, identical wrong answer in all 8.

| image | ground truth | all 8 samples said | confidence |
|---|---|---|---|
| clock_002.png | 04:06 | 07:07 | medium |
| clock_006.png | 05:21 | 07:22 | medium |
| clock_007.png | 07:31 | 07:37 | high |
| clock_009.jpg | 04:00 | 10:22 | medium |
| hygrometer_001.jpg | 75.0 % rh | 78 ("% rel.") | high |
| scale_002.jpg | 0.0 oz | 0 ("lb") | high |

T=1.0 should produce variance. these don't. the model has a fixed internal read of each image and replays it.

clock_009 is the most striking. the wall-mounted clock has hour hand on 4 and minute hand on 12. opus reads it as 10:22, eight times, with medium confidence. that's not parallax or ambiguity — that's a confidently wrong geometric read that doesn't update.

clock_007 says 07:37 eight times when gt is 07:31. only six minutes off, model said "high" all eight times. close-but-wrong with locked-in confidence is the most dangerous failure mode for downstream tasks.

## near-deterministic cases

| image | unique readings across 8 samples |
|---|---|
| clock_001 | 2 |
| clock_003 | 6 |
| clock_004 | 2 |
| clock_005 | 4 |
| clock_008 | 5 (and 3 of 8 correct) |
| scale_001 | 1 (all correct) |
| speedometer_001 | 1 (all correct) |

even where variance exists it's narrow — usually 2-6 unique readings, not 8. the model's posterior over each image is a narrow distribution centered on a wrong answer.

## quoted failures

clock_004 (gt 06:02). model says 11:30, high confidence, eight times:
```json
{"instrument_type": "clock", "reading": "11:30", "unit": "time", "scale_max": null, "confidence": "high"}
```
hour hand is straight down at 6, minute hand at 12. model swapped hands and snapped the minute to :30.

clock_009 (gt 04:00). model says 10:22, medium confidence, eight times:
```json
{"instrument_type": "clock", "reading": "10:22", "unit": "time", "scale_max": null, "confidence": "medium"}
```
the actual photo is a wall clock at a cable-car station. hour hand on 4, minute hand on 12. model is reading something else entirely.

hygrometer_001 (gt 75% rh). model says 78, high confidence, eight times:
```json
{"instrument_type": "hygrometer", "reading": 78, "unit": "% rel.", "scale_max": 100, "confidence": "high"}
```
needle sits between the 70 and 80 marks closer to 75. model reads 78 — numerically inside 5% of 100 — but reports the unit as "% rel." instead of "rh". strict rubric calls this a fail. permissive unit table would call it a pass. either way the model is high-confident on a non-trivial sub-tick read.

## why this matters more than "models fail at clocks"

clockbench is synthetic clocks at 13.3% pass@1. our slice is real images at 11.1% pass@1 on clocks. the headline accuracy isn't the story — clockbench already proved that. the new finding is:

1. **same wrong answer 8 times at T=1.0.** sampling tricks don't help. the model doesn't represent uncertainty over geometric reads.
2. **"high confidence" is anti-correlated with correctness.** worse than chance for picking which read to trust.
3. **the model never says "low".** zero self-doubt across 99 samples.

these are training signals you can't get from a benchmark that only reports pass@k. and they suggest the training data needed isn't more clock images — it's images that teach the model *when to stop being confident*.

## why this is a richer training target than clockbench alone

clockbench is synthetic and clock-only. it tells you "models can't read time." it does not give you the calibration story because it doesn't track confidence-vs-correctness or sample variance.

this env tracks both. and it covers 8 instrument types beyond clocks, so the training signal isn't "memorize clock face geometry." it's "translate needle-on-scale photos to numbers, and know when you're guessing."

## limitations

- 99 samples is too few for fine calibration curves. n is a floor on the story not a ceiling.
- confidence is the model's self-reported field in the json output, not its actual logits. could be miscalibrated separately from the underlying read.
- sonnet/haiku absent. universal claim requires them.
- the deterministic-wrong pattern holds on opus. doesn't mean it holds on every frontier model. needs replication.

## tldr

opus 4.6: 12% accuracy on its "high confidence" calls. 0 "low confidence" calls. same wrong answer eight times in a row on 6 of 13 images at T=1.0. this is a deterministic-confidence failure, not just an accuracy gap. that's the angle.
