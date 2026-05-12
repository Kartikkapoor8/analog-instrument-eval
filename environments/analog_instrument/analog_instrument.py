"""
analog_instrument — read analog instruments from photos.

A Prime Intellect verifiers environment. The model is given a photograph of an
analog instrument (clock, pressure gauge, thermometer, scale, voltmeter, etc.)
and must output structured JSON identifying the instrument and its current
reading.

The rubric is fully deterministic (no model in the loop):
  1. Parse the model's JSON output.
  2. Require unit match (case insensitive, with alias table).
  3. Require canonicalized instrument type match.
  4. For clocks: pass if predicted HH:MM is within 1 minute of ground truth.
  5. For numeric instruments: pass if predicted reading is within 5% of
     scale_max of ground truth.
  6. Reward is binary (1.0 or 0.0) per item.

Tracked-only metrics (weight 0):
  - format_compliance: did the JSON parse?
  - confidence_calibration: was reported confidence correlated with correctness?
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

import verifiers as vf
from datasets import Dataset


DATA_DIR = Path(__file__).parent / "data"
IMAGES_DIR = DATA_DIR / "images"
GT_DIR = DATA_DIR / "ground_truth"
MANIFEST_PATH = DATA_DIR / "manifest.json"


SYSTEM_PROMPT = """You will be shown a photo of an analog instrument. Identify the instrument type and read its current value. Output ONLY valid JSON in this format:
{
  "instrument_type": "<type>",
  "reading": <number or HH:MM string>,
  "unit": "<unit>",
  "scale_max": <number or null>,
  "confidence": "<high|medium|low>"
}

