import json, re, hashlib, sys

base = 'ts-spaces/jin-chan-chan-fu-pan-ai-da-ting-2022-2026/assets/data.json'
d = json.load(open(base))
# 1. trend data.json identical to replay data.json
t = open('ts-spaces/jin-chan-chan-ai-da-ting-qu-shi-tu/assets/data.json','rb').read()
r = open(base,'rb').read()
assert hashlib.sha256(t).hexdigest() == hashlib.sha256(r).hexdigest(), 'trend data.json differs'
print('trend data.json identical to replay data.json OK')

# 2. board inline data vs data.json
b = open('jin-chan-chan-3d-board/index.html').read()
def js_obj(txt):
    txt = re.sub(r'([A-Za-z_][A-Za-z0-9_]*)\s*:', r'"\1":', txt)
    txt = re.sub(r',\s*([}\]])', r'\1', txt)
    return json.loads(txt)
ev = js_obj(re.search(r'const ROUND_EVENTS = (\[.*?\]);\n', b, re.S).group(1))
snaps = js_obj(re.search(r'const REPLAY_SNAPSHOTS = (\{.*?\n    \});', b, re.S).group(1))
order = json.loads(re.search(r'const REPLAY_ORDER = (\[.*?\]);', b, re.S).group(1))
ohp = js_obj(re.search(r'const SEASON_OPEN_HP = (\{.*?\});', b, re.S).group(1))
ogold = js_obj(re.search(r'const SEASON_OPEN_GOLD = (\{.*?\});', b, re.S).group(1))

rounds = [(s['id'], rr) for s in d['seasons'] for rr in s['rounds']]
assert len(ev) == len(rounds) == 94, (len(ev), len(rounds))
tot_moves = 0
for (sid, rr), e in zip(rounds, ev):
    assert e[0] == sid and e[1] == rr['code'], (e[0], e[1], sid, rr['code'])
    assert e[2] == rr['date'] and e[4] == rr['title'], (e, rr['code'])
    assert len(e[7]) == len(rr['moves']), (sid, rr['code'])
    for m, dm in zip(e[7], rr['moves']):
        assert m[0] == dm[0] and m[2] == dm[2] and m[3] == dm[3], (m, dm)
    tot_moves += len(e[7])
assert tot_moves == 751, tot_moves
print('board ROUND_EVENTS == data.json rounds/moves OK (94 rounds, 751 moves)')

labels = [f"{sid} {rr['code']}" for sid, rr in rounds]
assert order == labels, 'REPLAY_ORDER mismatch'
assert list(snaps.keys()) == labels, 'snapshot keys mismatch'
# snapshots vs data.json standings (recomputed from openings + moves)
# 快照含已见的全部玩家：当季名单取当季累计值，早季专属玩家取冻结的上季末值。
seen_hp = {}
seen_gold = {}
for s in d['seasons']:
    hp = dict(d['openings'][s['id']]['hp']); gold = dict(d['openings'][s['id']]['gold'])
    for rr in s['rounds']:
        for m in rr['moves']:
            hp[m[0]] = hp.get(m[0], d['openings'][s['id']]['hp'][m[0]]) + m[2]
            gold[m[0]] = gold.get(m[0], d['openings'][s['id']]['gold'][m[0]]) + m[3]
        lab = f"{s['id']} {rr['code']}"
        exp_hp = {p: hp[p] if p in hp else seen_hp[p] for p in snaps[lab]['hp']}
        exp_gold = {p: gold[p] if p in gold else seen_gold[p] for p in snaps[lab]['gold']}
        assert snaps[lab]['hp'] == exp_hp, (lab, 'hp')
        assert snaps[lab]['gold'] == exp_gold, (lab, 'gold')
    seen_hp.update(hp); seen_gold.update(gold)
print('board snapshots == data.json standings OK')
assert ohp == {s: d['openings'][s]['hp'] for s in d['openings']}, 'open hp mismatch'
assert ogold == {s: d['openings'][s]['gold'] for s in d['openings']}, 'open gold mismatch'
print('board SEASON_OPEN_HP/GOLD == data.json openings OK')

# 3. season-end checks
def season_end(sid):
    hp = dict(d['openings'][sid]['hp']); gold = dict(d['openings'][sid]['gold'])
    for s in d['seasons']:
        if s['id'] != sid: continue
        for rr in s['rounds']:
            for m in rr['moves']:
                hp[m[0]] = hp.get(m[0], 100) + m[2]; gold[m[0]] = gold.get(m[0], 0) + m[3]
    return {'hp': hp, 'gold': gold}
e5 = season_end('S5'); e6 = season_end('S6')
assert (e5['hp']['OAI'], e5['gold']['OAI']) == (79, 58), e5['hp']['OAI']
assert (e5['hp']['ANTH'], e5['gold']['ANTH']) == (121, 113)
assert (e5['hp']['NVDA'], e5['gold']['NVDA']) == (36, 54)
assert (e6['hp']['OAI'], e6['gold']['OAI']) == (82, 59), e6
print('S5/S6 end values OK: OAI 79/58, ANTH 121/113, NVDA 36/54; S6 OAI 82/59')
print('ALL CONSISTENCY CHECKS PASSED')
