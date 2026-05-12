# personal photos

photos you take yourself go in this folder.

## why this folder exists

public datasets (clockbench, wikimedia commons) only get you so far.
the real signal is workplace contexts the model has never seen:
pressure gauges at industrial sites, lab balances, hospital BP cuffs,
shop voltmeters under fluorescent light.

these are the "type 1 data" that anyone can label trivially but
frontier models can't read. that's the moat.

## photo guidelines

1. **reading must be unambiguous.** you can read it in 5 seconds with
   high confidence. if you have to squint or second-guess, skip it.
2. **avoid zero readings.** boring. trivially correct. needle resting at
   0 is not useful signal. find ones in active use.
3. **shoot real angles.** how the instrument is normally seen. don't
   stage perfect head-on shots — the model needs to handle parallax,
   glare, partial occlusion, dim light.
4. **note ground truth IMMEDIATELY.** don't rely on memory. write it
   down or fill in the JSON as you take the photo.
5. **diversity matters more than count.** 20 photos across 7
   instrument types beats 50 photos of wall clocks.

## what to shoot

workplace (preferred):
- pressure gauges at any industrial site
- lab balances, beam scales
- voltmeters/ammeters in shops, electrical panels
- analog speedometers/tachometers in vehicles
- BP cuffs in clinics (with permission)
- water meters, gas meters
- oven dials, thermostats (the analog kind)

home / general (acceptable):
- wall clocks, mantle clocks
- kitchen scales, postal scales
- bathroom scales
- analog thermometers (dial or mercury)
- tire pressure gauges
- hygrometers, barometers

## naming

save image as: `<type>_<NNN>.jpg`

where `<type>` is one of:
- `clock`, `pressure_gauge`, `thermometer`, `scale`, `voltmeter`,
  `ammeter`, `tachometer`, `speedometer`, `sphygmomanometer`,
  `multimeter`, `barometer`, `hygrometer`, `other`

and `<NNN>` starts at `100` for personal photos (to avoid collision
with public set which uses `001`-`099`).

example: `pressure_gauge_103.jpg`

## ground truth json

create matching file in `data/ground_truth/<type>_<NNN>.json` with
this shape (copy `_template.json` next to this README):

```json
{
  "image": "pressure_gauge_103.jpg",
  "instrument_type": "pressure_gauge",
  "reading": 45.0,
  "unit": "psi",
  "scale_max": 100.0,
  "source": "personal",
  "difficulty": "medium",
  "tags": ["workplace", "off_zero", "real_photo"],
  "verification_method": "label says 0-100 psi, needle centered between 40 and 50, my own read at high confidence"
}
```

then add the new entry to `data/manifest.json` (or rerun
`scripts/rebuild_manifest.py`).

## after you shoot

run:
```
python3 scripts/rebuild_manifest.py
python3 -m pytest environments/analog_instrument/test_rubric.py
```

then the env will pick up the new photos automatically.
