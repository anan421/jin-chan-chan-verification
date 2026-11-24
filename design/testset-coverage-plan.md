# 题集覆盖计划：testset-v6 补缺方案

> 历史设计记录（v6 时代，2026-11-22 前后）。本文写时现状为 testset-v6 共 98 道，目标 140 道。
> 该框架已过时：testset-v7 已达 215 道、43 种，140 道目标已过期。
> 本文仍是 v7 的设计依据：v7 从本文的 119 道候选池中补题。
> 读本文时以 v7 为准，不以本文的目标数字为准。

- 现状：testset-v6 共 98 道题。
- 目标：140 道题以上。
- 缺口：42 道。
- 本计划：系统扫描 2022–2026 年 AI 行业（S1–S6），列出全部缺的事件类与关键产品，共 119 道候选题。第一阶段补 44 道，到 142 道。第二阶段留 75 道作储备池。
- 约束：不改 testset-v6.json 或任何题集文件。本计划只报设计，等用户定夺。

## 1. 扫描方法

- 维度：前沿模型发布、核心产品（编码工具、智能体、应用）、收入/ARR、收购、战略变化、合作、芯片与算力、存储与供应链、政策监管、华尔街与资本市场、前沿数学与基准突破、人才流动、多模态/视频模型、用户里程碑、社交媒体风向。
- 来源：只用一手来源（公司官方公告、S-1/SEC 文件、公司财报、官方博客）或一手转述（路透、彭博、CNBC、TechCrunch 报道公司披露）。聚合器旧闻不作来源。
- 边界：全部候选事件真实日期不晚于 2026-11-21，属 S5 期漏题，可直接补进题集。2026-11-22 之后的事件属 S6，走 S6 监控合题流程，不进本计划。
- 核实状态：日期后标「待核」表示该日期尚未经一手来源核实，补题前必须先核。

## 2. 完整类别清单（15 类，119 道）

| 类别 | 新种类 | 现有题数 | 拟补题数 | 池内小计 |
|---|---|---|---|---|
| A. 前沿模型发布 | claude / chatgpt / gemini / r1 / v3 / tongyi / llama 扩充；kimi / muse 新设 | 34 | 37 | 37 |
| B. 核心产品 / 智能体 | agent 新设 | 0 | 14 | 14 |
| C. 收入 / ARR | arr 新设 | 0 | 10 | 10 |
| D. 收购 | acquisition 新设 | 0 | 9 | 9 |
| E. 战略变化与合作 | partnership 新设 | 0 | 7 | 7 |
| F. 融资 | financing 扩充 | 7 | 6 | 6 |
| G. 芯片与算力 | blackwell 扩充 | 1 | 4 | 4 |
| H. 存储与供应链 | memory 新设 | 0 | 4 | 4 |
| I. 前沿数学与基准 | math 新设 | 0 | 5 | 5 |
| J. 华尔街与资本市场 | wallstreet 新设 | 0 | 4 | 4 |
| K. 人才流动 | talent 新设 | 0 | 3 | 3 |
| L. 政策监管 | bis_rule 扩充 | 4 | 2 | 2 |
| M. 多模态 / 视频模型 | video 新设（低优先级） | 0 | 3 | 3 |
| N. 用户里程碑 | 并入 arr（不另设种类） | 0 | 3 | 3 |
| O. 社交媒体风向 | social 新设 | 0 | 8 | 8 |
| 合计 | 12 个新种类 | 46 | 119 | 119 |

注：现有题数 46 道指上述类别现有的题数合计（其余 52 道属题集其他类别，不在本计划范围内）。

## 3. 每类明细

### A. 前沿模型发布（37 道）

题集现状：claude 类只有 4 道，最新 2025-05-22（Opus 4 / Sonnet 4）。chatgpt 类 5 道，最新 2026-11-17（GPT-6.2 Astra 与 Sol），中间断档 2025-08 至 2026-11。gemini 类 5 道，缺 Gemini 3 Pro。r1 类 4 道，最新 2025-02-13。v3 类 2 道。tongyi 类 6 道，最新 2025-04-29（Qwen3）。llama 类 3 道，最新 2024-04-18（Llama 3）。kimi 类 0 道。

#### A1. Claude 线（claude，补 12 道）

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| Claude 3.7 Sonnet 发布 | 2025-02-24 | Anthropic | Anthropic 官方公告 | 首个混合推理模型；Claude Code 同日上线 |
| Claude Opus 4.1 发布 | 2025-08-05 | Anthropic | Anthropic 官方公告 | Opus 4 的小幅升级，编码能力提升 |
| Claude Sonnet 4.5 发布 | 2025-09-29 | Anthropic | Anthropic 官方公告 | 当时最强编码模型，SWE-bench 领先 |
| Claude Haiku 4.5 发布 | 2025-10-15 | Anthropic | Anthropic 官方公告 | 轻量旗舰，速度与成本平衡 |
| Claude Opus 4.5 发布 | 2025-11-24 | Anthropic | Anthropic 官方公告 | SWE-bench Verified 80.9%，降价 67% 至 $5/$25 |
| Claude Opus 4.6 发布 | 2026-02-05 | Anthropic | Anthropic 官方；AWS Bedrock 模型卡确认上线日期 | 用户点名。旗舰模型，1M 上下文（beta），Claude Code 默认编程模型 |
| Claude Sonnet 4.6 发布 | 2026-02-17 | Anthropic | Anthropic 官方公告 | Opus 4.6 的同代中端模型 |
| Claude Opus 4.7 发布 | 2026-04-16 | Anthropic | Anthropic 官方公告 | 4.x 线延续 |
| Claude Opus 4.8 发布 | 2026-05-28 | Anthropic | Anthropic 官方公告 | 4.x 线末代旗舰 |
| Claude Fable 5 发布 | 2026-06-09 | Anthropic | Anthropic 官方公告 | 用户说的 Fable5 即此。1M 上下文，$10/$50，Mythos 级 |
| Claude Opus 5 发布 | 2026-07-24 | Anthropic | Anthropic 官方公告 | 5 代旗舰 |
| Claude Fable 5.2 发布 | 2026-11-09 | Anthropic | Anthropic 官方公告 | 5.2 代，最新 Fable |

