# 第 14 轮 numeric_history 独立复核报告

日期：2026-11-25。复核人是独立第二人，未参与编译。只复核，不跑预测，不改方法文件，不改题集，不提交。

## 结论先行

- 逐值复核 42 项：通过 40 项，删除 2 项。
- 删除：q124 的 500（百万周活，20250609），q127 的 10（10 亿美元年化收入，20250609）。
- 删除原因：跨题泄漏。两项都是 2025-06-09 CNBC 同日披露，分别是 q122 与 q123 的事件本身。预测员 P4 同时读 S4-3-2 与 S4-4-1，同时答 q122、q123、q124、q127。P4 在 q124、q127 的字段里直接看到 q122、q123 的答案。
- 删后每组剩 40 个值。q124 剩 2 个值（300、400）。q127 剩 2 个值（3.4、5.5）。两题仍满足规则 N 的不少于 2 个数值要求。总数 40 仍在设计要求的约 30 至 50 个值之内。
- 两处重点项结论：q121 的 $65M 留下。Sacra 页面写明 Published Nov 27th, 2024，早于预测点 2025-01-27。q129 的两项都留下。$500M 的 Series F 公告是 Anthropic 官方 2025-09-02 公告，原文写 Claude Code run-rate revenue over $500M。$1B 的披露是 Anthropic 官方 2025-12-03 收购 Bun 公告，原文写 11 月 Claude Code 达 $1B run-rate revenue。字段日期 202512 是公布月，数值期是 2025 年 11 月。两项公布日都早于 2026-01-01。
- 删后重扫：numeric_history 字段全文扫描，主项（第 1–3 项）0 命中。第 5 项 6 处长公共子串，与搭建报告的 6 处相同，都是通用词重叠，不是泄漏。
- 删后重核：两组各 31 文件、215 题，round_date 与 testset-v7 一致，forward_guidance 0 道，numeric_history 仍在 14 道题上，两组 diff -r 逐字节一致。核对脚本全部通过。

## 复核方法

- 核对对象是题目文件里的实际字段：`runs/round14-weak-repair-2-2026-11-25/questions-control/` 与 `questions-experiment/`。
- 事件数字以 testset-v7.json 为准。14 道题的事件数字：q121 500（百万美元 ARR），q122 500（百万周活），q123 10（十亿美元年化收入），q124 800（百万周活），q125 1000（百万美元 ARR），q126 9（十亿美元），q127 20（十亿美元），q128 14（十亿美元），q129 2.5（十亿美元 Claude Code run rate），q130 750（百万月活），q131 30（十亿美元），q132 47（十亿美元），q133 40（十亿美元），q213 4（万亿美元市值）。
- 每项查四条：日期严格早于本题 round_date；数值不等于本题事件数字；来源是轮次日期之前已公布的数字（公司财报、电话会、官方公告、或报道已公布数字的 reputable 媒体），不是事件本身的报道，不是预测点之后的转述；跨题泄漏。
- 跨题泄漏的判定口径：数值等于另一道题的事件数字时，看看到该值的预测员是否也答那道题。预测员分派按搭建报告分派表：P1 答 S1、S2；P2 答 S3；P3 答 S4 1-1、1-2、1-3；P4 答 S4 3-2、4-1；P5 答 S4 5-1 与 S5 全部。同一预测员批内（不只同一轮次文件）的等值才算泄漏。只看裸数字相等不算，须玩家、单位、指标口径也相同才算泄漏。版本号、年份、其他指标里的同名数字不算。
- 来源逐项上网核对。重点项读了原文页面（Sacra 页面、Anthropic 官方 Series F 公告、Anthropic 官方收购 Bun 公告、Cursor 官方博客 Series B 文章、TechCrunch 2024-12-19 与 2025-06-05 报道）。

## 42 项逐值 verdict 表

日期栏写字段里的 date。round_date 栏写本题预测点。

