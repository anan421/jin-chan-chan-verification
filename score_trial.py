#!/usr/bin/env python3
"""Score the weakest-link trial (vision round 5).

Reads testset-v3.json for the true kind of each of the 21 weak questions,
scores trial1, trial2 (raw), and trial2-clean (trial2b redo replaces the
contaminated trial2 S5-3-2 file), and prints per-kind breakdowns plus
trial1-vs-trial2 agreement. Also writes score-trial.json next to the
prediction files.
"""
import json, glob, os
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
TRIAL = os.path.join(BASE, 'runs', 'weakest-link-vision5-2026-11-22', 'trial')

ts = json.load(open(os.path.join(BASE, 'testset-v3.json')))
qs = ts['questions'] if isinstance(ts, dict) else ts
truth = {q['q_id']: q['kind'] for q in qs}
WEAK = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 26, 27, 31, 32, 53, 57, 64, 81, 82]

def load(pattern, replace=None):
    preds = {}
    for f in sorted(glob.glob(os.path.join(TRIAL, pattern))):
        for p in json.load(open(f)):
            preds[p['q_id']] = p
    if replace:
        for p in json.load(open(os.path.join(TRIAL, replace))):
            preds[p['q_id']] = p
    return preds

t1 = load('predictions-trial1-*.json')
t2 = load('predictions-trial2-*.json')
t2c = load('predictions-trial2-*.json', replace='predictions-trial2b-S5-3-2.json')

result = {}
for name, preds in [('trial1', t1), ('trial2_raw', t2), ('trial2_clean', t2c)]:
    assert set(preds) == set(WEAK), (name, sorted(set(preds) ^ set(WEAK)))
    correct = [q for q in WEAK if preds[q]['predicted_kind'] == truth[q]]
    bykind = defaultdict(lambda: [0, 0])
    for q in WEAK:
        bykind[truth[q]][1] += 1
        if preds[q]['predicted_kind'] == truth[q]:
            bykind[truth[q]][0] += 1
    result[name] = {
        'correct': len(correct), 'total': len(WEAK), 'correct_qids': correct,
        'by_kind': {k: v for k, v in sorted(bykind.items())},
        'guesses': {q: preds[q]['predicted_kind'] for q in WEAK},
    }
    print(f"{name}: {len(correct)}/{len(WEAK)} correct: {correct}")
    for k in sorted(bykind):
        print(f"  {k}: {bykind[k][0]}/{bykind[k][1]}")

# trial1 clean score: q13 excluded (audit found its facts describe the event
# itself; the question's round date is 32 days after its event date).
t1_clean = [q for q in result['trial1']['correct_qids'] if q != 13]
result['trial1_clean'] = {'correct': len(t1_clean), 'total': len(WEAK) - 1,
                          'correct_qids': t1_clean, 'excluded_qids': [13],
                          'exclusion_reason': 'q13 facts describe the event itself'}
print(f"trial1_clean (q13 excluded): {len(t1_clean)}/{len(WEAK) - 1}")

agree = [q for q in WEAK if t1[q]['predicted_kind'] == t2c[q]['predicted_kind']]
result['agreement_trial1_vs_trial2_clean'] = {'same_guess': len(agree), 'total': len(WEAK)}
print(f"agreement trial1 vs trial2_clean: {len(agree)}/{len(WEAK)} same guess")

with open(os.path.join(TRIAL, 'score-trial.json'), 'w') as fh:
    json.dump(result, fh, indent=2, ensure_ascii=False)
print("wrote score-trial.json")