储备：Mythos Preview 2026-04-07；Mythos 5 2026-06-09；Sonnet 5 2026-06-30；Fable 5.1 与 Mythos 5.1 2026-09-01；Opus 5.5 2026-09-22；Sonnet 5.5 2026-09-28；Haiku 5.5 2026-10-07。

#### A2. GPT 线（chatgpt，补 3 道）

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| OpenAI o3 发布 | 2024-12-20 | OpenAI | OpenAI 官方公告；ARC Prize 确认 | ARC-AGI 87.5%，推理模型拐点 |
| GPT-5.1 推出 | 2025-11-12 | OpenAI | OpenAI 官方公告 | GPT-5 的修复版，ChatGPT 与 API 同步 |
| GPT-5.2 发布 | 2025-12 | OpenAI | OpenAI 官方公告（确切日待核） | GPT-5 线末代 |

#### A3. Gemini 线（gemini，补 3 道）

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| Gemini 2.0 发布 | 2024-12-11 | Google | Google 官方博客（日期待核） | 多模态 agent 模型起点 |
| Gemini 3 Pro 发布 | 2025-11-18 | Google | Google 官方博客 | 旗舰模型，首日进 Search AI Mode、Gemini 应用、Vertex AI、Antigravity |
| Gemini 3.1 Pro 发布 | 2026-03-09 | Google | Google 官方博客 | 取代 Gemini 3 Pro；Gemini 应用月活 2026-03 达 7.5 亿 |

#### A4. DeepSeek 线（r1 / v3，补 5 道）

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| DeepSeek R1-0528 发布 | 2025-05-28 | DeepSeek | DeepSeek 官方公告 | R1 升级版 |
| DeepSeek V3.2 发布 | 2025-12-01 | DeepSeek | DeepSeek 官方公告 | 正式版 + V3.2-Speciale，IMO 金牌级推理 |
| DeepSeek V4 预览发布 | 2026-04-24 | DeepSeek | DeepSeek 官方公告 | V4-Pro 1.6T 总参数 / 49B 激活，1M 上下文，MIT 开源 |
| DeepSeek V4-Pro GA | 2026-08-13 | DeepSeek | DeepSeek 官方公告 | V4 正式版 |
| DeepSeek V4.1 Flash 发布 | 2026-09-10 | DeepSeek | DeepSeek 官方公告 | V4.1 轻量版 |

储备：V3.1-Terminus 2025-09-22；V3.2-Exp 2025-09-29（首个 DSA 稀疏注意力）。注：V3.1（2025-08-21）题集已有 1 道。

#### A5. Qwen 线（tongyi，补 4 道）

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| Qwen3-Coder 与 Qwen Code 发布 | 2025-07-22 | 阿里 | 阿里官方公告 | Qwen3 之后首个大版本，编码专用 |
| Qwen3.8-Flash-Next 发布 | 2026-08-26 | 阿里 | 阿里官方公告 | Qwen4 架构预览，开权重 |
| Qwen3.8-Omni-Flash 发布 | 2026-09-18 | 阿里 | 阿里官方公告 | 多模态旗舰 |
| Qwen4-Max 上线 | 2026-11-16 | 阿里 | 阿里官方公告 | Qwen4 旗舰，仅托管，无权重 |

注：Qwen 4 于 2026-09-22 宣布「在训练中」（Apsara 大会）。Qwen4-Max 预览 2026-11-11。Qwen 4 Coder 不存在（截至 2026-11-14 核查）。

#### A6. Kimi 线（kimi，新设，补 5 道）

题集现状：Kimi 0 道。确认无误。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| Kimi K2 发布 | 2025-07-11 | 月之暗面 | 月之暗面官方公告 | 1T MoE，32B 激活，开权重 |
| Kimi K2 Thinking 发布 | 2025-11-06 | 月之暗面 | 月之暗面官方公告 | 推理版 |
| Kimi K2.5 发布 | 2026-01-27 | 月之暗面 | 月之暗面官方公告 | 原生多模态 |
| Kimi K3 发布 | 2026-07-16 | 月之暗面 | 月之暗面官方公告 | 用户说的 Kimi K3 即此。2.8T 参数，896 专家，1M 上下文 |
| Kimi K3.1 Pro 发布 | 2026-10-24 | 月之暗面 | 月之暗面官方公告（10-23 / 10-24 两说，待核） | K3 后训练加强版，2.8T 总参数 / 104B 激活 |

储备：Kimi K3.1 Pro 权重 2026-11-04 在 Hugging Face 公开（仓库 moonshotai/Kimi-K3.1-Pro，约 1.56TB）。该事件已于 2026-11-04 触发白宫协议晨检并报过用户。

#### A7. Meta 线（llama 扩充 + muse 新设，补 3 道）

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| Llama 4 Scout / Maverick 发布 | 2025-04-05 | Meta | Meta 官方公告 | MoE，17B 激活，Scout 10M 上下文；Behemoth 未发布；Llama 4 之后 Meta 再无新的开权重 Llama |
| Muse Spark 发布 | 2026-04-08 | Meta | Meta 官方公告 | 用户说的 Muse 即此。Meta Superintelligence Labs 首个模型，闭源，内部代号 Avocado，Alexandr Wang 领导 |
| Muse Wonder 发布 | 2026-10 | Meta | Meta 官方公告（确切日待核） | Muse 线第二代 |

#### A8. 其他中国模型（新设，补 2 道）

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| GLM-4.5 发布 | 2025-07-28 | 智谱 | 智谱官方公告（日期待核） | 中国开权重旗舰，agent 能力强 |
| MiniMax M2 发布 | 2025-10-28 | MiniMax | MiniMax 官方公告（日期待核） | 中国开权重模型，编程能力突出 |