### q121（CURSOR，round_date 20250127；事件数字 500，百万美元 ARR）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 4 | USD million ARR | 202404 | TechCrunch, 2024-12-19, Series B report: ARR $4M in April 2024 | 通过 | 日期 202404 与公布日 2024-12-19 都早于 20250127。4 ≠ 500。TechCrunch 原文写 revenue has grown from $4M ARR in April。来源不是事件报道。跨题：裸数字 4 与 q213 事件数字 4 相同，但玩家、单位、指标都不同（NVDA 万亿美元市值），P3 也不答 q213。不是泄漏。 |
| 48 | USD million ARR | 202410 | TechCrunch, 2024-12-19, Series B report: $4M a month in October 2024, i.e. $48M ARR | 通过 | 日期 202410 与公布日 2024-12-19 都早于 20250127。48 ≠ 500。TechCrunch 原文写 ARR in October was $48M。来源不是事件报道。无跨题等值。 |
| 65 | USD million ARR | 202411 | Sacra estimate, November 2024: $65M ARR in November 2024 | 通过 | Sacra 页面原文写 Published Nov 27th, 2024，写 Sacra estimates that Cursor hit $65M ARR in November 2024。公布日 2024-11-27 早于 20250127。65 ≠ 500。来源是轮次前已公布的估计，不是事件报道。跨题：裸数字 65 与 q101 事件数字 65 相同，但 q101 是 OpenAI 收 io 的 $65 亿（65 亿美元），玩家、单位、指标都不同。不是泄漏。 |

### q122（OAI，round_date 20250601；事件数字 500，百万周活）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 200 | million weekly active users | 202408 | OpenAI, August 2024: 200M weekly active users | 通过 | 202408 早于 20250601。200 ≠ 500。OpenAI 2024 年 8 月披露，TechCrunch 2025-03-06 a16z 报道复核同一序列（100M 2023 年 11 月至 200M 2024 年 8 月）。来源不是事件报道。无同指标跨题等值。 |
| 300 | million weekly active users | 202412 | OpenAI, December 2024: 300M weekly active users | 通过 | 202412 早于 20250601。300 ≠ 500。TechCrunch 2025-02-20 写 OpenAI only had 300M users in December 2024。来源不是事件报道。裸数字 300 与 q187（英伟达对 OpenAI 投资 $300 亿）相同，但指标不同。不是泄漏。 |
| 400 | million weekly active users | 202502 | OpenAI via CNBC/TechCrunch, February 2025: 400M weekly active users | 通过 | 202502 早于 20250601。400 ≠ 500。TechCrunch 2025-02-20 直接报道（OpenAI told CNBC 400M weekly active users），TechCrunch 2025-03-06 复核同一数字。字段写 TechCrunch 2025-03-06，公布日以 2025-02-20 为准，两日都早于 20250601。来源不是事件报道。无同指标跨题等值。 |

### q123（OAI，round_date 20250601；事件数字 10，十亿美元年化收入）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 1.6 | USD billion annualized revenue | 202312 | The Information, reported June 2024: annualized revenue $1.6B in late 2023 | 通过 | 202312 与报道日 2024 年 6 月都早于 20250601。1.6 ≠ 10。The Information 2024-06-12 报道写 annualized revenue was $1.6B around the end of last year。来源不是事件报道。裸数字 1.6 与 q34（Doubao-Seed-1.6 版本号）相同，但不是指标数字。不是泄漏。 |
| 2 | USD billion annualized revenue | 202402 | Financial Times, February 2024: annualized revenue reached $2B | 通过 | 202402 早于 20250601。2 ≠ 10。FT 2024 年 2 月报道的数值期是 2023 年 12 月（$2B+ annualized run rate）。数值期与公布月都早于 20250601。来源不是事件报道。无同指标跨题等值。 |
| 3.4 | USD billion annualized revenue | 20240612 | The Information, June 12 2024: annualized revenue $3.4B | 通过 | 20240612 早于 20250601。3.4 ≠ 10。The Information 2024-06-12 报道，Bloomberg 同日引述。来源不是事件报道。无同指标跨题等值。 |

