# -*- coding: utf-8 -*-
"""从回放页 data.json 生成 3D 棋盘内嵌数据（ROUND_EVENTS / 快照 / 开局表）。"""
import json, re, copy
from pathlib import Path

# 路径从仓库位置推导：仓库在 <工作区>/verification，数据与棋盘在工作区根目录下。
WS = Path(__file__).resolve().parent.parent
D = str(WS / 'ts-spaces/jin-chan-chan-fu-pan-ai-da-ting-2022-2026/assets/data.json')
B = str(WS / 'jin-chan-chan-3d-board/index.html')
d = json.load(open(D))
html = open(B).read()

seasons = d['seasons']
openings = d['openings']

# ---- ROUND_EVENTS / REPLAY_ORDER / 快照 ----
events = []
order = []
snaps = {}
# 已见玩家的最后已知值：S0 专属玩家在后续赛季快照里冻结为 S0 季末值（与线上棋盘一致）。
seen_hp = {}
seen_gold = {}
for s in seasons:
    sid = s['id']
    hp = dict(openings[sid]['hp'])
    gd = dict(openings[sid]['gold'])
    roster = [m['id'] for m in s['meta']]
    for r in s['rounds']:
        label = f"{sid} {r['code']}"
        order.append(label)
        events.append([sid, r['code'], r['date'], r['type'], r['title'], r['global'], r['verdict'],
                       [[m[0], m[1], m[2], m[3]] for m in r['moves']]])
        for (pl, _t, dh, dg) in r['moves']:
            hp[pl] = hp.get(pl, 0) + dh
            gd[pl] = gd.get(pl, 0) + dg
        snap_players = list(dict.fromkeys(roster + list(seen_hp)))
        snaps[label] = {"hp": {p: hp[p] if p in hp else seen_hp[p] for p in snap_players},
                        "gold": {p: gd[p] if p in gd else seen_gold[p] for p in snap_players}}
    seen_hp.update(hp)
    seen_gold.update(gd)

assert len(order) == 94 and len(events) == 94 and len(snaps) == 94
assert sum(len(e[7]) for e in events) == 751