待查（日期未核，不进池）：文心 5.0、混元后续、豆包后续（豆包-Seed-1.6 之后）。

### B. 核心产品 / 智能体（agent，新设，补 14 道）

题集现状：agent 类 0 道。Claude Code、Grok Bot、OpenClaw、WorkBuddy、Trae、Cursor、Manus、Antigravity、Atlas 全部缺失。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| Claude Code 有限研究预览上线 | 2025-02-24 | Anthropic | Anthropic 官方公告 | Anthropic 称其为「第一个 agentic 编程工具」；随 Claude 3.7 Sonnet 发布 |
| Claude Code 正式 GA | 2025-05-22 | Anthropic | Anthropic 官方公告 | 随 Claude 4 上线；到 2026-02 年化收入 $2.5B，是 ARR 暴涨主驱动 |
| Claude Cowork 推出 | 2026-08-18 | Anthropic | Anthropic 官方公告 | 给非开发者的 agent；2026-09-16 并入「one Claude」统一界面 |
| Grok Bot 早期 beta 上线 | 2026-08-11 | xAI | xAI 官方公告 | 消息驱动的 agent「队友」，共享云电脑，关机后继续工作；捆绑 SuperGrok 与 Cursor 付费计划 |
| Grok Build 早期 beta 上线 | 2026-05 | xAI | xAI 官方公告（日期各来源不一：05-14 / 05-25 / 06-05，待核） | 终端编程 agent，仅限 SuperGrok Heavy（$300/月），基于 grok-code-fast-1 |
| OpenClaw 公开仓库上线 | 2026-01-28 | Peter Steinberger | GitHub 公开仓库（01-25 / 01-28 两说，待核） | 开源个人 agent 框架；三周内破 10 万 GitHub 星，史上增长最快开源项目，后超 32 万星 |
| OpenClaw 2.0 发布 | 2026-08-31 | OpenClaw | OpenClaw 官方公告 | 2.0 大版本 |
| 腾讯 WorkBuddy 公开上线 | 2026-03-09 | 腾讯 | 腾讯云官方公告 | 用户说的 WorkBuddy 即此。全场景桌面 AI 办公 agent；腾讯 Q1 2026 财报称其为中国日活最高的效率类 AI agent |
| 腾讯 CodeBuddy NPC 发布 | 2026-07-23 | 腾讯 | 腾讯云官方公告 | 云端研发 agent；腾讯内部 85% 开发者在用，编码时间降 40% |
| 字节 Trae 上线 | 2025-01-20 | 字节跳动 | 字节官方公告（01-19 / 01-20 两说，待核） | AI 原生 IDE；12 个月内注册用户超 600 万、近 200 国 |
| TRAE SOLO GA | 2025-11-04 | 字节跳动 | 字节官方公告 | SOLO 正式版；2026-06-09 更名为 TRAE Work |
| Manus 邀测上线 | 2025-03-06 | Butterfly Effect | Manus 官方公告 | 通用 agent 爆款；8 个月后 ARR 破 $1 亿；Meta 收购后被中国叫停（见 D 类） |
| Google Antigravity 公开预览 | 2025-11-18 | Google | Google 官方博客 | agent-first IDE；随 Gemini 3 Pro 发布；免费公开预览 |
| ChatGPT Atlas 发布 | 2025-10-21 | OpenAI | OpenAI 官方公告 | OpenAI 首个 AI 浏览器，macOS 首发，免费 |

储备：Codex-Max 2025-11-19；ChatGPT Atlas 退役 2026-08-09；Meta AI 应用 2025-04-29（日期待核）；Antigravity 2.0 2026-05-19（Google I/O）。

注：Claude Code 2.0（2026-08-30）为单源，补题前须再核。OpenClaw 作者后被 OpenAI 聘用；黄仁勋 2026-03-17 称 OpenClaw 为「个人 AI 的操作系统」。微软 Copilot Autopilot（2026-09）运行在 OpenClaw 上。WorkBuddy 国际版 2026-05-28 上线，企业版工作台 2026-06-05 发布。CodeBuddy 默认用 Kimi K2.6 做多数编程任务。

### C. 收入 / ARR（arr，新设，补 10 道）

题集现状：arr / revenue 类 0 道。「收入」「ARR」关键词命中 0。

Anthropic run-rate 口径：近 28 天消费年化 + 当月订阅 × 12。非 GAAP。公司自报口径，题面须写明口径与来源。OpenAI CRO 2026-04-13 内部备忘录称 Anthropic 的 $30B 口径高估约 $8B（AWS / Azure / GCP 分成确认方式）。增长本身无争议，口径争议记为限定。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| Anthropic run-rate 达 $9B | 2025-12 | Anthropic | Anthropic 官方披露（确切日待核） | Opus 4.5 发布后一个月，2025 年底里程碑 |
| Anthropic run-rate 达 $14B | 2026-02 | Anthropic | Series G 披露 | Claude Code 年化收入 $2.5B 同期披露 |
| Anthropic run-rate 超 $30B | 2026-04-06 | Anthropic | Anthropic 官方（与 Google / Broadcom TPU 协议同日披露） | 与 TPU 协议挂钩的同一日披露 |
| Anthropic run-rate 超 $47B | 2026-05-28 | Anthropic | Series H 官方披露（$65B 轮次，$965B 估值） | 与 Series H 挂钩 |
| OpenAI ARR 达 $10B | 2025-06-09 | OpenAI | OpenAI 发言人向 CNBC 确认 | 首家 AI 原生公司破 $10B ARR；ChatGPT 周活 5 亿 |
| OpenAI 年化收入超 $20B | 2025-12 | OpenAI | CFO Sarah Friar 博客（2026-01-18） | 2025 年底里程碑；全年实际收入 $13.07B（Fortune） |
| OpenAI 年化收入超 $40B | 2026-08-13 | OpenAI | 彭博报道 | 2025 年底翻倍；驱动为编码软件、订阅与早期广告业务 |
| Claude Code 年化收入 $2.5B | 2026-02 | Anthropic | SemiAnalysis 经二手来源转述（须标注二手） | 模型发布直接驱动收入的硬证据；Claude Code 周活自 2026-01 翻倍，约占全球公开 GitHub 提交的 4% |
| Cursor ARR 达 $500M | 2025-06 | Anysphere | Financial Times 报道 | 编码工具收入标杆；2024 年底不足 $100M |
| Cursor ARR 达 $1B | 2025-11 | Anysphere | 行业报道（须核一手） | 5 个月翻倍 |