### q213（NVDA，round_date 20250601；事件数字 4，万亿美元市值）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 2 | USD trillion market capitalization | 20240223 | Market cap history: crossed $2T on February 23 2024 | 通过 | 20240223 早于 20250601。2 ≠ 4。市值史写 $2T Feb 23 2024。多家报道复核同一日期。来源不是事件报道。无同指标跨题等值。 |
| 3 | USD trillion market capitalization | 20240605 | Market cap history: crossed $3T on June 5 2024 | 通过 | 20240605 早于 20250601。3 ≠ 4。2024-06-05 收盘市值 $3.019T，CNBC 当日报道。来源不是事件报道。无同指标跨题等值。 |
| 3.5 | USD trillion market capitalization | 202410 | Zacks, October 23 2024: closed above $3.5T market capitalization in October 2024 | 通过 | 202410（整个 10 月）早于 20250601。3.5 ≠ 4。2024 年 10 月市值破 $3.5T 有同期报道佐证（2024-10-26 报道写周五市值 $3.53T）。来源不是事件报道。无同指标跨题等值。 |

### q124（OAI，round_date 20250801；事件数字 800，百万周活）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 300 | million weekly active users | 202412 | OpenAI, December 2024: 300M weekly active users | 通过 | 202412 早于 20250801。300 ≠ 800。来源同 q122 的 300。无同指标跨题等值。 |
| 400 | million weekly active users | 202502 | OpenAI via CNBC/TechCrunch, February 2025: 400M weekly active users | 通过 | 202502 早于 20250801。400 ≠ 800。来源同 q122 的 400。无同指标跨题等值。 |
| 500 | million weekly active users | 20250609 | OpenAI via CNBC, June 9 2025: weekly active users 500M | 不过，删除 | 日期与来源本身都通过（20250609 早于 20250801，500 ≠ 800，CNBC 2025-06-09 披露属实）。跨题泄漏不过：该值就是 q122 的事件本身。q122 事件名 ChatGPT 周活达 5 亿，事件数字 500，同一玩家 OAI，同一单位百万周活，同一披露日 2025-06-09，同一来源 CNBC。P4 答 q122（S4-3-2），又读 q124 的字段（S4-4-1）。P4 在本题字段里直接看到 q122 的答案。删除。 |

### q125（CURSOR，round_date 20250801；事件数字 1000，百万美元 ARR）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 100 | USD million ARR | 20250116 | Anysphere official blog, January 16 2025 (Series B): recurring revenue exceeded $100M | 通过 | 20250116 早于 20250801。100 ≠ 1000。Cursor 官方博客 Series B 文章原文写 having exceeded $100m in recurring revenue，Published 2025-01-16。官方公告。来源不是事件报道。无同指标跨题等值。 |
| 300 | USD million ARR | 202504 | TechCrunch, June 5 2025: ARR $300M in mid-April 2025 | 通过 | 数值期 202504 与公布日 2025-06-05 都早于 20250801。300 ≠ 1000。TechCrunch 2025-06-05 写 60% increase from the $300M we reported in mid-April。来源不是事件报道。无同指标跨题等值。 |
| 500 | USD million ARR | 20250605 | TechCrunch, June 5 2025: ARR topped $500M by June 2025 | 通过 | 20250605 早于 20250801。500 ≠ 1000。TechCrunch 2025-06-05 写 surpassed $500M in ARR。来源不是事件报道。跨题：该值等于 q121 的事件数字 500（同一玩家 CURSOR，同一单位百万美元 ARR）。但不是泄漏。q121 由 P3 答（S4 1-1、1-2、1-3），P3 不读 S4-4-1。读 S4-4-1 的 P4 不答 q121。没有一位预测员同时看到该值又答 q121。搭建报告的说明成立。保留。 |

