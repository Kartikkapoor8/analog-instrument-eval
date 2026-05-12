"""tests for analog_instrument rubric. run with: python -m pytest test_rubric.py -v"""
import json
import sys
from pathlib import Path

import pytest

# load analog_instrument.py directly (bypass __init__.py shadowing)
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "analog_instrument_mod",
    Path(__file__).parent / "analog_instrument.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
parse_completion = _mod.parse_completion
score_reading = _mod.score_reading
score_clock = _mod.score_clock
score_numeric = _mod.score_numeric
normalize_type = _mod.normalize_type
normalize_unit = _mod.normalize_unit
units_match = _mod.units_match


# ---------- normalization tests ----------

def test_normalize_type_canonical():
    assert normalize_type("analog_clock") == "analog_clock"

def test_normalize_type_alias():
    assert normalize_type("clock") == "analog_clock"
    assert normalize_type("WALL CLOCK") == "analog_clock"
    assert normalize_type("Wristwatch") == "analog_clock"

def test_normalize_type_parenthetical():
    # smoke test: model returned "sphygmomanometer (blood pressure gauge)"
    assert normalize_type("sphygmomanometer (blood pressure gauge)") == "sphygmomanometer"

def test_normalize_type_unknown():
    assert normalize_type("toaster") == "unknown"
    assert normalize_type(None) == "unknown"

def test_normalize_unit_aliases():
    assert normalize_unit("MPH") == "mph"
    assert normalize_unit("miles per hour") == "mph"
    assert normalize_unit("kg") == "kg"
    assert normalize_unit("Kilograms") == "kg"

def test_units_match_time_passthrough():
    assert units_match("anything", "time") is True

def test_units_match_strict():
    assert units_match("psi", "psi") is True
    assert units_match("psi", "bar") is False


# ---------- clock tests ----------

def test_clock_exact_match():
    assert score_clock("12:25", "12:25") == 1.0

def test_clock_within_1_min():
    assert score_clock("12:26", "12:25") == 1.0
    assert score_clock("12:24", "12:25") == 1.0

def test_clock_off_by_2_min_fails():
    assert score_clock("12:27", "12:25") == 0.0

def test_clock_12_hour_equivalence():
    # 12:25 PM should match 12:25 stored as "00:25" form too
    assert score_clock("00:25", "12:25") == 1.0

def test_clock_alt_readings():
    # ground truth from clockbench has ranges like [1:04, 1:05]
    assert score_clock("01:05", "01:04", alts=["01:05"]) == 1.0
    assert score_clock("01:06", "01:04", alts=["01:05"]) == 1.0
    assert score_clock("01:07", "01:04", alts=["01:05"]) == 0.0

def test_clock_unparseable():
    assert score_clock("noon", "12:00") == 0.0
    assert score_clock(None, "12:00") == 0.0


# ---------- numeric tests ----------

def test_numeric_exact_match():
    assert score_numeric(50.0, 50.0, 100.0) == 1.0

def test_numeric_within_5pct():
    # tolerance is 5.0
    assert score_numeric(54.9, 50.0, 100.0) == 1.0
    assert score_numeric(45.1, 50.0, 100.0) == 1.0

def test_numeric_outside_5pct():
    assert score_numeric(56.0, 50.0, 100.0) == 0.0

def test_numeric_string_parse():
    assert score_numeric("50 psi", 50.0, 100.0) == 1.0

def test_numeric_non_numeric_fails():
    assert score_numeric("hot", 50.0, 100.0) == 0.0


# ---------- full score_reading tests ----------

def _gt_numeric(itype, reading, unit, scale_max):
    return {"instrument_type": itype, "reading": reading, "unit": unit, "scale_max": scale_max}

def test_score_reading_full_match():
    gt = _gt_numeric("pressure_gauge", 50.0, "psi", 100.0)
    pred = {"instrument_type": "pressure_gauge", "reading": 50, "unit": "psi", "scale_max": 100, "confidence": "high"}
    assert score_reading(pred, gt) == 1.0

def test_score_reading_wrong_unit():
    gt = _gt_numeric("pressure_gauge", 50.0, "psi", 100.0)
    pred = {"instrument_type": "pressure_gauge", "reading": 50, "unit": "bar", "scale_max": 100, "confidence": "high"}
    assert score_reading(pred, gt) == 0.0

def test_score_reading_wrong_type():
    gt = _gt_numeric("pressure_gauge", 50.0, "psi", 100.0)
    pred = {"instrument_type": "thermometer", "reading": 50, "unit": "psi", "scale_max": 100, "confidence": "high"}
    assert score_reading(pred, gt) == 0.0

def test_score_reading_outside_tolerance():
    gt = _gt_numeric("tachometer", 2200.0, "rpm", 14000.0)
    # tolerance = 700, so 1000 is out, 1500 is in
    pred_bad = {"instrument_type": "tachometer", "reading": 1000, "unit": "RPM", "scale_max": 14000, "confidence": "high"}
    pred_ok = {"instrument_type": "tachometer", "reading": 1500, "unit": "rpm", "scale_max": 14000, "confidence": "high"}
    assert score_reading(pred_bad, gt) == 0.0
    assert score_reading(pred_ok, gt) == 1.0

def test_score_reading_clock_pass():
    gt = {"instrument_type": "analog_clock", "reading": "12:25", "unit": "time", "scale_max": None}
    pred = {"instrument_type": "clock", "reading": "12:26", "unit": "time", "scale_max": None, "confidence": "high"}
    assert score_reading(pred, gt) == 1.0

def test_score_reading_clock_fail():
    gt = {"instrument_type": "analog_clock", "reading": "12:25", "unit": "time", "scale_max": None}
    pred = {"instrument_type": "clock", "reading": "11:27", "unit": "time", "scale_max": None, "confidence": "high"}
    assert score_reading(pred, gt) == 0.0

def test_score_reading_none_input():
    gt = {"instrument_type": "analog_clock", "reading": "12:25", "unit": "time"}
    assert score_reading(None, gt) == 0.0


# ---------- parse_completion tests ----------

def test_parse_clean_json():
    out = parse_completion('{"instrument_type": "clock", "reading": "12:25"}')
    assert out == {"instrument_type": "clock", "reading": "12:25"}

def test_parse_code_fence():
    raw = '```json\n{"instrument_type": "clock", "reading": "12:25"}\n```'
    out = parse_completion(raw)
    assert out["reading"] == "12:25"

def test_parse_with_prose():
    raw = 'Sure! Here is the reading:\n{"instrument_type": "clock", "reading": "12:25"}'
    out = parse_completion(raw)
    assert out["reading"] == "12:25"

def test_parse_malformed():
    assert parse_completion("not json at all") is None
    assert parse_completion("") is None
    assert parse_completion("{bad json") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
