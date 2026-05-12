# analog-instrument-eval

RL environment for reading analog instruments from photos. Deterministic rubric, verified public dataset, cross-model eval.

## install

```
prime env install kartikkapoor/analog_instrument
```

Hub: https://app.primeintellect.ai/dashboard/environments/kartikkapoor/analog_instrument

## what this is

Frontier vision models can't read analog clocks, gauges, scales, or thermometers at human-trivial accuracy. This env quantifies that gap with a clean rubric (no LLM judge), 30 verified public images, and a calibration story you can't get from clockbench alone. Through-line from meeting_intent: same question (do models miss things humans read trivially?), different sensory channel (vision instead of dialogue).

## headline finding

opus 4.6 sits at 23.1% pass@1 on the public set, 11.1% on clocks alone. on 6 of 13 images, opus gives the same wrong answer 8 times in a row at T=1.0. when opus says "high confidence" it's correct 12% of the time. it never says "low."

Full analysis: [results/REPORT.md](results/REPORT.md)
Calibration deep-dive: [results/CALIBRATION_ANALYSIS.md](results/CALIBRATION_ANALYSIS.md)
Sourcing plan for scale: [results/SOURCING_METHODOLOGY.md](results/SOURCING_METHODOLOGY.md)

## structure

```
analog-instrument-eval/
├── environments/analog_instrument/    # the verifiers env
│   ├── analog_instrument.py           # env, rubric, scoring
│   ├── test_rubric.py                 # 29 tests
│   └── data/
│       ├── images/public/             # 30 verified public photos
│       ├── images/personal/           # empty in v0.1, placeholder for workplace shots
│       ├── ground_truth/              # one json per image
│       └── manifest.json
├── scripts/
│   ├── run_eval.py                    # cross-model eval runner
│   ├── build_dataset.py               # candidate fetcher
│   ├── fetch_v02.py                   # v0.2 wikimedia category fetch
│   └── rebuild_manifest.py
└── results/
    ├── REPORT.md
    ├── CALIBRATION_ANALYSIS.md
    ├── SOURCING_METHODOLOGY.md
    ├── CROSS_MODEL.md
    ├── eval_full.json
    └── raw_samples_opus.json
```

## quick numbers

- 30 verified public images (16 clocks, 14 gauges/scales/etc)
- 29/29 rubric tests passing
- opus 4.6 ran on 17 of those (v0.1 subset), 99 samples
- sonnet 4.6 + haiku 4.5 pending (API credit issue mid-run)
- v0.2 on Prime Intellect Hub

## status

v0.2 shipped. ready for direction decision. next is sonnet/haiku runs when credits resolve, then phase 2 sourcing (500 student-sourced workplace photos — see SOURCING_METHODOLOGY.md).

## license

MIT