### q126（ANTH，round_date 20250801；事件数字 9，十亿美元年化收入）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 1 | USD billion annualized revenue | 202412 | Reuters, June 2025: annualized revenue nearly $1B in December 2024 | 通过 | 数值期 202412 与公布日（路透 2025-05-30，见注）都早于 20250801。1 ≠ 9。路透原文写 December 2024 when the metric was nearly $1B。来源不是事件报道。无同指标跨题等值。 |
| 2 | USD billion annualized revenue | 202503 | Reuters, June 2025: figure crossed $2B around end of March 2025 | 通过 | 数值期 202503 与公布日都早于 20250801。2 ≠ 9。路透原文写 crossed $2B around the end of March。来源不是事件报道。无同指标跨题等值。 |
| 3 | USD billion annualized revenue | 202505 | Reuters, June 2025: hit $3B at May end 2025 | 通过 | 数值期 202505 与公布日都早于 20250801。3 ≠ 9。路透原文写 at May's end it hit $3B。来源不是事件报道。无同指标跨题等值。 |

注：路透这篇的实际刊发日是 2025-05-30（SRN 转载写 Fri, May 30, 2025；The Hindu 写 May 31, 2025 IST）。字段写“Reuters, June 2025”差了几天，但公布日仍在轮次日期之前。Verdict 不变。只记此注，不改字段（复核只删值，不改写）。

### q127（OAI，round_date 20250801；事件数字 20，十亿美元年化收入）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 3.4 | USD billion annualized revenue | 202406 | The Information, June 12 2024: annualized revenue $3.4B | 通过 | 202406 早于 20250801。3.4 ≠ 20。来源同 q123 的 3.4。无同指标跨题等值。 |
| 5.5 | USD billion annualized revenue | 20250609 | CNBC, June 9 2025: ARR above $5.5B at end of 2024 | 通过 | 20250609 早于 20250801。5.5 ≠ 20。CNBC 2025-06-09 披露写 ARR up from $5.5B in December 2024。来源不是本题事件的报道（本题事件是 2025 年底超 $20B，2026-01-18 披露）。裸数字 5.5 与 q69（Pangu 5.5 版本号）相同，但不是指标数字。不是泄漏。 |
| 10 | USD billion annualized revenue | 20250609 | Company spokesperson via CNBC, June 9 2025: ARR $10B | 不过，删除 | 日期与来源本身都通过（20250609 早于 20250801，10 ≠ 20，CNBC 2025-06-09 披露属实）。跨题泄漏不过：该值就是 q123 的事件本身。q123 事件名 OpenAI ARR 达 $10B，事件数字 10，同一玩家 OAI，同一单位十亿美元年化收入，同一披露日 2025-06-09，同一来源 CNBC。P4 答 q123（S4-3-2），又读 q127 的字段（S4-4-1）。P4 在本题字段里直接看到 q123 的答案。删除。 |

### q128（ANTH，round_date 20260101；事件数字 14，十亿美元年化收入）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 1 | USD billion annualized revenue | 202501 | Reuters, June 2025: about $1B at start of 2025 | 通过 | 数值期 202501 与公布日（路透 2025-05-30）都早于 20260101。1 ≠ 14。路透原文写 nearly $1B in December 2024，2025 年初口径约 $1B。来源不是事件报道。无同指标跨题等值。 |
| 3 | USD billion annualized revenue | 202505 | Reuters, June 2025: hit $3B at May end 2025 | 通过 | 202505 与公布日都早于 20260101。3 ≠ 14。来源同 q126 的 3。无同指标跨题等值。 |
| 7 | USD billion annualized revenue | 202510 | Reuters, October 2025 (via Sherwood): run rate $7B in October 2025 | 通过 | 202510 早于 20260101。7 ≠ 14。2025 年 10 月中旬 Anthropic 向路透表示 run rate approaching $7B（Oct 15, 2025）。字段记值 7，来源措辞是 approaching $7B。数字与月份已 pin 定。来源不是事件报道。无同指标跨题等值。 |