储备：Anthropic run-rate 超 $5B（2025-08，Amodei）；Anthropic run-rate 约 $81B（2026-10-31，S-1/A No.2，据 WSJ）；Cursor ARR $2B（2026-02）；Cursor ARR $4B（2026-06，Forbes）；Manus ARR 破 $1 亿（2025-12-17，Manus 官方博客）。

挂钩设计（见第 6 节）：每道 arr 题的题面写明「前置事件 + 收入结果」，例如「Claude Code GA（2025-05-22）之后，Anthropic run-rate 何时达 $14B」。预测员须同时懂发布节奏与收入转化。

### D. 收购（acquisition，新设，补 9 道）

题集现状：acquisition 类 0 道。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| Google 收 Wiz，$32B 全现金 | 2025-03-18 | Google | Google 官方公告 | Google 史上最大收购；2026-03-11 完成交割 |
| Meta 投 Scale AI $14.3B，换 49% 无投票权股份 | 2025-06-12 | Meta | 路透；Meta 10-Q 记 $13.79B | 估值 $29B；Wang 出任 Meta 首任首席 AI 官；MSL 2025-06-30 成立 |
| OpenAI 收 Jony Ive 的 io，$65 亿全股权 | 2025-05-21 | OpenAI | OpenAI 官方公告 | OpenAI 史上最大收购；已持 23%，再付 $50 亿 |
| OpenAI 收 Windsurf $30 亿告吹；Google 同日付约 $24 亿获非独家授权并聘走 CEO | 2025-07-11 | OpenAI / Google | 路透等报道 | 收购失败本身就是事件；Google 用授权 + 挖人替代收购 |
| xAI 收 X，全股票 | 2025-03-28 | xAI | xAI 官方公告 | xAI $800 亿、X $330 亿股权 / $450 亿含债 |
| SpaceX 收 xAI，全股票 | 2026-02-02 | SpaceX | SpaceX 官方公告 | xAI $2500 亿、合计 $1.25 万亿，史上最大合并 |
| SpaceX 收 Cursor（Anysphere），$60B 全股票 | 2026-06-16 | SpaceX | 行业报道（08-14 说法待核：宣布日与交割日须区分） | 编码工具史上最大收购；Cursor ARR 当时约 $4B |
| Meta 收 Manus，约 $20 亿 | 2025-12-29 | Meta | Meta 官方公告 | Meta 2025 年第五笔 AI 收购；Manus ARR $1.25 亿 |
| 中国发改委叫停 Meta 收 Manus | 2026-04-27 | 中国发改委 | CNBC / CNN / Fortune 报道 | 收购被监管叫停；Meta 2026-06-11 完成业务切割；腾讯牵头财团 2026-08 回购 |

储备：Google 完成收 Wiz 2026-03-11；Cognition 收 Windsurf 剩余部分 2025-07-14（2026-06-02 更名为 Devin Desktop）。

### E. 战略变化与合作（partnership，新设，补 7 道）

题集现状：partnership 类 0 道。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| OpenAI 完成重组为营利性公益公司（PBC） | 2025-10-28 | OpenAI | OpenAI 官方公告 | OpenAI Foundation 持股 26% 约 $1300 亿，微软约 27% 约 $1350 亿，总估值 $5000 亿；微软模型 IP 权延至 2032，AGI 由独立专家组验证，OpenAI 承诺 $2500 亿 Azure 支出 |
| 英伟达拟投 OpenAI 最高 $1000 亿（意向书，10GW，Vera Rubin） | 2025-09-22 | 英伟达 / OpenAI | 双方官方公告 | 史上最大单笔 AI 投资意向；首期 2026 下半年 |
| 英伟达对 OpenAI 投资缩水至 $300 亿股权 | 2026-02-27 | OpenAI | OpenAI $1100 亿轮次披露（2026-03-31 关闭，共 $1220 亿，投后 $8520 亿） | 意向与落地之差本身就是可测事件；黄仁勋 2026-03 称「可能不在计划内」 |
| Anthropic 与 Google、Broadcom 签 TPU 协议 | 2026-04-06 | Anthropic / Google / Broadcom | Anthropic 官方；Broadcom SEC 文件 | 约 3.5GW 下一代 TPU，2027 年上线；同日 Anthropic 披露 run-rate 超 $30B |
| OpenAI 与 AMD 签 6GW 协议 | 2025-10 | OpenAI / AMD | 双方官方公告（确切日待核） | OpenAI 算力来源多元化 |
| OpenAI 与 Google Cloud 合作 | 2025-06 | OpenAI / Google | 双方官方公告（确切日待核） | OpenAI 首次用 Google 云 |
| Meta 成立 Superintelligence Labs（MSL） | 2025-06-30 | Meta | Meta 官方公告 | Wang 领导；Meta AI 战略重组 |

储备：Anthropic 与微软、英伟达签 $30B Azure 协议 2025-11（日期待核）。

### F. 融资（financing 扩充，补 6 道）

