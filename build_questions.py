#!/usr/bin/env python3
"""Build question files for Round 5 thin-history (MUSK/TSMC, round-first method).

Inputs (no answers anywhere):
- Round-3 question files: facts_before_round_date + round/date/questions.
- trace-latest.json: walk-forward player history (moves with date < round date),
  excluding semantic_kind == 'unknown'.
Outputs:
- runs/thin-history-round5-2026-11-22/questions-<round>.json (11 files)
  Each file: round, date, questions (MUSK/TSMC only), facts, vocabulary, method.
  No actual_kind, no correct, no search-first predicted_kind.
"""
import json
import os
from collections import Counter

R3_DIR = '/home/hatch/workspace/verification-r3-thin/runs/thin-history-round3-2026-11-22'
TRACE = '/home/hatch/workspace/verification/traces/trace-latest.json'
OUT_DIR = '/home/hatch/workspace/verification-r5-thin/runs/thin-history-round5-2026-11-22'

VOCAB = ['anthropic_ipo', 'ascend', 'bis_rule', 'blackwell', 'capex', 'chatgpt',
         'claude', 'colossus', 'doubao', 'doubao_price_war', 'energy', 'financing',
         'gemini', 'huang_resign', 'hunyuan', 'llama', 'megaspeed', 'msft_invest',
         'musk_table', 'open_source', 'overseas_rental', 'pangu', 'r1', 'sec_probe',
         'spacex_xai', 'stargate', 'tongyi', 'v3', 'wenxin']

METHOD = (
    "Round-first method (see design/thin-history-method-round5.md). "
    "Step 1 - Theme: from facts dated on or before the round date, identify the round's "
    "headline event (the single biggest external event affecting the hall). If it is a shared "
    "event, guess its kind. If it is one company's product/model launch: MUSK -> spacex_xai, "
    "TSMC -> the headline kind. If the headline event's protagonist is the player themself, "
    "treat it as no headline event and go to Step 2. "
    "Step 2 - Fallback (only if Step 1 finds no headline event): MUSK -> financing; "
    "TSMC -> most frequent kind in the prefix (ties by most recent; none known -> capex). "
    "Only use facts dated on or before the round date. Do not read the trace, scoring files, "
    "other rounds' files, or search-first predictions."
)


def kind_of(m):
    return m.get('semantic_kind') or m.get('action_kind')


def main():
    tr = json.load(open(TRACE))
    players = {p['key']: p['id'] for p in tr['players']}
    moves = tr['moves']
    # rounds in order (season, round_label, date)
    rounds = sorted(set((m['season'], m['round_label'], m['date']) for m in moves))
    # map (season, round_label) -> date
    round_date = {(s, rl): d for (s, rl, d) in rounds}
    # per-round kinds by player (from trace, known kinds only)
    # round_order index for "previous 3 rounds"
    round_keys = [(s, rl) for (s, rl, d) in rounds]

    os.makedirs(OUT_DIR, exist_ok=True)
    n_q = 0
    for fn in sorted(os.listdir(R3_DIR)):
        if not fn.startswith('questions-') or not fn.endswith('.json'):
            continue
        qf = json.load(open(os.path.join(R3_DIR, fn)))
        rnd = qf['round']          # e.g. 'S4 1-1'
        date = qf['date']
        season = int(rnd.split()[0][1:])
        rl = rnd.split()[1]
        # previous 3 rounds (by order) before this round
        idx = round_keys.index((season, rl))
        prev3 = round_keys[max(0, idx - 3):idx]
        # previous round (immediately before)
        prev1 = round_keys[idx - 1] if idx > 0 else None
        # kinds in previous round, all players
        prev_round_kinds = {}
        if prev1 is not None:
            for m in moves:
                if (m['season'], m['round_label']) == prev1:
                    k = kind_of(m)
                    if k != 'unknown':
                        prev_round_kinds[tr['players'][m['player']]['key']] = k
        questions = []
        for q in qf['questions']:
            player = q['player']
            pid = players[player]
            prior = [m for m in moves if m['player'] == pid and m['date'] < date]
            counts = Counter(kind_of(m) for m in prior if kind_of(m) != 'unknown')
            # kinds in previous 3 rounds (in round order)
            last3 = []
            for (ps, prl) in prev3:
                for m in moves:
                    if m['player'] == pid and (m['season'], m['round_label']) == (ps, prl):
                        k = kind_of(m)
                        if k != 'unknown':
                            last3.append(k)
            questions.append({
                'season': q['season'],
                'round_label': q['round_label'],
                'round': q['round'],
                'date': q['date'],
                'player': player,
                'hp_start': q.get('hp_start'),
                'gold_start': q.get('gold_start'),
                'rules_version': q.get('rules_version'),
                'first_appearance': q.get('first_appearance'),
                'player_history_counts': dict(counts),
                'player_most_frequent': counts.most_common(1)[0][0] if counts else None,
                'player_last3_kinds': last3,
                'prev_round_kinds': prev_round_kinds,
            })
            n_q += 1
        out = {
            'round': rnd,
            'date': date,
            'method': METHOD,
            'vocabulary': VOCAB,
            'questions': questions,
            'facts_before_round_date': qf.get('facts_before_round_date', []),
        }
        out_path = os.path.join(OUT_DIR, fn)
        json.dump(out, open(out_path, 'w'), ensure_ascii=False, indent=2)
        print(f"{fn}: {len(questions)} questions, date={date}")
    print('total thin questions:', n_q)


if __name__ == '__main__':
    main()
