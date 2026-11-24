# 第 7 轮 Part 2 报告：题集补齐（testset-v7，215 道）

- 工作区：`~/workspace/verification-v1-testset-complete`
- 分支：`loop/vision-1-testset-complete`（未合 main，未推 GitHub）
- 日期：2026-11-22
- 范围：只补题集。不跑实验，不动 S6 池与监控，不改任何 S5 动作、血量、金币。动作数仍 558，`data.json` 未动。

## 1. 结果总览

- testset-v6 98 道 → **testset-v7 215 道**（+117 道）。
- 分集：A 108 / B 107（旧 98 道分集一字未动；新 117 道按种类/赛季/轮次/玩家分层轮换，B 先起，A 58 / B 59）。
- 种类：29 个 → **43 个**（新设 14 个：kimi、muse、agent、arr、acquisition、partnership、memory、math、wallstreet、talent、video、social、glm、minimax）。
- 缺口：到 140 道的缺口 42 → **0**（已超目标 75 道）。
- 候选池 119 道，核实通过 117 道，未进 2 道（见 §3）。
- claude 类：4 道 → **16 道**（3.7 → 4 → 4.1 → 4.5 → 4.6 → 4.7 → 4.8 → 5 → 5.2，含 Fable 5 / 5.2）。模型发布类合计约 34 道 → 约 71 道。

## 2. 各类别补了多少道

| 类别 | 种类 | 补题数 | 备注 |
|---|---|---|---|
| A1 Claude | claude | 12 | 3.7、4.1、Sonnet 4.5、Haiku 4.5、Opus 4.5、Opus 4.6、Sonnet 4.6、Opus 4.7、Opus 4.8、Fable 5、Opus 5、Fable 5.2 |
| A2 GPT | chatgpt | 3 | o3、GPT-5.1、GPT-5.2 |
| A3 Gemini | gemini | 3 | Gemini 2.0、3 Pro、3.1 Pro |
| A4 DeepSeek | r1 / v3 | 5 | R1-0528、V3.2、V4 预览、V4-Pro GA、V4.1 Flash |
| A5 Qwen | tongyi | 4 | Qwen3-Coder、Qwen3.8-Flash-Next、Qwen3.8-Omni-Flash、Qwen4-Max |
| A6 Kimi | kimi（新） | 5 | K2、K2 Thinking、K2.5、K3、K3.1 Pro |
| A7 Meta | llama / muse（新） | 3 | Llama 4、Muse Spark、Muse Wonder |
| A8 其他中国模型 | glm / minimax（新） | 2 | GLM-4.5、MiniMax M2 |
| B 核心产品 | agent（新） | 13 | Claude Code 预览/GA、Cowork、Grok Bot、Grok Build、OpenClaw 2.0、WorkBuddy、CodeBuddy NPC、Trae、TRAE SOLO、Manus、Antigravity、Atlas |
| C 收入/ARR | arr（新） | 10 | Anthropic $9B/$14B/$30B/$47B、OpenAI $10B/$20B/$40B、Claude Code $2.5B、Cursor $500M/$1B |
| N 用户里程碑 | arr（并入） | 3 | ChatGPT 周活 5 亿/8 亿、Gemini 月活 7.5 亿 |
| D 收购 | acquisition（新） | 9 | Google-Wiz、Meta-Scale、OpenAI-io、Windsurf 告吹、xAI-X、SpaceX-xAI、SpaceX-Cursor、Meta-Manus、发改委叫停 |
| E 战略/合作 | partnership（新） | 6 | OpenAI PBC 重组、英伟达拟投 OpenAI、投资缩水、Anthropic TPU 协议、OpenAI-AMD、Meta MSL |
| F 融资 | financing | 6 | OpenAI $40B/$122B、Anthropic G/H、CoreWeave IPO、SpaceX IPO |
| G 芯片 | blackwell | 4 | Blackwell Ultra、Rubin、TPU Ironwood、AMD MI400 |
| H 存储 | memory（新） | 4 | 存储短缺、三星/SK 海力士再涨、DRAM 合约价、美光退出 Crucial |
| I 数学/基准 | math（新） | 5 | IMO 2024 银牌、o3 ARC-AGI、IMO 2025 金牌×3（OpenAI、DeepMind、DeepSeekMath-V2） |
| J 华尔街 | wallstreet（新） | 4 | 英伟达 $4T、甲骨文 +35%、CoreWeave +14%、英伟达因 R1 跌 17% |
| K 人才 | talent（新） | 3 | Meta $1 亿签约奖、Ruoming Pang 跳槽、Tulloch $15 亿 offer |
| L 政策 | bis_rule | 2 | 欧盟 AI 法案、加州 SB 53 |
| M 视频 | video（新） | 3 | Sora、Veo 3、Sora 2 |
| O 社交媒体 | social（新） | 8 | 吉卜力刷屏、Gemini 暂停、Sydney、Gemini 演示造假、Devin 拆穿、vibe coding、Claude 玩宝可梦、OpenAI 员工联署 |
| 合计 | | 117 | |

## 3. 没进的 2 道（带原因）