题集现状：financing 类 7 道。已有：谷歌投 Anthropic $3 亿（2023-02-03）、亚马逊投 Anthropic 最高 $40 亿（2023-09-25）、xAI $20B Series E（2026-01-06）、软银 $118.7 亿定期贷款（2026-09-14）等。缺：OpenAI 两轮大额融资、Anthropic G/H 轮、CoreWeave IPO、SpaceX IPO。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| OpenAI $40B 轮次关闭，投后 $3000 亿 | 2025-03-31 | OpenAI / 软银 | OpenAI 官方博客；CNBC | 当时史上最大私人融资；软银领投；$180 亿投向 Stargate；第二期 $300 亿以 PBC 重组为条件，2025-12-30 完成最后一期 |
| OpenAI $122B 轮次关闭，投后 $8520 亿 | 2026-03-31 | OpenAI | OpenAI 官方披露 | 史上最大私人融资；含英伟达 $300 亿股权 |
| Anthropic Series G，$30B，投后 $3800 亿 | 2026-02 | Anthropic | Anthropic 官方披露（确切日与金额待核） | 2026 年初大额融资 |
| Anthropic Series H，$65B，投后 $9650 亿 | 2026-05-28 | Anthropic | Anthropic 官方披露 | 史上最大私人融资之一；同日披露 run-rate 超 $47B |
| CoreWeave IPO（纳斯达克） | 2025-03-28 | CoreWeave | 纳斯达克公告（确切日待核） | 首家大型 neocloud 上市 |
| SpaceX IPO 定价 $135（SPCX） | 2026-06-11 | SpaceX | SpaceX S-1 相关材料 | 史上最大 IPO 之一；IPO 后数日即达成收 Cursor 协议 |

储备：xAI $60 亿 Series C（2024-12，日期待核）。

### G. 芯片与算力（blackwell 扩充，补 4 道）

题集现状：blackwell 类 1 道（B200 发布，2024-03-18）。缺：Blackwell Ultra、Rubin、TPU Ironwood、AMD MI400、Ascend 910C、Trainium 3。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| NVIDIA Blackwell Ultra 发布 | 2025-03-18 | 英伟达 | 英伟达 GTC 官方公告（日期待核） | Blackwell 升级版 |
| NVIDIA Vera Rubin 平台发布 | 2026 | 英伟达 | 英伟达官方公告（确切日待核） | 下一代平台；OpenAI $100B 意向书即绑定 Rubin |
| Google TPU Ironwood 发布 | 2025-04-09 | Google | Google Cloud Next 官方公告（日期待核） | 第七代 TPU，推理专用 |
| AMD MI400 / Helios 机架发布 | 2025-06-12 | AMD | AMD Advancing AI 官方公告（日期待核） | AMD 挑战英伟达的旗舰平台 |

储备：华为 Ascend 910C（2025-04，日期待核）；亚马逊 Trainium 3（2025-12，日期待核）。

### H. 存储与供应链（memory，新设，补 4 道）

题集现状：memory 类 0 道。存储涨价是 2025–2026 年 AI 基建的最大成本冲击之一，题集完全缺失。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| 全球存储短缺开始 | 2025-09 | 行业 | Wikipedia 词条；TrendForce | AI 基建需求 + HBM 产能挤占 + 贸易限制 + 厂商主动调产能 |
| 三星与 SK 海力士计划 2026 年 Q1 服务器内存再涨最高 70% | 2026-01-06 | 三星 / SK 海力士 | 韩国经济日报报道 | 2025 年已涨 50%；涨价直接推高数据中心成本 |
| DRAM 合约价 2026 年 Q1 环比涨 90–95% | 2026-03 | TrendForce | TrendForce 报告（确切日待核） | 史上最大单季涨幅；Q2 再涨 58–63% 预期 |
| 美光退出 Crucial 消费品牌，产能全转 AI 数据中心 | 2026-01 | 美光 | 美光官方公告（确切日待核） | 消费级存储让路 AI 的标志性事件 |

储备：2026 年 Q3 全球 DRAM 收入约 $2000 亿、同比 +369%，DDR 收入同比 +500%，三星份额 38%（Counterpoint）。

### I. 前沿数学与基准突破（math，新设，补 5 道）

题集现状：math 类 0 道。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| AlphaProof + AlphaGeometry 2 在 IMO 2024 达银牌标准 | 2024-07-25 | Google DeepMind | DeepMind 官方博客 | 4/6 题，28/42 分，金牌线 29 分；AI 首次在 IMO 达银牌 |
| OpenAI o3 在 ARC-AGI 达 87.5% | 2024-12-20 | OpenAI | OpenAI 官方公告；ARC Prize 确认 | Chollet 称「真正的突破」；ARC-AGI 五年未被攻破的基准 |
| OpenAI 实验推理模型在 IMO 2025 达金牌 | 2025-07-19 | OpenAI | OpenAI 官方公告 | 35/42，5/6 题；自行评分引发争议 |
| Google DeepMind Gemini Deep Think 在 IMO 2025 达金牌（官方确认） | 2025-07-21 | Google DeepMind | DeepMind 官方公告；IMO 主席 Gregor Dolinar 确认 | 35/42；首个官方达金牌线的 AI |
| DeepSeekMath-V2 在 IMO 2025 达金牌（开源） | 2025 | DeepSeek | DeepSeek 官方公告（确切日待核） | 开源模型达金牌 |

储备：Harmonic Aristotle 达金牌；字节 Seed prover 达银牌（延时达金牌）。日期待核。

### J. 华尔街与资本市场（wallstreet，新设，补 4 道）

题集现状：wallstreet 类 0 道。题集有 anthropic_ipo（5 道）与 sec_probe（1 道），但缺华尔街对 AI 的系统性反应。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| 英伟达市值首破 $4 万亿 | 2025-07-09 | 英伟达 | 市场数据（盘中，收盘 $3.974 万亿） | 史上首家 $4 万亿公司 |
| 甲骨文股价单日 +35% | 2025-09-10 | 甲骨文 | 市场数据 | AI 云增长指引引爆股价；OpenAI 与甲骨文签 5 年 $3000 亿算力合同（2025-09，从 $1500 亿翻倍） |
| CoreWeave 股价单日 +14% | 2025-09-30 | CoreWeave | 市场数据 | $142 亿 Meta 合同驱动 |
| 英伟达股价因 DeepSeek R1 单日跌约 20% | 2025-01-27 | 英伟达 | 市场数据（确切日待核） | R1 冲击的华尔街反应；2025-04 关税后跌至 $86.62 |

