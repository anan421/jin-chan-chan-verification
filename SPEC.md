# 题集补齐 SPEC（给核实员）

## 任务
核实计划里你负责类别的每一道候选题（一手来源），产出可直接进题集的题目 JSON。
计划：`~/workspace/verification/design/testset-coverage-plan.md`。
题集现状：`~/workspace/verification-v1-testset-complete/testset-v6.json`（98 道，q_id 0–78、80–98，q79 空缺）。

## 核实标准（硬性）
- 每道题补进题集前，须用一手来源核实事件与日期。
- 一手来源 = 公司官方公告、SEC 文件、公司财报、官方博客；或路透 / 彭博 / CNBC / TechCrunch 报道公司披露。
- 聚合器旧闻、二手转述不作来源（arr 类的 SemiAnalysis 转述须在 source 里标注「据 SemiAnalysis 转述」）。
- 日期只有月份时，event_real_date 写 YYYYMM（6 位），不拼凑确切日。
- 核实不了一手来源的题：status 写 "excluded"，verify_note 写清原因（例如「只有单源」「日期两说无法定」「找不到官方公告」），不进题集。
- 事件真实日期须不晚于 2026-11-21（S5 事件）。晚于该日的题不进，status 写 "excluded" 并说明。
- 诉讼 / 执法类不进（用户未定）。Grok 图像滥用等安全争议事件不进。

## 输出格式
写一个 JSON 文件到 `~/workspace/verification-v1-testset-complete/new_questions/<你的文件名>.json`。
格式：`{"category": "A1", "questions": [ ... ], "excluded": [ ... ]}`。
每道 verified 的题一个对象，字段如下（不要自己编 q_id 与 split，中央统一分）：
- `event_name`：事件短名，如 "Claude Opus 4.6 发布"。
- `event_real_date`：整数。确切日写 YYYYMMDD（8 位）；只有月份写 YYYYMM（6 位）。
- `player`：玩家代码（见下表）。
- `kind`：种类代码（见下表，按计划）。
- `action`：一句话中文，写事件的意思 / 影响（仿照题集现有风格，如 "Claude 编程场景成王牌"）。
- `source`：引用文字，含来源名 + 日期 + 关键事实。如 "Anthropic 官方公告，2026-02-05：Opus 4.6 发布，1M 上下文（beta）"。
- `verify_url`：你核实用的 primary 来源 URL（供审计，不进最终题集）。
- `verify_note`：你确认了什么 / 有何限定（如「日期两说，官方公告为准」「口径为公司自报，非 GAAP」）。
- `origin`：写 "testset-complete"。
- `round_label_hint`（可选）：你认为该事件属哪个赛季轮次，可不填，中央按日期重算。

excluded 的题也列出：`{"event_name": ..., "reason": "..."}`，放在顶层 `excluded` 数组。

## 玩家代码映射
- Anthropic → ANTH；OpenAI → OAI；Google / DeepMind → GOOG；Meta → META；微软 → MSFT；英伟达 → NVDA；阿里 → ALI；字节跳动 → BYTE；腾讯 → TCE；百度 → BIDU；华为 → HUAWEI；DeepSeek → DPSK；亚马逊 → AMZN；甲骨文 → ORCL；台积电 → TSMC；软银 → SFTB；马斯克 / xAI / SpaceX → MUSK。
- 新增：月之暗面 / Kimi → KIMI；智谱 → ZHIPU；MiniMax → MINIMAX；OpenClaw → OPENCLAW；Manus / Butterfly Effect → MANUS；Anysphere / Cursor → CURSOR；CoreWeave → CRWV；欧盟 → EU；加州 → CALIF；三星 → SAMSUNG；SK 海力士 → SKHYNIX；美光 → MICRON；AMD → AMD。
- 多方事件用主要一方：Google 收 Wiz → GOOG；Meta 投 Scale → META；OpenAI 收 io → OAI；xAI 收 X → MUSK；SpaceX 收 xAI → MUSK；SpaceX 收 Cursor → MUSK；Meta 收 Manus → META；中国发改委叫停 Meta 收 Manus → META；OpenAI PBC 重组 → OAI；英伟达拟投 OpenAI → NVDA；英伟达投资缩水 → NVDA；Anthropic TPU 协议 → ANTH；OpenAI 与 AMD → OAI；OpenAI 与 Google Cloud → OAI；Meta 成立 MSL → META。

## 种类代码
按计划：claude、chatgpt、gemini、r1、v3、tongyi、llama、kimi、muse（Meta 的 Muse 模型，注意与种类名区分）、agent、arr、acquisition、partnership、financing、blackwell、memory、math、wallstreet、talent、bis_rule、video、social。
- N 类（用户里程碑）并入 arr 种类，不另设种类（kind 写 "arr"）。
- Qwen 线用 tongyi；DeepSeek R1 线用 r1，V3/V4 线用 v3；Llama 用 llama；Muse Spark / Wonder 用 muse。

## 注意
- 不要改 testset-v6.json 与任何题集文件。只写你的输出 JSON。
- 不要动 S6 池与 S6 监控。
- 每个事件先查一手来源再写题。不要凭记忆写日期。
- 若计划给的日期与一手来源不符，以一手来源为准，并在 verify_note 说明。
- 若计划给的事件本身查无实据（如某产品不存在、某数字有争议），status 写 "excluded" 并说明，不要硬编。