### q129（ANTH，round_date 20260101；事件数字 2.5，十亿美元 Claude Code run rate）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 0.5 | USD billion annualized revenue run rate | 20250902 | Series F announcement, September 2 2025: coding product run rate over $500M | 通过 | 20250902 早于 20260101。0.5 ≠ 2.5。Anthropic 官方 Series F 公告（2025-09-02）原文写 Claude Code already generating over $500M in run-rate revenue。TechCrunch 2025-09-02 同日复核。官方公告。来源不是事件报道（本题事件是 2026-02-12 Series G 公告的 $2.5B）。无同指标跨题等值。 |
| 1 | USD billion annualized revenue run rate | 202512 | December 2025 disclosure: coding product $1B run rate in November 2025 | 通过 | 202512（整个 12 月）早于 20260101。1 ≠ 2.5。披露已 pin 定：Anthropic 官方收购 Bun 公告，2025-12-03，原文写 In November, Claude Code reached $1 billion in run-rate revenue。数值期是 2025 年 11 月，公布日是 2025-12-03。字段日期 202512 是公布月，口径站得住。11 月与 12 月说法不一的问题已解决：11 月是数值期，12 月是公布月。来源不是事件报道。无同指标跨题等值。 |

### q130（GOOG，round_date 20260101；事件数字 750，百万月活）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 350 | million monthly active users | 202503 | Google data in antitrust trial, reported by TechCrunch April 23 2025: 350M monthly users in March 2025 | 通过 | 数值期 202503 与报道日 2025-04-23 都早于 20260101。350 ≠ 750。TechCrunch 2025-04-23 报道庭审数据：Gemini 350M MAU in March 2025。来源不是事件报道。无同指标跨题等值。 |
| 400 | million monthly active users | 20250520 | Google I/O 2025, May 20 2025: app over 400M monthly active users | 通过 | 20250520 早于 20260101。400 ≠ 750。Google I/O 2025 主题演讲，Pichai 称 over 400M monthly active users。官方披露。来源不是事件报道。无同指标跨题等值。 |
| 450 | million monthly active users | 20250723 | Alphabet Q2 2025 earnings call, July 23 2025: app more than 450M monthly active users | 通过 | 20250723 早于 20260101。450 ≠ 750。Alphabet Q2 2025 财报电话会，Pichai 称 more than 450M。官方披露。来源不是事件报道。无同指标跨题等值。 |
| 650 | million monthly active users | 20251029 | Alphabet Q3 2025 earnings call, October 29 2025: app over 650M monthly active users | 通过 | 20251029 早于 20260101。650 ≠ 750。Alphabet Q3 2025 财报电话会，Pichai 称 over 650M。官方披露。来源不是事件报道。无同指标跨题等值。 |

### q131（ANTH，round_date 20260101；事件数字 30，十亿美元年化收入）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 1 | USD billion annualized revenue | 202501 | Reuters, June 2025: about $1B at start of 2025 | 通过 | 202501 与公布日都早于 20260101。1 ≠ 30。来源同 q128 的 1。无同指标跨题等值。 |
| 3 | USD billion annualized revenue | 202505 | Reuters, June 2025: hit $3B at May end 2025 | 通过 | 202505 与公布日都早于 20260101。3 ≠ 30。来源同 q126 的 3。无同指标跨题等值。 |
| 7 | USD billion annualized revenue | 202510 | Reuters, October 2025 (via Sherwood): run rate $7B in October 2025 | 通过 | 202510 早于 20260101。7 ≠ 30。来源同 q128 的 7（approaching $7B，路透 2025-10-15）。无同指标跨题等值。 |

### q132（ANTH，round_date 20260101；事件数字 47，十亿美元年化收入）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 1 | USD billion annualized revenue | 202501 | Reuters, June 2025: about $1B at start of 2025 | 通过 | 202501 与公布日都早于 20260101。1 ≠ 47。来源同 q128 的 1。无同指标跨题等值。 |
| 3 | USD billion annualized revenue | 202505 | Reuters, June 2025: hit $3B at May end 2025 | 通过 | 202505 与公布日都早于 20260101。3 ≠ 47。来源同 q126 的 3。无同指标跨题等值。 |
| 7 | USD billion annualized revenue | 202510 | Reuters, October 2025 (via Sherwood): run rate $7B in October 2025 | 通过 | 202510 早于 20260101。7 ≠ 47。来源同 q128 的 7。无同指标跨题等值。 |