# ---- 开局表 ----
open_hp = {sid: openings[sid]['hp'] for sid in
           ['S0', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6']}
open_gold = {sid: openings[sid]['gold'] for sid in
             ['S0', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6']}

# ---- 校验：与旧棋盘季末快照一致（S1~S6 季末） ----
old = open(WS / 'jin-chan-chan-3d-board/index.html.bak-pre-monthly').read()
m = re.search(r'const REPLAY_SNAPSHOTS = (\{.*?\n    \});', old, re.S)
assert m, 'old snapshots not found'
_raw = re.sub(r'([A-Za-z_][A-Za-z0-9_]*)\s*:', r'"\1":', m.group(1))
_raw = re.sub(r',\s*([}\]])', r'\1', _raw)
old_snaps = json.loads(_raw)
season_end_label = {'S1': 'S1 3-2', 'S2': 'S2 5-1', 'S3': 'S3 6-1', 'S4': 'S4 5-1',
                    'S5': 'S5 6-2', 'S6': 'S6 1-1'}
new_end_label = {'S1': 'S1 2022-12', 'S2': 'S2 2023-12', 'S3': 'S3 2024-12',
                 'S4': 'S4 2025-12', 'S5': 'S5 2026-11', 'S6': 'S6 1-1'}
# S6 不比旧快照：S6 1-1 在 2026-11-24 又加 2 条（黄仁勋复任、Megaspeed），NVDA 季末由 36 血 / 54 金变为 37 血 / 55 金。
# 旧快照只有当季名单，快照只比旧快照有的玩家（早季专属玩家冻结值不在旧快照里）。
for sid in ['S1', 'S2', 'S3', 'S4', 'S5']:
    old_end = old_snaps[season_end_label[sid]]
    new_end = snaps[new_end_label[sid]]
    assert {p: new_end['hp'][p] for p in old_end['hp']} == old_end['hp'], sid
    assert {p: new_end['gold'][p] for p in old_end['gold']} == old_end['gold'], sid
print('season-end snapshots match old board for S1-S5 OK')
# 校验：快照与 data.json computeStandings 季末一致
for s in seasons:
    sid = s['id']
    hp = dict(openings[sid]['hp']); gd = dict(openings[sid]['gold'])
    for r in s['rounds']:
        for (pl, _t, dh, dg) in r['moves']:
            hp[pl] += dh; gd[pl] += dg
    last = f"{sid} {s['rounds'][-1]['code']}"
    # 只比当季名单玩家：早季专属玩家在快照里是冻结值，不在当季累计值里。
    assert {p: snaps[last]['hp'][p] for p in hp} == hp, sid
    assert {p: snaps[last]['gold'][p] for p in gd} == gd, sid
print('snapshots match data.json standings OK')
# 校验：S0 季末
assert snaps['S0 2022-12']['hp']['OAI'] == 135 and snaps['S0 2022-12']['hp']['GOOG'] == 128

# ---- 生成 JS 字面量 ----
def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(', ', ': '))
snaps_js = '{\n' + ',\n'.join(
    f'      "{k}": {js(v)}' for k, v in snaps.items()) + ',\n    }'
order_js = '[' + ', '.join(f'"{x}"' for x in order) + ']'
events_js = '[' + ', '.join(js(e) for e in events) + ']'
oph_js = '{\n' + ',\n'.join(
    f'      "{k}": {js(v)}' for k, v in open_hp.items()) + ',\n    }'
opg_js = '{\n' + ',\n'.join(
    f'      "{k}": {js(v)}' for k, v in open_gold.items()) + ',\n    }'

# ---- 拼入 index.html ----
# 1. REPLAY_SNAPSHOTS + REPLAY_ORDER（从 'const REPLAY_SNAPSHOTS' 到 REPLAY_ORDER 行尾）
i0 = html.index('    const REPLAY_SNAPSHOTS = {')
i1 = html.index('];', html.index('const REPLAY_ORDER = [', i0)) + 2
new_block = ('    const REPLAY_SNAPSHOTS = ' + snaps_js + ';\n'
             '    const REPLAY_ORDER = ' + order_js + ';\n'
             '    // v15: 每轮 1–117 条动作（来源：复盘页 data.json；按月重组后同步，'
             'S0 每轮 1–5 条，S5 2026-11 共 117 条）')
# 上次运行已插过同一行注释时去掉旧行，避免重复（可重复跑）
rest = re.sub(r'^\n    // v15: 每轮 1–117 条动作[^\n]*', '', html[i1:], count=1)
html = html[:i0] + new_block + rest
# 2. ROUND_EVENTS（整行替换）
m = re.search(r'const ROUND_EVENTS = \[\[.*?\]\];\n', html, re.S)
assert m, 'ROUND_EVENTS not found'
html = html[:m.start()] + 'const ROUND_EVENTS = ' + events_js + ';\n' + html[m.end():]
# 3. SEASON_OPEN_HP
m = re.search(r'const SEASON_OPEN_HP = \{.*?\n    \};', html, re.S)
assert m, 'SEASON_OPEN_HP not found'
html = html[:m.start()] + 'const SEASON_OPEN_HP = ' + oph_js + ';' + html[m.end():]
# 4. SEASON_OPEN_GOLD_S1 -> 全季金币开局表；已转过则直接更新 SEASON_OPEN_GOLD（可重复跑）
m = re.search(r'    const SEASON_OPEN_GOLD_S1 = \{[^}]*\};', html)
if m:
    html = (html[:m.start()] +
            '    // v15: 全季开局金币（与 data.json openings 一致；S0 全部为 0）\n'
            '    const SEASON_OPEN_GOLD = ' + opg_js + ';' + html[m.end():])
else:
    m = re.search(r'    const SEASON_OPEN_GOLD = \{.*?\n    \};', html, re.S)
    assert m, 'SEASON_OPEN_GOLD not found'
    html = html[:m.start()] + '    const SEASON_OPEN_GOLD = ' + opg_js + ';' + html[m.end():]
# 5. SEASON_NAMES + S0
html = html.replace(
    'const SEASON_NAMES = { S1: "第一季", S2: "第二季", S3: "第三季", S4: "第四季", S5: "第五季", S6: "第六季" };',
    'const SEASON_NAMES = { S0: "前传", S1: "第一季", S2: "第二季", S3: "第三季", S4: "第四季", S5: "第五季", S6: "第六季" };')
open(B, 'w').write(html)
print('board data written: 94 rounds, 751 moves, snapshots', len(snaps))
print('S0 first snapshot:', snaps['S0 2018-06'])
print('S5 2026-11 snapshot OAI/ANTH/NVDA:', snaps['S5 2026-11']['hp']['OAI'],
      snaps['S5 2026-11']['hp']['ANTH'], snaps['S5 2026-11']['hp']['NVDA'])
