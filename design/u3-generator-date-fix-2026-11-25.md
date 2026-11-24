# U3 修复报告：生成器事实日期问题

日期：2026-11-25。范围：只改生成器指令与新检查脚本。不改题集。不改冻结赛季。不改历史分数。不改历史预测文件。

## 结论

- 生成器已修。第 12 轮起，汇总事实不再盖轮次日期戳。月级日期写 YYYYMM。年 级日期写 YYYY。
- 历史 39 条违规仍在原文件里。不能重生成。原因见第 5 节。清单见附录。
- 新检查脚本 `check_fact_dates.py` 已验证：基线 39 条与审计逐条一致。第 11 轮另查出 41 条同类变形与 3 条格式错误。

## 1. 生成器位置

没有写事实的代码生成器。预测文件由预测员（大模型）按指令文件写出。生成器就是这三份指令文件：

| 文件 | 作用 |
| --- | --- |
| `design/search-boundary-tightened.md` | 方法文件。查资料规则。第 12 轮沿用。 |
| `design/predictor-plan-baseline-retest.md` | 基线重测预测员计划。 |
| `design/predictor-plan-vision11-round11.md` | 第 11 轮对照组预测员计划。 |
| `design/experiment-baseline-retest-v7.md` | 基线重测实验设计。纪律条目。 |

题目文件生成器 `build_questions_baseline_v7.py` 不是成因。它把历史过滤为严格早于轮次日期的动作。它给出的 `player_history_counts` 本身不带日期。预测员没有日期可填，才填轮次日期。

## 2. 缺陷成因

### 2.1 盖轮次日期戳

旧指令要求每条事实都有日期，且日期必须早于轮次日期。但汇总事实没有自身日期。汇总事实指三类：玩家历史汇总（次数统计、最常做种类）、无历史记录、最近动作种类。

题目文件只给统计结果，不给统计对应的日期。`player_last3` 的每条记录有真实日期，但汇总统计没有。预测员手头唯一的日期就是轮次日期。预测员填了轮次日期。39 条基线违规全是这类事实。没有一条严格晚于轮次日期。没有一条含事件内容。不是泄题。

分布：C1 7 条，C2 4 条，C3 28 条。C3 集中在 S4 1-3 与 S5/S6 新题。15 条在猜中记录上。

### 2.2 月级日期拼凑确切日

旧指令已有“日期只有月份时写 YYYYMM，不拼凑确切日”一句。但没有检查执行。审计把月份日期按当月 1 日算。只要拼凑出的确切日早于轮次日期，审计就查不出。规则存在，但不可验证。

逐条拼凑无法从输出文件证实。输出文件不保留事实来源。检查脚本只能标出可疑项。基线 5 条可疑，第 11 轮 10 条可疑。抽查显示多数可疑项是真实确切日（如 ChatGPT 2022-11-30 上线）。可疑项只作人工复核提醒，不计入违规。

## 3. 改了哪里

### 3.1 `design/search-boundary-tightened.md`（主修复，第 12 轮沿用）

新增第 1.1 节：汇总事实没有自身日期，`date` 写 `null`。不写轮次日期。不用轮次日期填充。汇总事实引用某次具体动作时，写那次动作的真实日期。该日期必须严格早于轮次日期。`player_last3` 每条记录自带真实日期，用那个日期。

新增第 1.2 节：日期只有月份时写 YYYYMM（6 位数字）。日期只有年份时写 YYYY（4 位数字）。不拼凑月份与确切日。完整日期写 YYYYMMDD 或 YYYY-MM-DD。完整日期必须严格早于轮次日期。日期等于轮次日期即违规。

### 3.2 两份预测员计划

`predictor-plan-baseline-retest.md` 与 `predictor-plan-vision11-round11.md`：`facts` 条目加汇总事实写 `null` 的写法。纪律条目加年级日期写 YYYY 与汇总事实写 `null`。

### 3.3 `design/experiment-baseline-retest-v7.md`

纪律条目加年级日期写 YYYY 与汇总事实写 `null`。