For clocks, reading is HH:MM format.
For other instruments, reading is a number.
Output ONLY the JSON, no other text."""


# canonical instrument type → set of accepted aliases (lowercase)
TYPE_ALIASES: dict[str, set[str]] = {
    "analog_clock": {"analog_clock", "clock", "analog clock", "wall clock",
                     "wristwatch", "watch", "analog_watch", "time"},
    "pressure_gauge": {"pressure_gauge", "pressure gauge", "manometer",
                       "gauge", "pressure"},
    "thermometer": {"thermometer", "analog thermometer", "dial thermometer",
                    "mercury thermometer", "temperature"},
    "scale": {"scale", "bathroom scale", "kitchen scale", "weighing scale",
              "balance", "postal scale", "spring scale", "weight"},
    "voltmeter": {"voltmeter", "analog voltmeter", "panel voltmeter", "volt meter"},
    "ammeter": {"ammeter", "analog ammeter", "panel ammeter", "amp meter"},
    "multimeter": {"multimeter", "analog multimeter", "vom"},
    "tachometer": {"tachometer", "rpm gauge", "tach", "rev counter"},
    "speedometer": {"speedometer", "speed gauge"},
    "sphygmomanometer": {"sphygmomanometer", "blood pressure gauge",
                         "bp gauge", "bp cuff", "aneroid sphygmomanometer",
                         "aneroid"},
    "barometer": {"barometer", "aneroid barometer"},
    "hygrometer": {"hygrometer", "humidity gauge"},
    "other": {"other", "unknown"},
}

# unit equivalence groups (lowercase, no spaces unless meaningful)
UNIT_ALIASES: dict[str, set[str]] = {
    "mph": {"mph", "miles per hour", "mi/h", "mi per hour"},
    "kph": {"kph", "km/h", "kmh", "kilometers per hour"},
    "kg": {"kg", "kilogram", "kilograms", "kgs"},
    "lb": {"lb", "lbs", "pound", "pounds"},
    "oz": {"oz", "ounce", "ounces"},
    "rpm": {"rpm", "r/min", "rev/min", "revolutions per minute"},
    "mmhg": {"mmhg", "mm hg", "mm of mercury", "torr"},
    "psi": {"psi", "pounds per square inch"},
    "bar": {"bar", "bars"},
    "pa": {"pa", "pascal", "pascals"},
    "kpa": {"kpa", "kilopascal", "kilopascals"},
    "celsius": {"celsius", "c", "°c", "degrees celsius", "degc"},
    "fahrenheit": {"fahrenheit", "f", "°f", "degrees fahrenheit", "degf"},
    "v": {"v", "volt", "volts", "volts dc", "volts ac", "vdc", "vac"},
    "a": {"a", "amp", "amps", "ampere", "amperes"},
    "ma": {"ma", "milliamp", "milliamps", "milliampere"},
    "ohm": {"ohm", "ohms", "Ω"},
    "time": {"time", ""},  # clocks
    "percent": {"percent", "%"},
    "rh": {"rh", "relative humidity", "%rh"},
    "inhg": {"inhg", "in hg", "inches of mercury", "inches hg"},
    "ft": {"ft", "foot", "feet"},
    "m": {"m", "meter", "meters", "metre"},
}


def normalize_type(t: Any) -> str:
    """Canonicalize an instrument type string to one of TYPE_ALIASES keys, or 'unknown'."""
    if not isinstance(t, str):
        return "unknown"
    raw = t.strip().lower()
    # strip parenthetical extras like "sphygmomanometer (blood pressure gauge)"
    raw = re.sub(r"\(.*?\)", "", raw).strip()
    raw = raw.replace("-", " ").replace("_", " ")
    for canon, aliases in TYPE_ALIASES.items():
        if raw == canon.replace("_", " "):
            return canon
        for a in aliases:
            if raw == a:
                return canon
    return "unknown"


def normalize_unit(u: Any) -> str:
    """Canonicalize a unit string to a key in UNIT_ALIASES, or the lowercased raw value."""
    if u is None:
        return ""
    raw = str(u).strip().lower()
    raw = raw.replace(" ", "")
    for canon, aliases in UNIT_ALIASES.items():
        # normalize aliases too
        norm_aliases = {a.replace(" ", "") for a in aliases}
        if raw == canon or raw in norm_aliases:
            return canon
    return raw


def units_match(pred: Any, gt: Any) -> bool:
    """True if predicted unit is equivalent to ground-truth unit."""
    p = normalize_unit(pred)
    g = normalize_unit(gt)
    if g in ("time", ""):
        # clocks don't have units the same way; accept any reasonable
        return True
    return p == g


def parse_clock(s: Any) -> tuple[int, int] | None:
    """Parse an HH:MM string. Returns (hours, minutes) or None."""
    if not isinstance(s, str):
        return None
    m = re.search(r"(\d{1,2})\s*[:hH]\s*(\d{1,2})", s)
    if not m:
        return None
    h = int(m.group(1))
    mn = int(m.group(2))
    if not (0 <= h <= 23 and 0 <= mn <= 59):
        return None
    return h, mn


def score_clock(predicted_time: Any, gt_time: str,
                tolerance_min: int = 1,
                alts: list[str] | None = None) -> float:
    """Pass if predicted HH:MM is within tolerance_min minutes of ground truth.

    Hours are matched modulo 12 (analog clock face has no AM/PM distinction).
    """
    p = parse_clock(predicted_time)
    if p is None:
        return 0.0
    ph, pm = p
    p_total = (ph % 12) * 60 + pm
    candidates: list[tuple[int, int]] = []
    g = parse_clock(gt_time)
    if g:
        candidates.append(g)
    if alts:
        for a in alts:
            ag = parse_clock(a)
            if ag:
                candidates.append(ag)
    if not candidates:
        return 0.0
    for ch, cm in candidates:
        c_total = (ch % 12) * 60 + cm
        diff = abs(c_total - p_total)
        # wrap-around (12 hour clock)
        diff = min(diff, 12 * 60 - diff)
        if diff <= tolerance_min:
            return 1.0
    return 0.0


def score_numeric(predicted: Any, gt_value: float, scale_max: float,
                  tolerance_frac: float = 0.05) -> float:
    """Pass if |predicted - gt| <= tolerance_frac * scale_max."""
    try:
        if isinstance(predicted, str):
            num = re.search(r"-?\d+(?:\.\d+)?", predicted.replace(",", ""))
            if not num:
                return 0.0
            p = float(num.group(0))
        else:
            p = float(predicted)
    except (TypeError, ValueError):
        return 0.0
    if scale_max is None or scale_max <= 0:
        return 0.0
    tol = tolerance_frac * float(scale_max)
    return 1.0 if abs(p - float(gt_value)) <= tol else 0.0


def score_reading(predicted: dict | None, ground_truth: dict) -> float:
    """Main scoring function. Returns 1.0 if reading passes all checks, else 0.0.

    Predicted is the parsed JSON dict from the model (or None if parse failed).
    Ground truth has keys: instrument_type, reading, unit, scale_max,
    optional ground_truth_alt (list of alt clock strings).
    """
    if not isinstance(predicted, dict):
        return 0.0

    # instrument type must match (canonicalized)
    pred_type = normalize_type(predicted.get("instrument_type"))
    gt_type = normalize_type(ground_truth.get("instrument_type"))
    if pred_type == "unknown" or pred_type != gt_type:
        return 0.0

    # clocks: 1-minute tolerance, no unit check needed
    if gt_type == "analog_clock":
        return score_clock(
            predicted.get("reading"),
            str(ground_truth.get("reading")),
            tolerance_min=1,
            alts=ground_truth.get("ground_truth_alt") or [],
        )

    # numeric instruments: unit must match AND value within tolerance
    if not units_match(predicted.get("unit"), ground_truth.get("unit")):
        return 0.0
    return score_numeric(
        predicted.get("reading"),
        float(ground_truth["reading"]),
        float(ground_truth["scale_max"]),
        tolerance_frac=0.05,
    )


def parse_completion(text: str) -> dict | None:
    """Extract a JSON dict from a model completion. Tolerates code fences and stray text."""
    if not isinstance(text, str):
        return None
    s = text.strip()
    # strip ``` fences
    fence = re.search(r"```(?:json|JSON)?\s*([\s\S]*?)```", s)
    if fence:
        s = fence.group(1).strip()
    # try direct
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    # fall back to first {...} block
    m = re.search(r"\{[\s\S]*\}", s)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


# ---- Verifiers integration ----

def _completion_text(completion: Any) -> str:
    """Extract assistant text from completion (string or chat message list)."""
    if isinstance(completion, str):
        return completion
    if isinstance(completion, list):
        for msg in reversed(completion):
            if not isinstance(msg, dict) or msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(
                    p.get("text", "")
                    for p in content
                    if isinstance(p, dict) and isinstance(p.get("text", ""), str)
                )
    return ""


def correctness_reward(completion: Any, info: dict, **kwargs) -> float:
    """Main reward: 1.0 if reading passes the rubric, else 0.0."""
    pred = parse_completion(_completion_text(completion))
    gt = json.loads(info["ground_truth_json"]) if isinstance(info.get("ground_truth_json"), str) else info["ground_truth"]
    return score_reading(pred, gt)


def format_reward(completion: Any, **kwargs) -> float:
    """Tracked-only: 1.0 if completion parses to JSON, else 0.0."""
    return 1.0 if parse_completion(_completion_text(completion)) is not None else 0.0


def confidence_correct_reward(completion: Any, info: dict, **kwargs) -> float:
    """Tracked-only: 1.0 if model said 'high' AND got it right. Used for calibration analysis."""
    pred = parse_completion(_completion_text(completion))
    if pred is None:
        return 0.0
    conf = str(pred.get("confidence", "")).strip().lower()
    gt = json.loads(info["ground_truth_json"]) if isinstance(info.get("ground_truth_json"), str) else info["ground_truth"]
    correct = score_reading(pred, gt) == 1.0
    return 1.0 if (conf == "high" and correct) else 0.0


def confidence_wrong_reward(completion: Any, info: dict, **kwargs) -> float:
    """Tracked-only: 1.0 if model said 'high' BUT got it wrong. The calibration failure signal."""
    pred = parse_completion(_completion_text(completion))
    if pred is None:
        return 0.0
    conf = str(pred.get("confidence", "")).strip().lower()
    gt = json.loads(info["ground_truth_json"]) if isinstance(info.get("ground_truth_json"), str) else info["ground_truth"]
    correct = score_reading(pred, gt) == 1.0
    return 1.0 if (conf == "high" and not correct) else 0.0


def _image_data_url(path: Path) -> str:
    """Encode image file as a data URL for chat-completions image input."""
    ext = path.suffix.lstrip(".").lower()
    media_type = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                  "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        b64 = base64.standard_b64encode(f.read()).decode()
    return f"data:{media_type};base64,{b64}"


def load_environment(**kwargs) -> vf.Environment:
    """Load the analog_instrument SingleTurnEnv from data/manifest.json."""
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"manifest.json not found at {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text())

    rows: list[dict] = []
    for entry in manifest:
        img_rel = entry["image"]
        img_path = IMAGES_DIR / img_rel
        if not img_path.exists():
            continue
        gt_path = GT_DIR / entry["ground_truth_file"]
        if not gt_path.exists():
            continue
        gt = json.loads(gt_path.read_text())

        # build chat-completions style multimodal user message.
        # use list-of-parts for BOTH system and user so arrow can store the
        # content field uniformly across all rows.
        data_url = _image_data_url(img_path)
        sys_content = [{"type": "text", "text": SYSTEM_PROMPT}]
        user_content = [
            {"type": "image_url", "image_url": {"url": data_url}},
            {"type": "text", "text": "Read this instrument."},
        ]

        # serialize ground_truth as JSON string so arrow can store it uniformly
        rows.append({
            "prompt": [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": user_content},
            ],
            "answer": json.dumps({
                "reading": gt["reading"],
                "unit": gt.get("unit", ""),
                "instrument_type": gt["instrument_type"],
            }),
            "info": {
                "image": img_rel,
                "instrument_type": gt["instrument_type"],
                "ground_truth_json": json.dumps(gt),
                "source": gt.get("source", ""),
                "difficulty": gt.get("difficulty", "medium"),
            },
            "task": "analog_instrument",
        })

    dataset = Dataset.from_list(rows)
    rubric = vf.Rubric(
        funcs=[correctness_reward, format_reward,
               confidence_correct_reward, confidence_wrong_reward],
        weights=[1.0, 0.0, 0.0, 0.0],
    )
    return vf.SingleTurnEnv(
        dataset=dataset,
        rubric=rubric,
        **kwargs,
    )
