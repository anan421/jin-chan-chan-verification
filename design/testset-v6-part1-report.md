# 第 7 轮 Part 1 报告：题集修补（testset-v6，98 道）

- 工作区：`~/workspace/verification-v1-round7`
- 分支：`loop/vision-1-round7-forward-guidance`（未合 main，未推 GitHub）
- 日期：2026-11-22
- 范围：只做题集修补。不跑实验，不动看板。

**S5 是按 Gu 决定重开的已封口赛季。** 本次修补只改题集，不改任何 S5
动作、血量、金币。动作数仍 558，`data.json` 未动（见 §5）。

## 1. 撤 q79（Grok 4.8）——已确认

- 撤下：q79，S5 5-1，MUSK，kind `spacex_xai`，split B，
  `event_real_date` 20261118，事件“xAI Grok 4.8 软发布”，
  `trace_idx` 511。
- 撤回原因：来源只有马斯克 X 帖文，无 xAI 官方新闻稿、无 API 发布、
  无基准。Gu 已批准按官方公告标准撤回。
- 只撤题，不动 S5 动作：trace_idx 511 的动作
  “xAI Grok 4.8 开始向部分 Bot 用户软发布”仍在 trace 里；
  动作数仍 558；`data.json`、血量、金币一字未动。
- 不重编号：`testset-v6.json` 的 q_id 为 0–78、80–98，q79 空缺。
- 分集不变量已核验：`spacex_xai` 剩 q75(B)、q76(A)、q77(B)、q78(A)，
  两边都有，不用重新分 A/B；全集每种 2 道以上的种类仍两边都有
  （脚本断言通过）。

## 2. 修 23 处日期违规——全部修完

修法（沿用第 6 轮 Part 1 的方法）：`round_date` 改为该题的
`event_real_date`（预测点改到事件当天），每道修过的题带
`round_date_note` 说明。`event_real_date` 一题未改——23 道题的
`event_real_date` 与第 6 轮设计文档
（`design/experiment-vision6-round6.md`）的表逐条对过，一致，
修前已用日历天数核过。天数一律按日历算，绝不用 YYYYMMDD 整数相减
（q40 的旧口径“500 天”是错的，实为 153 天）。
S5 1-1 的题轮次日期仍是逐题的事件日期，没有统一成一个日期。

| q_id | 种类 | 玩家 | 修前 round_date | 修后 round_date (= event_real_date) | 晚的日历天数 | 修后天数 |
|---|---|---|---|---|---|---|
| 40 | financing | MUSK | 20251201 | 20250701 | 153 | 0 |
| 91 | tongyi | ALI | 20250801 | 20250429 | 94 | 0 |
| 47 | gemini | GOOG | 20240501 | 20240215 | 76 | 0 |
| 28 | claude | ANTH | 20250801 | 20250522 | 71 | 0 |
| 27 | claude | ANTH | 20240501 | 20240304 | 58 | 0 |
| 34 | doubao | BYTE | 20250801 | 20250611 | 51 | 0 |
| 48 | gemini | GOOG | 20250801 | 20250617 | 45 | 0 |
| 69 | pangu | HUAWEI | 20250801 | 20250620 | 42 | 0 |
| 41 | financing | ORCL | 20251201 | 20251023 | 39 | 0 |
| 54 | hunyuan | TCE | 20250801 | 20250627 | 35 | 0 |
| 77 | spacex_xai | MUSK | 20240501 | 20240328 | 34 | 0 |
| 98 | wenxin | BIDU | 20250801 | 20250630 | 32 | 0 |
| 76 | spacex_xai | MUSK | 20231201 | 20231104 | 27 | 0 |
| 29 | colossus | MUSK | 20240701 | 20240605 | 26 | 0 |
| 89 | tongyi | ALI | 20240301 | 20240205 | 25 | 0 |
| 78 | spacex_xai | MUSK | 20250801 | 20250709 | 23 | 0 |
| 45 | gemini | GOOG | 20230301 | 20230208 | 21 | 0 |
| 60 | llama | META | 20240501 | 20240418 | 13 | 0 |
| 85 | stargate | ORCL | 20250801 | 20250722 | 10 | 0 |
| 30 | datacenter | BYTE | 20250121 | 20250115 | 6 | 0 |
| 7 | bis_rule | BYTE | 20261118 | 20261116 | 2 | 0 |
| 4 | anthropic_ipo | ANTH | 20261121 | 20261120 | 1 | 0 |
| 88 | tongyi | ALI | 20231201 | 20231130 | 1 | 0 |

注：q7、q30 在第 6 轮已从干净分排除，但日期本身这次已修。
23 道题修后 `round_date` 全部等于 `event_real_date`，晚的天数全部为 0。

## 3. 全集重扫与前缀 / 事实日期核验——0 违规

核验脚本：`runs/testset-v6-part1/audit_v6.py`，复用仓库现有检查规则
（`build_prefixes.py` / `build_testset_v5.py` 的前缀与事实规则；
builder 本身只审计新题，本次对全集 98 道重跑同一规则）。
事实库按 v5 builder 的办法从当前 `data.json` 的 roundEvidence 重新生成，
与旧固定文件比对只允许新增（S5 五轮新增 11 条，与第 6 轮补丁一致）。