### q133（OAI，round_date 20260101；事件数字 40，十亿美元年化收入）

| 数值 | 单位 | 日期 | 出处 | verdict | 理由 |
|---|---|---|---|---|---|
| 3.4 | USD billion annualized revenue | 202406 | The Information, June 12 2024: annualized revenue $3.4B | 通过 | 202406 早于 20260101。3.4 ≠ 40。来源同 q123 的 3.4。无同指标跨题等值。 |
| 5.5 | USD billion annualized revenue | 20250609 | CNBC, June 9 2025: ARR above $5.5B at end of 2024 | 通过 | 20250609 早于 20260101。5.5 ≠ 40。来源同 q127 的 5.5。无同指标跨题等值。 |
| 10 | USD billion annualized revenue | 20250609 | Company spokesperson via CNBC, June 9 2025: ARR $10B | 通过 | 20250609 早于 20260101。10 ≠ 40。CNBC 2025-06-09 披露属实。跨题：该值等于 q123 的事件数字 10（同一玩家 OAI，同一单位）。但不是泄漏。q133 由 P5 答（S4 5-1 与 S5 全部），P5 不读 S4-3-2，不答 q123。读 S4-3-2 的 P4 不读 S5-1-1。没有一位预测员同时看到该值又答 q123。保留。 |

## 删除日志

| 序号 | 题号 | 删除的值 | 单位 | 字段日期 | 删除原因 | 删后该题剩余值 |
|---|---|---|---|---|---|---|
| 1 | q124 | 500 | million weekly active users | 20250609 | 跨题泄漏：该值就是 q122 的事件本身（OAI 500M 周活，CNBC 2025-06-09 同日披露）。P4 同时答 q122 又读 q124 的字段。 | 2 个（300、400） |
| 2 | q127 | 10 | USD billion annualized revenue | 20250609 | 跨题泄漏：该值就是 q123 的事件本身（OAI $10B ARR，CNBC 2025-06-09 同日披露）。P4 同时答 q123 又读 q127 的字段。 | 2 个（3.4、5.5） |

- 删除范围：两组题目文件同时删除。只删了 `runs/round14-weak-repair-2-2026-11-25/questions-control/questions-baseline-S4-4-1.json` 与 `questions-experiment/questions-baseline-S4-4-1.json` 里的上述两项。没有编新值替代。没有改其他文件。没有改方法文件。没有改题集。
- 删后两组目录 `diff -r` 逐字节一致。
- 删后没有题剩 0 个值。最少值的题是 q124、q127、q129，各剩 2 个值。规则 N 仍可执行。

## 两处重点项的结论

### q121 的 $65M

- 留下。搭建报告的担心已解决。Sacra 页面原文写 Published Nov 27th, 2024，写 Sacra estimates that Cursor hit $65M in annualized recurring revenue (ARR) in November 2024。公布日 2024-11-27 严格早于预测点 2025-01-27。数值期 2024 年 11 月也在预测点之前。来源是轮次前已公布的估计，不是事件本身的报道（本题事件是 TechCrunch 2025-06-05 报道的 $500M ARR）。

### q129 的两项

- $500M（0.5，20250902）：留下。Anthropic 官方 Series F 公告（2025-09-02）原文写 Claude Code already generating over $500 million in run-rate revenue。TechCrunch 2025-09-02 同日复核同一数字。轮次前公布来源已 pin 定。公布日早于 2026-01-01。
- $1B（1，202512）：留下。披露月份口径已 pin 定。Anthropic 官方收购 Bun 公告（2025-12-03）原文写 In November, Claude Code reached $1 billion in run-rate revenue。数值期是 2025 年 11 月。公布日是 2025-12-03。字段日期 202512 是公布月，口径站得住。公布日早于 2026-01-01。此前“11 月与 12 月说法不一”是数值期与公布月之分，不是来源不明的表现。

## 搭建报告点名的 500 一项的重查结论

