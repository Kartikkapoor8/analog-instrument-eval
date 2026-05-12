# analog_instrument

verifiers env for analog instrument reading from photos. single-turn, deterministic rubric, real images.

## install

```
prime env install kartikkapoor/analog_instrument
```

## what the model sees

- system prompt instructing strict json output
- one image of an analog instrument
- "Read this instrument."

expected output:
```json
{
  "instrument_type": "<type>",
  "reading": <number or "HH:MM">,
  "unit": "<unit>",
  "scale_max": <number or null>,
  "confidence": "<high|medium|low>"
}
```

## scoring

- instrument type must canonicalize to the gt type (alias table built in)
- unit must match (alias table covers psi/bar, kg/lb/oz, mph/kph, °c/°f, etc)
- clocks: pass if predicted hh:mm within 1 minute of gt (12-hour mod)
- numeric: pass if predicted reading within 5% of `scale_max`

tracked-only metrics: format compliance, confidence_correct, confidence_wrong (for calibration analysis).

## known failure modes (from v0.1 opus run)

- clocks: 1 of 9 passed. zero variance at T=1.0 — model commits to one wrong answer
- "snap to round number" on off-tick gauges
- unit mismatch when scale has multiple units printed (e.g. postal scale lb vs oz)
- "high confidence" reported when wrong more often than when right

## dataset

17 verified public images (clockbench public sample + wikimedia commons). personal photos folder exists but empty in v0.1 — user is shooting workplace instruments tomorrow.

see `data/manifest.json` for the master index. each image has a matching `data/ground_truth/<name>.json` with verification reasoning.

## tests

```
python -m pytest test_rubric.py -v
```

29 tests covering type canonicalization, unit aliases, clock tolerance, numeric tolerance, malformed json, parenthetical type names, etc.
