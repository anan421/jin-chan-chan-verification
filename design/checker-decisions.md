# 检查器决策记录（checker decisions）

本文记录 `check.py` 里有意偏离“最直白读法”的检查口径：每处写清改了
什么、为什么、旧口径是什么。静默改口径是不允许的；任何一处口径变化
都必须先记在这里，再改代码。Lean 层按同一语义合同修，两层口径必须
一致（Lean 工人另行记录）。

## 决策 1：C5 跨度规则（round-span rule）——2026-11-21，Gu 已批准

### 背景

首份真实合并报告 `runs/2026-11-21_115719/merged-report.md` 总体 fail，
其中 C5×18：S5 5-1 全 18 名玩家的 recorded rules_version 均为
RV-2026.2，检查器期望 RV-2026.1（“rule in effect on 20261118”）。

根因：该轮日期为「2026 年 11 月 18–19 日」，转换取最早一天 20261118
当 move 日期；当天在效 RV-2026.1；但该轮横跨了规则变更日，页面按
轮内后半段生效的版本记 roundRV 为 RV-2026.2。单日日期不能代表整轮，
旧口径把轮内后半段才生效的正确版本判为错。

### 前置验证：trace 里没有字段能表达轮次跨度

修前已验证 `traces/trace-2026-11-21.json`：moves 只有单日 `date`
（S5 5-1 全为 20261118）；seasons 只有赛季级 `start_date` /
`end_date`（S5 为 20251201–20261121），不能表达轮内跨度；全 trace
扫描无任何 span 字段。因此轮次跨度必须以外挂文件记录，不改 trace
schema，不改转换器。

### 旧口径

recorded rules_version 必须等于按 move 单日日期 D 解析出的 base
（全局）规则 `resolve_rules(rules, D)` 的 rule_id，否则 fail
`round_rv`。

### 新口径（全文）

move 的 recorded rules_version V 接受，当且仅当：

1. V 是 move 日期 D 当天在效的 base（全局）规则；或
2. V 是一条 base 规则，且其生效窗口与该轮跨度 [D, spanEnd] 有重叠。

其中：

- spanEnd 取自 `rules/round-spans.json`，key 为 (season, round_label)；
  无条目的轮次 spanEnd = D，即无跨度。
- 规则窗口为 [effective_from, effective_to)，effective_to 为空表示
  开放；重叠指 effective_from ≤ spanEnd 且（effective_to 为空或
  effective_to > D）。
- player 专属 overlay 规则永不计入：V 必须是 base（全局）规则。
- 禁令种类检查与日期检查仍用 D，不变；C2/C3 账本的规则解析仍用 D，
  不变。本决策只改 ROUND_RV 的接受条件。

### 5-1 的依据

- 页面轮次日期原文：「2026 年 11 月 18–19 日」。
- 转换取最早一天 20261118，当天在效 RV-2026.1；页面 roundRV 记为
  RV-2026.2。
- RV-2026.2 于 2026-11-19 生效（《联邦公报》文号 2026-23529，印刷页
  91 FR 74970），其窗口 [20261119, ∞) 与跨度 [20261118, 20261119]
  在 20261119 处重叠，故接受。
- 轮次日期未改为单日；RV-2026.2 生效日未提前。

### 实现（check.py）

- 新增 `load_round_spans()` / `ROUND_SPANS` / `round_span_end()` /
  `rule_window_overlaps()`：span 文件按 `check.py` 所在目录解析
  （`rules/round-spans.json`），缺失或不可读时退回旧严格口径
  （无跨度）。
- C5 段 round_rv 分支：recorded ≠ base(D) 时，再按重叠分支判定；
  仍不接受则 fail，note 记轮次跨度。
- 防御性细节（合同未明说、与合同一致）：spanEnd 早于 D 时不缩小
  跨度（取 max(D, spanEnd)）。
- `rules/round-spans.json`（version 1）格式已合用，未改；其中 S5
  5-1 一条：span [20261118, 20261119]，附上款依据。

### 适用范围说明

span 文件按 (season, round_label) 查，因此同样作用于同 key 的
fixture 轮次。已核对：两份 fixture 中 S5 5-1 的 recorded 版本本来
就等于 base(D)，无一处是靠重叠分支新通过的；broken fixture 失败
集修前修后逐项相同（见下回归）。

## 决策 2：C6 不同卡计数规则（distinct-card counting）——2026-11-21，Gu 已批准

### 背景

首份真实合并报告 C6×1：`pool_cost_5_overheld`，期望 ≤ 10，实际 11。

根因：星门计划 1 张卡被 3 名玩家持有（key_cards：shared=True，
holders=[1,9,17]，即 OAI、ORCL、SFTB）；检查器按持有数计，11 条
cost 5 holdings 对 10 张池子。同一张共享卡被多人持有不是多张卡。

### 旧口径

每费池子计数按 holdings 逐条计数（`Counter` 对每条 holding 加 1）。

### 新口径（全文）

- 共享卡（key_cards 里 shared=true）按 (cost, card) 去重计 1 张，
  无论几名玩家持有；
- 非共享卡每条持有计 1，与旧口径相同；
- key_cards 的“多持有人须共享”检查（holders>1 且 shared=false
  则 fail）不变。

### 本例

cost 5 的 holdings 共 11 条、不同卡 9 张；新口径计 9 ≤ 10，通过。

### 定界：合成检查不动

逐卡加权合成检查（synthesis_overpool）不改。理由：它当前不 fail，
改它是超范围；它量的是星级合成加权占用（`sum(3^(stars-1) * n)`），
与“池子被几张不同卡占用”是另一回事，修 C6 计数不牵连它。

### 实现（check.py）

C6 段池子计数：先从 key_cards 建共享键集合 `{(cost, card)}`，再对
holdings 计数——共享键首次出现计 1、后续跳过；非共享键每条计 1。
其余 C6 检查（共享多持有人、synthesis_overpool）原文不动。

## 回归验证（2026-11-21 晚，修后跑）

- 真实 trace `traces/trace-2026-11-21.json`：verdict=pass，passed=3、
  failures=0、gaps=0，退出码 0。18 处 C5 与 1 处 C6 失败全部消失，
  无新失败（修前：fail，passed=3、failures=19）。
- ok fixture `fixtures/trace-fixture-ok.json`：仍 pass（passed=3、
  failures=0、gaps=0），退出码 0。
- broken fixture `fixtures/trace-fixture-broken.json`：仍 fail，
  failures=10、gaps=0，退出码 1，失败集与修前逐项相同（C2×3、C3、
  C4、C5×2、C6、C10、C11 全在）。被注入的日期错误（C5 S4 4-1
  date_before_true，20250101 < 20250120）仍被抓到；被注入的卡池
  超持（C6，12 条，其中 H100 与 R1 各 2 条、均为非共享卡）新口径
  下仍计 12 > 10，仍 fail。修法没有掩盖 broken fixture 的错误。