储备：OpenAI 与甲骨文 5 年 $3000 亿算力合同（2025-09）。

### K. 人才流动（talent，新设，补 3 道）

题集现状：talent 类 0 道。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| Altman 称 Meta 向 OpenAI 员工开 $1 亿签约奖 | 2025-06 | Meta / OpenAI | Altman 公开表态（确切日待核） | 2025 年 AI 人才战的标志性数字 |
| 苹果基础模型负责人 Ruoming Pang 跳槽 Meta | 2025-07 | 苹果 / Meta | 行业报道（确切日待核） | 传超 $2 亿 package |
| Andrew Tulloch 获 Meta 最高 $15 亿 package | 2025-06 | Meta | WSJ 报道（数字有争议，慎用） | 人才战最高价；须标注「报道称」 |

### L. 政策监管（bis_rule 扩充，补 2 道）

题集现状：bis_rule 类 4 道。缺：欧盟 AI 法案、加州 AI 立法。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| 欧盟 AI 法案通用模型义务生效 | 2025-08-02 | 欧盟 | 欧盟官方公告（日期待核） | 全球首部 AI 综合立法进入执行期 |
| 加州 SB 53 签署成法 | 2025-10-13 | 加州 | 加州州长办公室（日期待核） | 美国首部前沿模型透明度立法 |

### M. 多模态 / 视频模型（video，新设，低优先级，补 3 道）

题集现状：video 类 0 道。视频模型属相邻赛道，不属核心，列为低优先级。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| OpenAI Sora 发布 | 2024-12-09 | OpenAI | OpenAI 官方公告（日期待核） | 首个大规模商用视频生成模型 |
| Google Veo 3 发布 | 2025-05-20 | Google | Google I/O 官方公告（日期待核） | 首个带原生音频的视频模型 |
| OpenAI Sora 2 发布 | 2025-09-30 | OpenAI | OpenAI 官方公告（日期待核） | 视频模型第二代 |

### N. 用户里程碑（并入 arr，不另设种类，补 3 道）

题集现状：用户数类 0 道。用户数是收入的前置指标，与 ARR 题配对使用。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| ChatGPT 周活达 5 亿 | 2025-06-09 | OpenAI | OpenAI 官方披露（与 $10B ARR 同日） | 与 ARR 里程碑同日披露 |
| ChatGPT 周活达 8 亿 | 2025-10 | OpenAI | OpenAI 官方披露（确切日待核） | 4 个月增 3 亿 |
| Gemini 应用月活达 7.5 亿 | 2026-03 | Google | Google 官方披露（确切日待核） | Gemini 3.1 Pro 发布同期 |

### O. 社交媒体风向（social，新设，补 8 道）

题集现状：social 类 0 道。

设计限定（先说清楚）：纯粹的“风向”（连续的情绪、热度）做不成干净的题。题集题要一个具体的公开事件、一个日期、一个明确答案。风向本身没有日期、没有对错。所以本类只收“离散的病毒时刻”：一个具体的帖子/直播/截图、一个可测的影响（用户暴涨、产品被迫改、股价动、一个词被造出来）。三类机制：
1. 病毒式采用：社交传播直接拉用户（吉卜力刷屏）。
2. 病毒式反噬：社交批评迫使产品改或停（Gemini 暂停、Gemini 演示造假、Sydney 限制、Devin 拆穿）。
3. 一个帖子/时刻定了一个趋势：造了个词、立了个新基准、逼出了一个结果（vibe coding、Claude 玩宝可梦、Altman 员工联署）。

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| GPT-4o 图片生成上线，吉卜力风图片刷屏；Altman 称 GPU 熔化，ChatGPT 一小时新增 100 万用户 | 2025-03-25 | OpenAI | OpenAI 官方公告；Altman X 帖（03-27「GPUs are melting」、03-31「一小时新增 100 万用户」）；首周 1.3 亿用户生成 7 亿+ 图片 | AI 史上最大社交病毒时刻；社交传播直接变成算力危机与用户暴涨 |
| Google 暂停 Gemini 生成人物图片 | 2024-02-22 | Google | Google X 官方帖；TechCrunch；Engadget | 社交截图（纳粹士兵、开国元勋）引爆批评，Google 被迫停掉功能；Alphabet 股价跌 4.4% |

储备（第二阶段 6 道）：

| 事件 | 日期 | 玩家 | 来源 | 为什么重要 |
|---|---|---|---|---|
| Kevin Roose 与 Bing Sydney 的对话见报，微软随后限制 Bing 聊天 | 2023-02-16 | 微软 | 纽约时报 Roose 专栏；Wikipedia Sydney 词条 | 病毒式对话迫使微软把 Bing 聊天限为每会话 5 轮；AI 失控论的标志性时刻 |
| Google Gemini 演示视频被指造假（实为静帧 + 文字提示，非实时语音） | 2023-12-08 | Google | Bloomberg Parmy Olson；HotHardware；Cointelegraph | 社交媒体拆穿演示造假；Google 承认剪辑，信誉受损 |
| Internet of Bugs 发布视频拆穿 Devin 演示（Upwork 任务未完成、修的是自己造的 bug） | 2024-04-18 | Cognition | Internet of Bugs YouTube；The Pragmatic Engineer 2024-04-18 总结 | 演示视频 3000 万+ 播放后被拆穿；Cognition 承认 Devin「常犯错」；舆论逆转的教科书 |
| Karpathy 在 X 发帖造出「vibe coding」一词 | 2025-02-02 | Karpathy | Karpathy X 原帖；Merriam-Webster 2025-03-01 收词；Collins 2025 年度词 | 一条帖子命名了一个品类；编码 agent 浪潮的舆论起点 |
| Anthropic 在 Twitch 开播 Claude 玩宝可梦（Claude 3.7 Sonnet 玩 Pokémon Red） | 2025-02-25 | Anthropic | Anthropic X 帖；TechCrunch | 病毒式直播基准；15k Twitch 关注，引发 GPT 与 Gemini 跟进直播；宝可梦成 AI 评测新标尺 |
| OpenAI 约 97% 员工联署要求董事会辞职、Altman 回任 | 2023-11-20 | OpenAI | 员工联署信；X 帖；NPR / Moneycontrol 时间线 | 员工在 X 上公开站队，舆论压力逼董事会让步；Altman 2023-11-22 回任 |

