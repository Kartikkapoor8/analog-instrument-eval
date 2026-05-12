# sourcing methodology

how this dataset scales beyond the v0.1 public set.

## the phase 1 dataset (current)

30 verified public images. mix of:
- clockbench public sample (8 synthetic clocks)
- wikimedia commons (real photos: clocks, gauges, scales, sphygmomanometer, hygrometer, barometers)

ground truth is verified manually. each image has a json file with source url, reading, unit, and a short verification note explaining the read.

sufficient for env validation and the deterministic-confidence finding. not sufficient for commercial training. real instruments in workplace contexts are the moat.

## phase 2 plan: student-sourced photos

frontier models can't self-label this task (see CALIBRATION_ANALYSIS.md — opus reads gauges wrong 8 times in a row at T=1.0). so labels have to come from humans. and any human who can read a number off a dial can label these. that's the unlock.

target: 500 photos with verified ground truth in 6 weeks.

### categories and where students would find them

industrial / shop floor (highest value, hardest access):
- factory pressure gauges (steam, hydraulic, pneumatic)
- temperature gauges on furnaces, ovens, boilers
- voltmeter/ammeter on electrical panels
- flow meters with analog dials
- access via: mechanical engineering students with internships, vocational programs, industrial co-ops

healthcare:
- aneroid sphygmomanometers (active readings during measurement)
- analog medical scales
- pediatric/adult thermometers
- pressure regulators on oxygen tanks
- access via: nursing students, pre-med shadowing, hospital volunteers (with provenance and consent doc)

automotive:
- analog speedometers and tachometers (older cars, motorcycles, trucks)
- tire pressure gauges (handheld and stationary)
- fuel gauges with analog needles
- shop air pressure gauges
- access via: auto shop apprentices, car-owner communities, motorcycle clubs

lab / research:
- analog balances (still common in chemistry labs)
- voltmeters/ammeters on bench supplies
- analog oscilloscope screens (rare but high-value)
- vacuum gauges, pressure transducers
- access via: chemistry/physics undergrads, lab tech jobs

home / vintage:
- wall clocks, mantle clocks, grandfather clocks
- kitchen scales (especially european analog ones)
- bathroom scales (analog still common)
- analog outdoor thermometers
- access via: anyone with a household / grandparents

### bounty structure

per-photo payment with bonuses for hard cases:

| case type | base | bonus | total |
|---|---|---|---|
| trivial (needle at 0, single scale) | $0.50 | - | $0.50 |
| standard (single scale, off-zero, clear) | $1.50 | - | $1.50 |
| multi-scale instrument | $1.50 | +$1.00 | $2.50 |
| sub-tick precision (between marks) | $1.50 | +$1.00 | $2.50 |
| workplace context (provenance verified) | varies | +$1.00 | varies |

500 photos × $2 average = $1000. cheap relative to the value of the dataset.

### quality control

each photo enters a 3-step verification:
1. photographer logs ground truth at intake (their read)
2. second student labels independently from the photo
3. third student adjudicates if 1 and 2 disagree by more than the rubric tolerance

mismatch rate is itself a signal. images where humans disagree get tagged as "ambiguous" and used for confidence-calibration training, not pass/fail eval.

anchor calibration: a set of 20 photos with known answers gets mixed into every labeler's queue. labelers who fail anchors get retrained or removed.

### consent template at intake

every workplace photo requires:
- photographer's signature that they have permission to photograph the instrument
- if identifiable people are in frame, written consent or face-blur required
- if proprietary equipment is shown, a release from the property owner

we keep the consent doc on file. if a buyer needs to verify provenance later, we can produce it.

## why students are the right labor pool

1. **task is generalist.** reading a gauge needs 30 minutes of training. anyone can do it. no domain expertise required for most instruments.

2. **frontier models can't self-label.** verified by this env. opus 4.6 fails 8/9 clocks, gets 50% on scales, 0% on hygrometer. no zero-shot pipeline replaces the human read.

3. **distributed access through campuses.** a CS student in toronto has zero pressure gauge access. their friend in mechanical engineering with a factory co-op has dozens. pre-pair them: photographer + labeler.

4. **cheaper than expert contractors.** $2/photo at scale beats $50/hour for industrial photographers. quality control by anchor calibration keeps the bar high.

5. **fast.** a student-operator can capture and log 20 photos in 30 minutes during a shift. 500 photos is 25 students × 1 hour.

## risks and mitigations

- **risk: photos look staged or duplicated.** mitigation: anchor calibration + spot audits of EXIF data + reject sequential photos taken within 5 seconds of each other.
- **risk: labelers cheat with AI.** mitigation: every labeler must explain their read in 1 sentence. cheap llm explanations are detectable.
- **risk: legal/consent issues from workplace photos.** mitigation: consent doc at intake, no people in frame by default, prefer instruments in maintenance/static contexts.
- **risk: dataset gets data-leaked into training corpora.** mitigation: hold out a private test set. only ship public set. v0.1's public set already has this structure (manifest + ground_truth visible, larger private set held back at later versions).

## what phase 1 already proves

before any phase 2 spend, this env shows:
- the failure exists (30 images, opus 11% on clocks, 23% overall)
- the failure is deterministic at T=1.0 (sampling won't fix it)
- labels are generalist (i can verify them in 5 seconds each as a 17-year-old)
- the rubric is clean (no llm judge, no canonicalization tricks)

phase 2 is "scale labor to 500-2000 photos." that's the moat — not the env code, the labeled real photos.

## tldr

500 photos, 6 weeks, ~$1000 in bounties, 25-50 students. 3-step verification. anchor calibration. consent doc at intake. ship a private test set, public train set. that's the path from v0.1 to commercial-grade.