- 全集重扫：`round_date` 晚于 `event_real_date` 的题 **0 道**
  （日历天数算，独立重算复核一致）。
- 前缀违规：**0**（98 道题全扫）。
- 事实日期违规：**0**（98 道题全扫；check3 flags 86 条，仅为
  “提到玩家 / 日期等于事件日期”的提示，与 v5 同类审计同性质）。
- `trace_idx` 动作比对：有 `trace_idx` 的 53 道题动作全部吻合。
- 构建器 `build_testset_v6.py` 的断言全部通过：98 道、A 50 / B 48、
  无重编号、除 23 道题的 `round_date` / `round_date_note` 外其余字段
  与 v5 一字不差。

## 4. S5 重验——通过

- 命令：`./run.sh`（工作区 `~/workspace/verification-v1-round7`，
  无 `--claims`、无 `--predict`，与第 6 轮重验同一口径）。
- **退出码：0**。运行目录：`runs/2026-11-22_064252/`。
- 合并报告 overall **pass**：快速检查器 pass（通过 3，失败 0，
  数据不足 0；覆盖 558 条动作 / 18 名玩家 / 5 个赛季 / 90 个排名 /
  12 条不变量）；Lean 构建退出 0；agent gate 跳过（无 claims）。
- trace 是在工作区内从已入库的 `raw-trace-real.json` 用
  `python3 extract.py raw-trace-real.json` 重新生成的（工作区
  `traces/` 属 gitignored，此前不存在；main 仓库的
  `trace-latest.json` 已走样，不采用）。再生 trace 为 558 条动作，
  raw sha 与第 6 轮一致；文件 sha 与第 6 轮记录不同只因
  `meta.extracted_at` 时间戳不同（本次 2026-11-22T06:41:38Z），
  内容无别的变化。

## 5. 页面 data.json 不用同步——已确认

日期修补只改题集，不改 `data.json`。`data.json` 的 sha256 在任务
前后一致：`78c35f31837f3160918d79d1b756cb7b7ff97e874bce509f83d0fae7d1584d3b`。
live 模型同样一字未动：`rules/payoff-model.json`
`d354bd86…`、`predict.py` `d8fcb4b9…`、`backtest.py` `7911c164…`，
任务前后哈希一致。无备份、无同步需要。

## 6. 池文件更新——工作区那份

工作区 `s6-pending-pool.json`（只改工作区这份；main 仓库
`~/workspace/verification/s6-pending-pool.json` 仍为
testset_n 99 / gap 41，未动，main 同步由上层定）。

- meta：`testset_n` 99 → **98**；`gap_to_140` 41 → **42**；
  `updated` 2026-11-22。
- note 追加一句：“Round-7 Part 1 2026-11-22：撤 q79（Grok 4.8，
  无官方公告）+ 修 23 处日期违规（最长 153 天 q40），S5 重验通过
  （./run.sh exit 0, runs/2026-11-22_064252/）；testset-v6.json 98 道题
  （A 50 / B 48）。”
- 候选列表未动：candidates 0，missed_s5 0，kind_gap 4，rejected 22。

## 7. 交付物（本分支）

- `testset-v6.json`（98 道，q79 已撤，23 处日期已修，JSON 有效；
  meta：name 注明 testset-v6、n=98、A 50 / B 48、gap_to_140=42、
  撤回原因与修补说明）。
- `build_testset_v6.py`（可复现的构建器：从 v5 生成 v6，含全部断言）。
- `s6-pending-pool.json`（工作区 meta 已更新）。
- `runs/testset-v6-part1/`（gitignored 证据：`audit_v6.py`、
  `prefixes-v6.json`、`prefix-audit-v6.json`、
  `facts-roundEvidence-v6.json`）。
- 本报告 `design/testset-v6-part1-report.md`。
- `runs/2026-11-22_064252/`（S5 重验运行目录，gitignored）。

## 8. 已知遗留（本次范围外，如实记录）

1. 6 道题的 trace `semantic_kind` 与题 kind 不同，均为 v5 已有状态，
   本次未动：q22（unknown/chatgpt）、q32（unknown/datacenter）、
   q38（unknown/financing）、q39（unknown/financing）、
   q55（unknown/invest_plan）、q89（blackwell/tongyi）。
   动作文本全部吻合；trace 的语义分类本就只覆盖 219/558 条，
   仓库 builder 也只对新题断言 kind 一致。
2. 53 道题缺 `old_q_idx` 字段，同样是 v5 已有状态（v5 为 54 道，
   含已撤的 q79）；其余字段完整。本次未补。
3. 45 道题无 `trace_idx`，v5 已有状态，未动。
4. 问题文件与打分脚本（`build_questions_v6.py`、`score_v6.py` 等）
   仍指向 testset-v5，是第 7 轮实验部分的待办，不属 Part 1。
5. 工作区另有并行工作产生的未入库文件
   （`design/experiment-vision7-round7.md`、
   `design/predictor-plan-vision7-round7.md`），本次提交不含它们。
