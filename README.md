# analog-instrument-eval

rl environment for analog instrument reading. verifies frontier vision capability gap with deterministic scoring.

## quick start

```
prime env install kartikkapoor/analog_instrument
```

## what's here

- 17 verified instrument images (clocks, gauges, scales, hygrometer, tachometer, sphygmomanometer, speedometers)
- deterministic rubric (no llm judge)
- single-turn verifiers env
- cross-model eval scaffold (opus 4.6, sonnet 4.6, haiku 4.5)
- calibration analysis

## headline finding

opus 4.6 lands at **23.1% pass@1** on the public set. at temperature 1.0, opus gives the same wrong answer 8 times in a row on 6 of 13 images. it says "high confidence" 58 times across 99 samples and is correct on only 7 of those. confidence is anti-correlated with correctness.

sonnet 4.6 and haiku 4.5 numbers pending — first run hit an api credit limit. see [results/CROSS_MODEL.md](results/CROSS_MODEL.md) and [results/REPORT.md](results/REPORT.md) for full analysis.

## pivot context

built after meeting_intent thesis was disproved by ablation (rubric canonicalization was carrying the signal, not model capability). this env addresses that gap: clean numeric scoring, verified human-trivial / model-hard task, hillclimbable.

smoke test (in another repo, see meeting-intent-eval branch `analog_instrument_smoke_test`) verified 28.6% pass@1 across 14 images. this env scales that with a real verifiers harness.

## structure

```
analog-instrument-eval/
├── environments/
│   └── analog_instrument/
│       ├── analog_instrument.py   # verifiers env + rubric
│       ├── test_rubric.py         # 29 tests, all passing
│       └── data/
│           ├── images/public/     # 17 verified public photos
│           ├── images/personal/   # placeholder for user's workplace photos
│           ├── ground_truth/      # one json per image
│           └── manifest.json
├── scripts/
│   ├── run_eval.py                # cross-model eval runner
│   ├── build_dataset.py           # wikimedia commons candidate fetcher
│   └── rebuild_manifest.py        # regenerate manifest from ground_truth/
└── results/
    ├── eval_full.json
    ├── raw_samples_opus.json
    ├── CROSS_MODEL.md
    ├── CALIBRATION_ANALYSIS.md
    └── REPORT.md
```

## rubric

```python
def score_reading(predicted, ground_truth):
    if predicted["instrument_type"] != ground_truth["instrument_type"]: return 0.0
    if predicted["unit"] != ground_truth["unit"]: return 0.0
    if instrument is clock:
        return 1.0 if predicted_time within 1 minute of gt else 0.0
    tolerance = 0.05 * ground_truth["scale_max"]
    return 1.0 if |predicted - gt| <= tolerance else 0.0
```

binary per item. unit and instrument type canonicalized via alias tables (`mph` = `miles per hour`, `analog_clock` = `clock` = `wristwatch`, etc).

## current dataset breakdown

- 9 analog clocks (8 clockbench synthetic public + 1 real wall clock)
- 2 sphygmomanometers (0 mmhg, cuff at rest)
- 2 scales (1 bathroom at 85 kg, 1 postal at 0 oz)
- 2 speedometers (parked vehicles at 0)
- 1 tachometer (motorcycle dashboard ~2200 rpm)
- 1 hygrometer (75% rh)

over-indexed on clocks and zero-readings right now. v0.2 will fix that with personal photos and more off-zero gauges.

## next

- 30-50 personal workplace photos (user shoots tomorrow, env auto-picks them up from `data/images/personal/`)
- complete sonnet 4.6 + haiku 4.5 runs
- v0.2 with 100+ images, off-zero gauge oversampling
- v1.0 scaling toward 500+ images for commercial-grade dataset

this is v0.1. more data is the moat.

## license

mit