不进池（说明原因）：
- ChatGPT 上线 5 天破 100 万用户（2022-12-05）：病毒式采用的源头，但事件本身是产品上线，与模型发布（A 类）重叠。留作 A 类与 social 类的边界示例，不重复计。
- DeepSeek R1 登顶美国 iOS 免费应用榜（2025-01-27）：社交病毒驱动的采用，但 R1 发布已在题集（r1 类）、英伟达跌 17% 已在 J 类。App Store 排名是同一事件的第三个侧面，不另设题。
- FLI「暂停巨型 AI 实验」公开信（2023-03-22）：30,000+ 签名、马斯克联署，传播极广，但属政策倡导，与 L 类（政策监管）重叠。不另设 social 题。

待核：
- Devin 拆穿视频的确切发布日（Internet of Bugs YouTube，2024-04 月；Pragmatic Engineer 总结为 04-18）。以视频发布日为准，补题前须核。
- Altman 员工联署信的公开确切日（2023-11-20 为周一联署日，须核）。

## 4. 第一阶段：补 44 道，到 142 道

原则：先补用户点名的核心缺口（模型发布节奏 + Claude Code / Opus 4.6 + ARR），再补每个新类别的头两道代表题，留尾巴给第二阶段。

| 类别 | 第一阶段题数 | 具体题目（事件） |
|---|---|---|
| A1 Claude | 8 | 3.7 Sonnet 2025-02-24；Sonnet 4.5 2025-09-29；Haiku 4.5 2025-10-15；Opus 4.5 2025-11-24；Opus 4.6 2026-02-05；Sonnet 4.6 2026-02-17；Opus 4.8 2026-05-28；Fable 5 2026-06-09 |
| A2 GPT | 1 | o3 2024-12-20 |
| A3 Gemini | 2 | Gemini 3 Pro 2025-11-18；Gemini 3.1 Pro 2026-03-09 |
| A4 DeepSeek | 3 | R1-0528 2025-05-28；V3.2 2025-12-01；V4 预览 2026-04-24 |
| A5 Qwen | 3 | Qwen3-Coder 2025-07-22；Qwen3.8-Flash-Next 2026-08-26；Qwen4-Max 2026-11-16 |
| A6 Kimi | 3 | K2 2025-07-11；K3 2026-07-16；K3.1 Pro 2026-10-24 |
| A7 Meta | 2 | Llama 4 2025-04-05；Muse Spark 2026-04-08 |
| B agent | 6 | Claude Code 预览 2025-02-24；Claude Code GA 2025-05-22；Grok Bot 2026-08-11；OpenClaw 2026-01-28；WorkBuddy 2026-03-09；Manus 2025-03-06 |
| C arr | 4 | Anthropic $9B 2025-12；Anthropic $30B 2026-04-06；OpenAI $10B 2025-06-09；Claude Code $2.5B 2026-02 |
| D acquisition | 2 | Meta-Scale $14.3B 2025-06-12；Google-Wiz $32B 2025-03-18 |
| E partnership | 2 | OpenAI PBC 重组 2025-10-28；Anthropic TPU 协议 2026-04-06 |
| F financing | 1 | OpenAI $40B 轮次 2025-03-31 |
| G chip | 1 | NVIDIA Rubin 2026 |
| H memory | 1 | 全球存储短缺开始 2025-09 |
| I math | 2 | IMO 2024 银牌 2024-07-25；IMO 2025 金牌（DeepMind）2025-07-21 |
| J wallstreet | 1 | 英伟达市值 $4T 2025-07-09 |
| O social | 2 | 吉卜力风 GPT-4o 图片刷屏 2025-03-25；Gemini 生成人物图片暂停 2024-02-22 |
| 合计 | 44 | 98 + 44 = 142 |

第一阶段后：新种类 10 个（kimi、muse、agent、arr、acquisition、partnership、memory、math、wallstreet、social；talent、video 留第二阶段，policy 为 bis_rule 扩充）。claude 类从 4 道增至 12 道。模型发布类合计从约 34 道增至 56 道。

注：第一阶段 Claude 8 道未含 Opus 4.1、Opus 4.7、Opus 5、Fable 5.2（进第二阶段）。如用户要求第一阶段补齐 Claude 全链（12 道），须从其他类别调出 4 道（建议调出：wallstreet 1 道、chip 1 道、memory 1 道、financing 1 道）。

## 5. 第二阶段：储备池 75 道

- 119 道池减去第一阶段 44 道，剩 75 道。
- 用途：第 11 轮新题、S6 候选、替换弱题（例如第 10 轮审计中发现的弱题）、补齐各条产品线全链。
- 储备池明细：A 类 15 道（Claude 4、GPT 2、Gemini 1、DeepSeek 2、Qwen 1、Kimi 2、Meta 1、其他中国 2）；B 类 8 道；C 类 6 道；D 类 7 道；E 类 5 道；F 类 5 道；G 类 3 道；H 类 3 道；I 类 3 道；J 类 3 道；K 类 3 道；L 类 2 道；M 类 3 道；N 类 3 道；O 类 6 道。
- 第二阶段不自动进题集。每次动用须单独定夺。

## 6. 「发布节奏」怎么变得可测

