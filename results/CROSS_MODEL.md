# cross-model analysis

## status

opus 4.6 ran on 13 of 17 images (99 samples). sonnet 4.6 and haiku 4.5 hit a "credit balance too low" error before any samples landed. cross-model comparison is incomplete and i'll fill it in once credits are sorted. for now this doc is opus-only.

## opus 4.6

| metric | value |
|---|---|
| images scored | 13 |
| samples total | 99 |
| pass@1 | 23.1% (3/13) |
| pass@8 | 23.1% (3/13) |
| sample accuracy | 14.1% |
| format compliance | 100% |
| deterministic wrong | 6/13 images |

per type:
| type | n | pass@1 | pass@8 |
|---|---|---|---|
| analog_clock | 9 | 11.1% | 11.1% |
| scale | 2 | 50.0% | 50.0% |
| speedometer | 1 | 100% | 100% |
| hygrometer | 1 | 0% | 0% |

opus passes only when:
- needle sits exactly at 0 (speedometer)
- needle sits at a clean tick that matches a round number (scale_001: gt 85, model says 90, within 5% of 130 scale)
- (one clock at 8:45, partial credit)

opus fails on:
- 8/9 clocks
- the hygrometer at 75% (model says 78% which is within numeric tolerance but says unit "% rel." which my strict rubric rejects — note this is a scoring choice, not a model error)
- the postal scale at 0 oz (model says 0 lb — same kind of unit mismatch)

## clocks: where the failure lives

8 of 9 clocks failed at both pass@1 and pass@8. the one clock that got partial credit (clock_008, gt 8:45) had 3/8 samples right.

zero-variance clocks (same wrong answer in all 8 samples at T=1.0):
- clock_002: gt 04:06, model says 07:07 eight times
- clock_006: gt 05:21, model says 07:22 eight times
- clock_007: gt 07:31, model says 07:37 eight times
- clock_009: gt 04:00, model says 10:22 eight times

these are the most damning samples. T=1.0 should produce variance. opus produces none. it commits to one wrong answer and locks in.

clock_003 had 6 unique readings across 8 samples (gt 08:10, predictions ranged 07:51 to 07:52) — model knew the answer was near 8 but couldn't pin minutes.

## are clocks universally hard?

can't fully answer without sonnet/haiku data. the smoke test (also opus) hit 0/64 on clocks, this run hit 1/72. consistent. clockbench published 13.3% pass@1 for top model across 180 clocks. our slice agrees with their range.

sonnet/haiku will likely be worse, not better — smaller models tend to be more confused by spatial-reasoning tasks. but until i have data i won't claim that.

## are gauges with sub-tick precision universally hard?

the hygrometer needle sits between the 70 and 80 marks at the 75 position (5% tolerance allows 70-80). opus reads it as 78. numerically pass, unit fail. on the model-output side this looks like correct reading + wrong unit.

we have only one off-zero gauge in the public set (the tachometer at ~2200 rpm, which didn't get sampled this run because opus ran out of credits before reaching it). need more off-zero gauges to answer this properly. that's part of why personal photos matter — they'll skew off-zero by design.

## one model right, another wrong?

not enough data yet. table will be filled when sonnet+haiku land.

## next steps

1. retry sonnet + haiku once credits propagate (or with a fresh key)
2. add the missing 4 images to opus (speedometer_002, sphygmomanometer_001/002, tachometer_001)
3. expand the public set with off-zero gauges so this isn't 90% clocks