1. **OpenAI 与 Google Cloud 合作**（E 类，partnership）：无双方官方公告。路透 2025-06-10 独家报道援引三名匿名消息人士，双方均拒绝置评。不合一手来源标准（须公司官方公告或报道公司披露），先不进。
2. **OpenClaw 公开仓库上线**（B 类，agent，计划日期 2026-01-28）：查无实据。GitHub API 显示 openclaw/openclaw 仓库 created_at 为 2025-11-24（当时名为 Warelay/Clawdbot），仓库自该日起即已公开；2026-01-28 既非创建日也非更名日（01-27 更名 Moltbot，01-29/01-30 更名 OpenClaw）。该事件按计划表述无法成立，不进。如要补 OpenClaw，可改以仓库创建日 20251124 或更名 OpenClaw 日 20260129/20260130 另行立题（由用户定）。

## 4. 计划日期纠正（以一手来源为准，共 14 处）

- Gemini 3.1 Pro：计划 2026-03-09 → **2026-02-19**（03-09 是旧版 preview 停服日）。
- GPT-5.2：计划只给月份 → **2025-12-11**。
- Kimi K3.1 Pro：计划 10-24 → **2026-10-23**（官方技术博客）。
- MiniMax M2：计划 10-28 → **2025-10-27**。
- Muse Wonder：计划只给月份 → **2026-10-12**。
- Claude Cowork：计划 2026-08-18 → **2026-01-12**（08-18 是扩围日，推出日为 01-12）。
- Anthropic Series G：计划只给月份 → **2026-02-12**。
- Rubin：计划只给年份 → **2026-01-05**（CES 发布；03-16 GTC 七芯片版是扩展）。
- 三星/SK 海力士涨价：计划 2026-01-06 → **2026-01-05**（韩国经济日报原文）。
- DRAM Q1 涨 90–95%：计划 2026-03 → **2026-02-02**（TrendForce 修订预期发布日）。
- 美光退出 Crucial：计划 2026-01 → **2025-12-03**（官方公告日；2026-02 只是停出货时点）。
- OpenAI-AMD 6GW：计划只给月份 → **2025-10-06**。
- 英伟达因 R1 跌幅：计划“约 20%”→ **16.9%（约 17%）**。
- 加州 SB 53 签署：计划 2025-10-13 → **2025-09-29**（州长办公室）。
- Tulloch：计划日期 2025-06 → **2025-08**；题面由“获 $15 亿 package”改为“据 WSJ 报道开出 offer、Tulloch 拒绝”（Meta 称数字“不准确且荒谬”）。
- Gemini 月活 7.5 亿：计划 2026-03 → **2026-02-04**（Alphabet Q4 财报电话会）。
- Gemini 演示造假：计划 12-08 → **2023-12-07**（首报日）。
- Devin 拆穿视频：计划 04-18 → **2024-04-09**（视频发布日；04-18 是总结文章日）。
- DeepSeekMath-V2：计划只给年份 → **2025-11-27**（论文提交日）。
- Altman $1 亿签约奖 / Ruoming Pang 跳槽：计划只给月份 → **2025-06-17 / 2025-07-07**。

另：Claude Code $2.5B 来源升级——计划称 SemiAnalysis 二手转述，核实发现 Anthropic 官方 Series G 公告直接披露同一数字，改引官方公告。Grok Build 只写月份 202605（确切日无法以官方为准）。

## 5. 校验与审计

- 组装器 `build_testset_v7.py` 断言全部通过：215 道（旧 98 + 新 117）、A 108 / B 107、无重编号（q79 仍空缺）、旧 98 道每个字段一字未动、每种 2 道以上的种类两边都有、日期全扫 0 违规。
- 日期格式：107 道确切日（8 位）、10 道月-only（6 位 YYYYMM，不拼凑确切日）、0 道年-only（Rubin 与 DeepSeekMath-V2 均核到确切日）。
- 赛季/轮次指派：中央按事件日期指派（事件日之前最后一轮；月-only 用当月 1 日之前最后一轮）。`round_date` 全部 ≤ 事件日（日历天数）。
- 审计 `audit_v7.py`：日期违规 **0**、重复 **0**、泄题（新事件名原样出现在更早 trace/事实库）**0**、污染（事实日期晚于事件日）**0**。审计文件 `runs/testset-v7-audit/audit-v7.json`。
- S5 重验：`./run.sh` 退出码 **0**（快速检查器 pass，558 条动作 / 18 名玩家 / 5 个赛季 / 90 个排名 / 12 条不变量；Lean 构建退出 0）。trace 是工作区内从 `raw-trace-real.json` 重新生成的，558 条动作，内容未动。

## 6. 看板更新

- 预测实验室看板（slug `jin-chan-chan-yu-ce-shi-yan-shi`）`update_testset` 已更新：题集 **215**（A 108 / B 107）、缺口 **0**，备注写清补齐口径与 2 道未进原因。`get_summary` 读回核对通过。
- 注意：看板按种类/轮次/玩家的分数图仍是 88 道基线（第 4 轮）的数字，新题集的分数要等下一轮（第 11 轮）在 215 道上跑出后才更新。

## 7. 未做的事与待定

- 未动 S6 池与 S6 监控（新题全是 S5 事件，真实日期不晚于 2026-11-21）。
- 未合 main，未推 GitHub（按分支纪律，待用户定夺）。
- OpenClaw 仓库题是否改以创建日 20251124 或更名日 20260129/20260130 另行立题，由用户定。
- OpenAI-Google Cloud 合作题是否接受匿名独家口径，由用户定（目前按一手来源标准排除）。
- 下一步：第 11 轮可在 215 道新题集上开跑（不再等 S6 候选积累）；或先在 215 道上重测基线，看分数变化。