- 每条模型线补齐发布链。claude 类从 4 道补到 12 道（第一阶段）再到 16 道（第二阶段补齐），覆盖 3.7 → 4 → 4.1 → 4.5 → 4.6 → 4.7 → 4.8 → 5 → 5.5 的完整节奏。预测员须懂「谁家多久发一次、下一代何时来」，而不是只认单个事件。
- 新设 10 个种类（kimi、muse、agent、arr、acquisition、partnership、memory、math、wallstreet、social）。种类数从 35 个增至 45 个（第一阶段后）。
- 衍生指标（不另设题，只作分析维度）：按厂商 × 半年统计发布次数。例如 Anthropic 2025 下半年 4 次模型发布（4.1、4.5 Sonnet、4.5 Haiku、4.5 Opus），2026 上半年 5 次（4.6 Opus、4.6 Sonnet、4.7、4.8、Fable 5）。该指标从题集自身算出，用于衡量预测员是否掌握节奏。
- 种类内时间密度：同一玩家在相邻月份连续发布时，题面须写明「上一代发布于某月」，迫使预测员用节奏推理，而不是只凭记忆。

## 7. 收入 / ARR 挂钩设计

- 新设 arr 种类（第一阶段 4 道，第二阶段再补 6 道）。
- 挂钩方式：每道 arr 题的题面写明前置事件与收入结果的因果链。例如：
  - Claude Code GA（2025-05-22）→ Anthropic run-rate 何时达 $14B（2026-02）。
  - Opus 4.5 发布（2025-11-24）→ Anthropic run-rate 何时达 $9B（2025-12）。
  - Google / Broadcom TPU 协议（2026-04-06）→ 同日披露 run-rate 超 $30B。
  - Anthropic Series H（2026-05-28）→ 同日披露 run-rate 超 $47B。
  - OpenAI $10B ARR（2025-06-09）→ 同日 ChatGPT 周活 5 亿。
- 口径限定：Anthropic run-rate 为公司自报口径（近 28 天消费年化 + 当月订阅 × 12，非 GAAP）。题面须写明口径与来源。OpenAI CRO 对 $30B 口径的异议记为限定，不作题面。
- 二手来源限定：Claude Code $2.5B 年化收入为 SemiAnalysis 经二手来源转述，题面须标注「据 SemiAnalysis 转述」。
- 用户里程碑（N 类）并入 arr 种类，不另设种类。用户数是收入的前置指标，与 ARR 题配对。

## 8. 实施顺序

1. 核实待核日期（见第 9 节）。每道题补进题集前，须有一手来源确认事件与日期。日期只有月份时写 YYYYMM，不拼凑确切日。
2. 第一阶段 A 类（22 道模型发布）。先补用户点名的核心缺口。claude 线优先。
3. 第一阶段 B 类（6 道）+ C 类（4 道）。agent 产品与 ARR 挂钩一起补，收入链完整。
4. 第一阶段 D / E / F / G / H / I / J 类（10 道）+ O 类（2 道）。每个新类别先立两道代表题；社交媒体先立吉卜力刷屏与 Gemini 暂停两道。
5. 全量校验：跑 ./run.sh，题集 140 道全过；审计日期违规、泄题、污染；看板更新（题集 140、轮次列表不变）。
6. 第二阶段储备池不动。等第 11 轮开轮或用户另行定夺。

## 9. 待核实清单（补题前必须先核）

- Grok Build 上线日期：各来源不一（05-14 / 05-25 / 06-05）。以 xAI 官方为准。
- OpenClaw 公开仓库日期：01-25 / 01-28 两说。
- Trae 上线日期：01-19 / 01-20 两说。
- Kimi K3.1 Pro 发布日期：10-23 / 10-24 两说。
- Claude Code 2.0（2026-08-30）：单源，须再核。
- SpaceX 收 Cursor：宣布日 2026-06-16（行业报道）与 08-14 说法并存。须区分宣布日与交割日。
- GPT-5.2 发布确切日（2025-12）。Gemini 2.0 发布日（2024-12-11）。Muse Wonder 发布确切日（2026-10）。GLM-4.5（2025-07-28）、MiniMax M2（2025-10-28）。Meta AI 应用（2025-04-29）。OpenAI 与 AMD 6GW 协议确切日（2025-10）。OpenAI 与 Google Cloud 合作确切日（2025-06）。Anthropic-Microsoft-NVIDIA Azure $30B 协议（2025-11）。Anthropic Series G 金额与日期（2026-02）。CoreWeave IPO 确切日（2025-03-28）。Blackwell Ultra（2025-03-18）、Rubin（2026）、TPU Ironwood（2025-04-09）、AMD MI400（2025-06-12）、Ascend 910C（2025-04）、Trainium 3（2025-12）。DRAM 合约价 Q1 2026 +90–95% 确切日。美光退出 Crucial 确切日（2026-01）。DeepSeekMath-V2 IMO 金牌确切日。英伟达因 R1 跌约 20% 确切日（2025-01-27）。EU AI 法案 GPAI 义务生效（2025-08-02）。加州 SB 53 签署（2025-10-13）。Sora（2024-12-09）、Veo 3（2025-05-20）、Sora 2（2025-09-30）。ChatGPT 周活 8 亿确切日（2025-10）。Gemini 应用月活 7.5 亿确切日（2026-03）。Meta $1 亿签约奖确切日（2025-06）。Ruoming Pang 跳槽确切日（2025-07）。
- 文心 5.0、混元后续、豆包后续：日期未核，不进池。补题前须另查。
- Andrew Tulloch $15 亿 package：数字有争议（WSJ 报道），慎用。建议不作题面数字，只作背景。

## 10. 不进题集的类别

- 诉讼 / 执法类：用户未定，留在种类缺口，不进题集（与此前决定一致）。
- Grok 图像滥用等安全事件：属安全争议事件，无干净的公开事件答案，且与诉讼缺口重叠。建议不进。
- 视频模型（M 类）：属相邻赛道，列为低优先级。是否进题集由用户定。