### 3.4 新增 `check_fact_dates.py`（检查脚本）

位置：`~/workspace/verification-v1-round11/check_fact_dates.py`。用法：`python3 check_fact_dates.py <预测目录>`。违规时退出码为 1。输出为 JSON。

检查规则：

- `date` 为 `null` 且内容是汇总事实，通过。
- `date` 为 `null` 且内容不是汇总事实，记违规 MISSING_DATE。
- YYYYMM 按当月 1 日算。必须早于轮次日期。
- YYYY 记警告 YEAR_ONLY_UNJUDGEABLE，不计入违规。沿用审计口径。
- 完整日期等于轮次日期，记违规 DATE_EQUALS_ROUND_DATE。晚于轮次日期，记违规 DATE_AFTER_ROUND_DATE。
- 日期带“前”或“前累计”后缀且数值等于轮次日期，记违规 ROUND_DATE_STAMPED_SUFFIX。旧审计未计这类。第 11 轮有 41 条。
- 内容只写月份、日期却带非 1 日的确切日，记警告 MONTH_FABRICATION_SUSPECT。只作人工复核提醒，不计入违规。
- 事实文本兼容 `content` 与 `text` 两个键。C2 的 S4 文件有 67 条事实用 `text` 键。
- `--self-test` 跑夹具：修正格式通过，盖戳事实被抓出。

## 4. 验证结果

| 检查 | 结果 |
| --- | --- |
| 自测 `--self-test` | 通过。修正格式 0 违规。盖戳事实被抓出。 |
| 基线重测（95 个文件，1457 条事实） | 违规 39 条。全是 DATE_EQUALS_ROUND_DATE。无晚于轮次日期的事实。与审计 `audit-baseline-v7.json` 的 39 条逐条一致（批次、题号、事实文本全对）。 |
| 第 11 轮（93 个文件，1214 条事实） | 违规 128 条：DATE_EQUALS_ROUND_DATE 84 条，与审计一致；ROUND_DATE_STAMPED_SUFFIX 41 条，是旧审计未计的同类变形；BAD_FORMAT 3 条，见第 5 节。 |
| 历史分数 | 未动。未改任何预测文件。未改题集。未改打分脚本。 |

## 5. 剩余未清的项与原因

### 5.1 基线 39 条违规仍在历史文件里

不能重生成。预测文件由预测员在 2026-11-22 跑出。重跑会产出不同的预测。分数会变。冻结赛季与历史分数不许改。手工改预测文件的日期等于改写历史。没有改。清单见附录。修复只对第 12 轮及以后生效。

### 5.2 第 11 轮 128 条违规仍在历史文件里

同上。84 条干净盖戳与审计一致。41 条“前/前累计”后缀变形是新规则下新增的违规类。旧审计未计这类，因为后缀文字写“之前”。新规则要求汇总事实写 `null`，所以这类仍算违规。3 条 BAD_FORMAT 是日期字段无法解析：

| 文件 | 题号 | 日期原文 | 事实 |
| --- | --- | --- | --- |
| predictions-D3-S4-1-1.json | q80 | 2024年内，轮次日期之前 | MSFT 资本开支趋势 115→140→190 亿美元连涨 |
| predictions-D3-S4-1-2.json | q56 | 20240901, 20241201, 20250120 | ALI 最近三次动作均为 tongyi |
| predictions-D3-S4-1-3.json | q189 | 20250120, 20241201 | DPSK 最近一次动作 r1，前一次 v3 |

这 3 条的事实内容是汇总或趋势。按新规则应写 `null`，或引用具体动作时写该动作的真实日期。

### 5.3 年级日期 11 条未判定

基线 10 条，第 11 轮 1 条。日期只有年份，无法判定是否早于轮次日期。沿用审计口径，不计入违规。新规则要求以后只写年份时写 YYYY，并由检查脚本标出警告。

### 5.4 月级拼凑可疑项 15 条未定论