- 搭建报告 q125 一节注明：500 一项的数值与 q121 的事件数字相同。重查结论：q125 的 500 不是泄漏。q121 由 P3 答，P3 只读 S4 1-1、1-2、1-3。q125 的字段在 S4-4-1 里，只由 P4 读。P4 不答 q121。没有一位预测员同时看到该值又答 q121。保留 q125 的 500。
- 但重查发现了另外两处同名泄漏，不在搭建报告的注明里：q124 的 500 泄漏 q122，q127 的 10 泄漏 q123。两处都是同一预测员 P4 的批内泄漏。两项已删除。见删除日志。
- 另有两处同名但不泄漏：q133 的 10 等于 q123 的事件数字，但 P5 不答 q123。q121 的 65 等于 q101 的 $65 亿，但玩家、单位、指标都不同。两处都保留。理由见 verdict 表。

## 删后重扫与重核结果

### numeric_history 字段全文重扫

- 扫描脚本：工作区根目录 `scan_method_leaks.py`。扫描对象：删后 14 道题、40 项的字段全文（抽出文件 `/tmp/numeric_history_only.json`）。结果已写入 `runs/round14-weak-repair-2-2026-11-25/scores/numeric-history-scan.json`（覆盖搭建时的旧扫描结果）。
- 第 1 项（事件名全文、动作原文全文）：0 命中。
- 第 2 项（同行题号加种类）：0 命中。
- 第 3 项（同行题号加玩家）：0 命中。
- 第 4 项（裸题号）：0 行。
- 第 5 项（长公共子串 ≥8 字）：6 处，与搭建报告的 6 处相同。人工复核，都是通用词重叠，不是泄漏：Series（与 q42 事件名共享，字段写 Series B report 与 Series F announcement）；inancial（与 q62 事件名共享，字段写 Financial Times）；announce（与 q34 事件名共享，字段写 announcement）；Alphabet Q（与 q11 事件名共享，字段写 Alphabet Q2/Q3 2025 earnings call）。
- 扫描退出码 0。主项 0 命中。扫描通过。

### 题目文件基础项重核

- 核对脚本：`/tmp/check_r14_questions.py`（搭建所用脚本，原样重跑）。结果 OVERALL: ALL PASS。
- 两组各 31 文件、215 题。题号齐全，无缺失，无多余。全部题 round_date 与 testset-v7.json 一致。player_last3 每条记录日期严格早于轮次日期。答案字段（kind、action、event_name、event_real_date、source）0 命中。forward_guidance 0 道题带。numeric_history 仍在正好 14 道题上（q121–q133 与 q213）。numeric_history 每项日期严格早于 round_date。numeric_history 没有一项数值等于本题事件数字。每项恰含 value、unit、date、source 四键。除 numeric_history 外两组题目文件逐题比对 0 处不同。两组目录 diff -r 逐字节一致。
- numeric_history 值总数：每组 40 个（原 42 个，删 2 个）。

## 给协调员的说明

- 跨题泄漏的判定用了预测员批口径，不是单文件口径。理由：预测员按分派表读整批轮次文件。P4 读 S4-3-2 与 S4-4-1 两份文件。单文件口径下 q124 的 500 与 q127 的 10 都不算泄漏，因为 q122、q123 在另一份文件里。但 P4 同时看到答案与题目。批口径才是实际泄漏面。协调员若坚持单文件口径，可推翻这两项删除。删除只动了两组题目文件里 S4-4-1 的两项。恢复只需把两项写回。
- 两个小注记，不改 verdict：路透 Anthropic $3B 一篇的实际刊发日是 2025-05-30，不是字段写的 June 2025。$7B 一项的来源措辞是 approaching $7B（路透 2025-10-15），字段记值 7。两处都不影响日期与来源 verdict。复核只删值，不改写字段。是否改写字段措辞，由协调员定。
- 本报告留在工作区，未提交。题目文件在 `runs/` 下，该目录在 `.gitignore` 里。复核改动只在工作区磁盘上，不在 git 提交里。