基线 5 条，第 11 轮 10 条。只作人工复核提醒。输出文件无来源，无法逐条证实是否拼凑。抽查显示多数是真实确切日。不计入违规。

## 附录：基线 39 条违规清单（未清，历史文件原样保留）

| 批次 | 题号 | 事实日期 | 轮次日期 | 事实内容 | 文件 |
| --- | --- | --- | --- | --- | --- |
| C1 | q99 | 20250127 | 20250127 | 谷歌玩家历史：gemini 3 次，open_source 1 次，capex 1 次，blackwell 1 次，最常做 gemini | predictions-C1-S4-1-3.json |
| C1 | q110 | 20250127 | 20250127 | Manus 玩家历史为空，hp_start 与 gold_start 为 null，没有 last3 记录 | predictions-C1-S4-1-3.json |
| C1 | q121 | 20250127 | 20250127 | Cursor 玩家历史为空，hp_start 与 gold_start 为 null，没有 last3 记录 | predictions-C1-S4-1-3.json |
| C1 | q137 | 20250127 | 20250127 | 谷歌玩家历史：gemini 3 次，open_source 1 次，capex 1 次，blackwell 1 次，最常做 gemini | predictions-C1-S4-1-3.json |
| C1 | q155 | 20250127 | 20250127 | CoreWeave 玩家历史为空，hp_start 与 gold_start 为 null，没有 last3 记录 | predictions-C1-S4-1-3.json |
| C1 | q195 | 20250127 | 20250127 | Karpathy 玩家历史为空，hp_start 与 gold_start 为 null，没有 last3 记录 | predictions-C1-S4-1-3.json |
| C1 | q210 | 20250127 | 20250127 | 谷歌玩家历史：gemini 3 次，open_source 1 次，capex 1 次，blackwell 1 次，最常做 gemini | predictions-C1-S4-1-3.json |
| C2 | q110 | 20250127 | 20250127 | MANUS 无历史记录（hp/gold 为 null，player_history_counts 为空），轮次日期之前无公开动作线可循。 | predictions-C2-S4-1-3.json |
| C2 | q121 | 20250127 | 20250127 | CURSOR 无历史记录（hp/gold 为 null），题目文件未给动作线。 | predictions-C2-S4-1-3.json |
| C2 | q155 | 20250127 | 20250127 | CRWV 无历史记录（hp/gold 为 null），题目文件未给动作线。 | predictions-C2-S4-1-3.json |
| C2 | q195 | 20250127 | 20250127 | KARPATHY 无历史记录（hp/gold 为 null，player_history_counts 为空），轮次日期之前无公开动作线可循。 | predictions-C2-S4-1-3.json |
| C3 | q194 | 20240301 | 20240301 | 本题玩家COGNITION无历史记录（hp_start与gold_start均为null，player_history_counts为空），轮次日期前无可查的公开动作 | predictions-C3-S3-2-1.json |
| C3 | q92 | 20241201 | 20241201 | DeepSeek历史动作有开源1次，最近一轮为开源 | predictions-C3-S3-6-1.json |
| C3 | q82 | 20250121 | 20250121 | OpenAI 历史动作：msft_invest 2 次、chatgpt 2 次；算力需求是主线 | predictions-C3-S4-1-2.json |
| C3 | q99 | 20250127 | 20250127 | 谷歌历史动作中 gemini 出现 3 次，为最常做的种类 | predictions-C3-S4-1-3.json |
| C3 | q99 | 20250127 | 20250127 | 谷歌历史动作：open_source 1 次、capex 1 次、blackwell 1 次，模型线最集中 | predictions-C3-S4-1-3.json |
| C3 | q137 | 20250127 | 20250127 | 谷歌历史动作中 gemini 出现 3 次，为最常做的种类 | predictions-C3-S4-1-3.json |
| C3 | q210 | 20250127 | 20250127 | 谷歌历史动作中 capex 出现 1 次；gemini 3 次为最常做 | predictions-C3-S4-1-3.json |
| C3 | q177 | 2025-12-01 | 20251201 | 美光无历史记录，hp_start 与 gold_start 均为 null，player_last3 为空 | predictions-C3-S4-5-1.json |
| C3 | q205 | 2025-12-01 | 20251201 | DeepSeek 历史动作：financing 1 次、open_source 1 次、v3 1 次、r1 1 次 | predictions-C3-S4-5-1.json |
| C3 | q205 | 2025-12-01 | 20251201 | DeepSeek 最近一次动作种类为 r1 | predictions-C3-S4-5-1.json |
| C3 | q120 | 2026-01-01 | 20260101 | OpenClaw 无历史记录，hp_start 与 gold_start 均为 null，player_last3 为空 | predictions-C3-S5-1-1.json |
| C3 | q167 | 2026-01-01 | 20260101 | Kimi 无历史记录，hp_start 与 gold_start 均为 null，player_last3 为空 | predictions-C3-S5-1-1.json |
| C3 | q168 | 2026-01-01 | 20260101 | Kimi 无历史记录，hp_start 与 gold_start 均为 null，player_last3 为空 | predictions-C3-S5-1-1.json |
| C3 | q178 | 2026-01-01 | 20260101 | 三星无历史记录，hp_start 与 gold_start 均为 null，player_last3 为空 | predictions-C3-S5-1-1.json |
| C3 | q179 | 2026-01-01 | 20260101 | 三星无历史记录，hp_start 与 gold_start 均为 null，player_last3 为空 | predictions-C3-S5-1-1.json |
| C3 | q206 | 2026-01-01 | 20260101 | DeepSeek 历史动作：financing 1 次、open_source 1 次、v3 1 次、r1 1 次 | predictions-C3-S5-1-1.json |
| C3 | q206 | 2026-01-01 | 20260101 | DeepSeek 最近一次动作种类为 r1 | predictions-C3-S5-1-1.json |
| C3 | q207 | 2026-01-01 | 20260101 | DeepSeek 历史动作：financing 1 次、open_source 1 次、v3 1 次、r1 1 次 | predictions-C3-S5-1-1.json |
| C3 | q207 | 2026-01-01 | 20260101 | DeepSeek 最近一次动作种类为 r1 | predictions-C3-S5-1-1.json |
| C3 | q208 | 2026-01-01 | 20260101 | DeepSeek 历史动作：financing 1 次、open_source 1 次、v3 1 次、r1 1 次 | predictions-C3-S5-1-1.json |
| C3 | q208 | 2026-01-01 | 20260101 | DeepSeek 最近一次动作种类为 r1 | predictions-C3-S5-1-1.json |
| C3 | q19 | 2026-10-06 | 20261006 | 亚马逊历史动作：open_source 2 次、capex 1 次、financing 1 次、r1 1 次 | predictions-C3-S5-2-1.json |
| C3 | q169 | 2026-10-06 | 20261006 | Kimi 无历史记录，hp_start 与 gold_start 均为 null，player_last3 为空 | predictions-C3-S5-2-1.json |
| C3 | q6 | 2026-11-05 | 20261105 | 台积电历史动作：open_source 1 次、capex 1 次、blackwell 1 次、r1 1 次、stargate 1 次 | predictions-C3-S5-3-2.json |
| C3 | q6 | 2026-11-05 | 20261105 | 台积电 player_last3 为空，无最近动作记录 | predictions-C3-S5-3-2.json |
| C3 | q24 | 2026-11-12 | 20261112 | OpenAI 历史动作：msft_invest 3 次、chatgpt 2 次、capex 2 次、financing 1 次、stargate 1 次、energy 1 次、llama 1 次 | predictions-C3-S5-4-1.json |
| C3 | q50 | 2026-11-12 | 20261112 | 英伟达历史动作：open_source 1 次、blackwell 1 次、stargate 1 次、energy 1 次 | predictions-C3-S5-4-1.json |
| C3 | q49 | 2026-11-18 | 20261118 | 谷歌历史动作：gemini 4 次、open_source 1 次、capex 1 次、blackwell 1 次 | predictions-C3-S5-5-1.json |
