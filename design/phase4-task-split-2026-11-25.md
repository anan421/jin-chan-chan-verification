# Phase 4-B 报告：任务拆分（2026-11-25）

- 阶段：Phase 4-B（任务拆分）。
- 日期：2026-11-25。
- 状态：完成。本报告只做分析与文档。
- 本报告不改题集内容，不改账本，不改冻结赛季，不改结算口径。
- 任务文档第 7.2 节把预测任务分五类：主动行为、外部事件、反应、影响、状态。
- Phase 3 报告见 `design/phase3-report-2026-11-25.md`。

## 1. 口径

- 题集：`testset-v7.json`，215 道题，43 种。题号是 0–215，q79 不存在。
- 两份题集副本的题号与题目内容一致，只差文件格式：仓库 `~/workspace/verification/testset-v7.json` 与 `~/workspace/verification-v1-round11/testset-v7.json`。
- 基线：第 11 轮基线重测对照组 C1、C2、C3。基线方法是收紧查资料规则、前瞻指引步骤、界限规则、角色扮演。
- 猜中判定：预测记录的 `kind` 等于题集的 `kind`，即算猜中。判定逻辑见 `score_baseline_v7.py` 第 85–89 行。
- 分数取审计后口径。审计文件是 `runs/baseline-retest-2026-11-22/trial-audit.md` 与 `audit-baseline-v7.json`。
- 审计排除 7 条记录：q30、q31 在三批全排，C2 q1 排。排除原因是猜中靠泄题事实得来。
- 审计后总分：C1 96、C2 104、C3 93，平均 97.67，噪声带 11。原始总分：C1 98、C2 107、C3 95，平均 100.00，噪声带 12。
- 基线得分缺失：0 道。三批各有 215 条记录，题号集合与题集完全一致，无重复，无遗漏。审计文件已核实这一点。
- 分类只看题集的 `event_name` 与 `action` 字段，不看预测记录。

## 2. 分类标准

分类依据是任务文档第 7.2 节的五类定义。账本格式文档 `design/forecast-ledger-schema.md` 第 3.1 节转录了这五类定义。原定义只有一句话。本报告把每类写成可执行的判定条件。

判定顺序是 impact、reaction、external_event、state、active_action。按顺序取第一条命中的类。一道题只归一类。

### 2.1 影响（impact）

- 定义：事件对血量、金币、段位的影响。本题集里指事件的市场或声望后果。
- 判定条件：事件本身是另一事件的后果，且事件名或动作字段写明因果链。后果包括股价涨跌、市值变化、声望受损、被迫改动作。
- 判定条件：事件本身是价格或市值变动，且有写明的触发事件，也归影响。没有触发事件的价格水平不归影响，归状态。

### 2.2 反应（reaction）

- 定义：某玩家对另一事件的反应。
- 判定条件：事件是某玩家针对另一已发生事件做出的回应动作，且回应关系写明。回应包括叫停、限制、暂停、联署要求、被迫评估。
- 判定条件：回应必须有明确的触发事件。没有触发事件的跟进式发布不归反应，归主动行为。

### 2.3 外部事件（external_event）

- 定义：玩家控制之外的事件。
- 判定条件：事件的发生不由任一棋盘玩家决定。包括监管规则发布、立法生效、监管方叫停收购、媒体调查报道发表、第三方指控、权重泄露。

### 2.4 状态（state）

- 定义：某时点的世界状态。
- 判定条件：事件是某时点可观测的数量或状态。包括财报数字、ARR、年化收入、资本开支额与指引、用户量、市值水平、基准分数与奖牌、第三方机构的价格涨幅预期。
- 判定条件：数字本身就是事件内容。预测者须猜中数值或水平是否达到，不须猜玩家做了什么动作。

### 2.5 主动行为（active_action）

- 定义：某玩家主动做的动作。
- 判定条件：事件是某玩家主动做的动作，且不符合 2.1–2.4 节的任一条件。包括发布模型与产品、上线、开源、收购、投资、融资、签约、合作、宣布计划、成立公司或部门、挖人、发帖、辞职。
- 判定条件：本类是默认类。不符合前四类的玩家主动行为都归本类。

### 2.6 边界情况

- 模型发布与产品上线归主动行为，即使发布后有市场反响。反响只写在动作字段里，不改变主类。
- 旗舰发布反响平淡归影响（q23）。发布是例行动作，新闻量在反响上。
- 豆包降价 99.3% 归主动行为（q35）。降价本身是新闻量很大的动作。
- 财报口径的资本开支数字与指引归状态（q10–q19）。公司正式宣布的多年投入计划归主动行为（q55–q57）。
- 收购归主动行为。监管方叫停收购归外部事件（q104 对照 q106）。收购告吹归主动行为（q103）。开价被拒归主动行为（q200）。
- 合作与签约归主动行为。投资意向的落地额归状态（q184 对照 q187）。
- 调查报道发表与立法生效归外部事件。玩家执行监管规则归反应（q5–q7 对照 q8）。
- 演示出错归主动行为（q45）。动作本身就是新闻。
- 融资到手与到账归主动行为（q2、q4）。融资动作完成就是事件。
- 同玩家同事件的多道题按同一标准分类。同一事件分给不同玩家时，各题的类可以不同。分类看事件内容，不看玩家。

### 2.7 无法归类的题

- 无法归类的题：0 道。
- 判定条件覆盖全部 215 道题。没有题需要硬分，没有题进入无法归类清单。

## 3. 五类分数表

分数是审计后口径。平均答对是三批答对数的平均值。正确率等于平均答对除以题数。

| 类 | 题数 | C1 | C2 | C3 | 平均答对 | 正确率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 主动行为（active_action） | 159 | 79 | 88 | 78 | 81.67 | 51.4% |
| 外部事件（external_event） | 12 | 0 | 1 | 1 | 0.67 | 5.6% |
| 反应（reaction） | 5 | 1 | 1 | 1 | 1.00 | 20.0% |
| 影响（impact） | 7 | 3 | 2 | 2 | 2.33 | 33.3% |
| 状态（state） | 32 | 13 | 12 | 11 | 12.00 | 37.5% |
| 合计 | 215 | 96 | 104 | 93 | 97.67 | 45.4% |

- 审计只改主动行为一类。原始分下主动行为三批是 81、91、80，平均 84.00。其余四类原始分与审计后相同。
- 主动行为平均分从 84.00 降到 81.67，原因是 q30、q31 审计排除。两道题原始三批全中，猜中靠泄题事实，审计后不计分。
- 外部事件平均 0.67 道只来自 q58 一题。q58 在 C2、C3 猜中，在 C1 猜错。其余 11 道题三批全错。
- 反应 5 道、影响 7 道、外部事件 12 道，样本小。一道题改动正确率很大。比较这三类时须看题数，不只看正确率。
- 状态类内部分化大。资本开支 10 道全对（30 条记录全对）。ARR 13 道只对 2 条记录（q123 两批）。数学 5 道只对 1 条记录（q175 一批）。
- 分数按种类猜中计，不按事件细节猜中计。q3 与 q23 的 3/3 只表示种类猜中，不表示基线猜中跌幅或反响。影响类分数因此偏高估计。q179 的 3/3 同理，只表示种类 memory 猜中。

## 4. 每类最弱的三道题

选取规则：在 0/3 的题里选三道，错因各不相同。括号里注明该类 0/3 的题数。错因来自预测记录的 `reason` 与 `forecast_prop` 字段。

### 4.1 主动行为（0/3 共 58 道）

| 题号 | 事件 | 错因 |
| --- | --- | --- |
| q99 | Google 收 Wiz，$32B 全现金 | 三批全猜 Gemini 新版本。谷歌历史无收购先兆。基线只顺玩家最常做的种类推。 |
| q109 | Claude Code 有限研究预览上线 | 三批全猜 Claude 新版本。agent 是新品类，历史无先兆。基线分不清新品类发布与模型迭代。 |
| q209 | OpenAI Sora 发布 | 三批各猜融资、订阅、agent。视频是新品类，Sora 无先兆。三批猜了三个不同方向，全错。 |

- q30 与 q31 不在上表里。两道题原始三批全中，审计排除后记 0 分。排除原因是猜中靠泄题事实，不是基线猜错。

### 4.2 外部事件（0/3 共 11 道）

| 题号 | 事件 | 错因 |
| --- | --- | --- |
| q5 | BIS remote-access rule published（阿里） | 三批猜通义新动作或资本开支。玩家历史无监管信号。基线无外部信息通道。 |
| q61 | NYT Alice Huang / MSS investigation published（华为） | 三批猜昇腾芯片动作。调查发表不在玩家动作线里。基线只看玩家历史。 |
| q192 | Google Gemini 演示视频被指造假 | 三批猜 Gemini 发布。被指造假是第三方指控，不在玩家动作线里。基线猜发布，事件是指控。 |

### 4.3 反应（0/3 共 3 道，全类最弱题就是这三道）

| 题号 | 事件 | 错因 |
| --- | --- | --- |
| q190 | 微软限制 Bing 聊天（Kevin Roose 对话见报后） | 三批猜扩大对 OpenAI 投资。基线不看触发事件，只顺玩家动作线。 |
| q191 | OpenAI 约 97% 员工联署要求董事会辞职、Altman 回任 | 三批猜 ChatGPT 新功能或新模型。联署是内部治理反应，不在产品线上。 |
| q193 | Google 暂停 Gemini 生成人物图片 | 两批猜 Gemini 迭代，一批猜资本开支。暂停是回应批评的动作。基线不建触发-反应链。 |

### 4.4 影响（0/3 共 4 道）

| 题号 | 事件 | 错因 |
| --- | --- | --- |
| q74 | SEC 调查报道，恐慌卖出（英伟达） | 三批猜 Megaspeed、Blackwell、出口管制。基线猜玩家下一步动作，不猜市场后果。 |
| q212 | 英伟达股价因 DeepSeek R1 单日跌约 17% | 三批猜 Blackwell 出货。基线猜芯片供给线，不猜 R1 冲击造成的股价后果。 |
| q215 | CoreWeave 股价单日涨约 14% | 三批猜收购。玩家无历史。基线按业务处境猜收购，不猜股价后果。 |

- 影响类第 4 道 0/3 的题是 q197（吉卜力风图片刷屏）。三批猜 ChatGPT 新功能或星门后续。产品部分猜对方向，刷屏后果没有猜。

### 4.5 状态（0/3 共 19 道）

| 题号 | 事件 | 错因 |
| --- | --- | --- |
| q121 | Cursor ARR 达 $500M | 两批猜 agent 产品，一批猜融资。基线不猜数字，只猜动作种类。 |
| q127 | OpenAI 年化收入超 $20B | 三批猜开放权重模型、融资、合作。基线不猜收入数字，只猜动作种类。 |
| q171 | AlphaProof + AlphaGeometry 2 在 IMO 2024 达银牌标准 | 三批猜 Gemini 新版本。基线不猜基准成绩，只猜模型迭代。 |

## 5. 每类下一步最值得试的方法方向

- 主动行为：为每名玩家建动作转移模型，用历史动作序列估计下一动作种类的概率，不只用最常做的种类。
- 外部事件：建外部信号通道，监视监管机构、立法日程与主流媒体调查报道，不只看玩家历史。
- 反应：建触发-反应链，先识别触发事件，再查该玩家过去对同类触发事件的反应。
- 影响：建事件-市场反应模型，用同类事件过去的价格与声望变动估计本次后果的方向与幅度。
- 状态：建数量外推模型，用收入、用户量与基准成绩的历史序列外推下一时点的数值，不猜动作种类。

## 6. 附录：215 道题逐题分类表

| 题号 | 种类（kind） | 玩家 | 事件 | 分类 |
| --- | --- | --- | --- | --- |
| q0 | anthropic_ipo | ANTH | S-1/A No.2: ~$900.9B compute commitments | 主动行为 |
| q1 | anthropic_ipo | ANTH | Anthropic files public S-1 | 主动行为 |
| q2 | anthropic_ipo | ANTH | 分阶段募资到手。绿鞋后合计口径见本轮说明 | 主动行为 |
| q3 | anthropic_ipo | ANTH | 上市次日跌 8.5% | 影响 |
| q4 | anthropic_ipo | ANTH | 募资已到账。现金垫最厚 | 主动行为 |
| q5 | bis_rule | ALI | BIS remote-access rule published | 外部事件 |
| q6 | bis_rule | TSMC | BIS remote-access rule published | 外部事件 |
| q7 | bis_rule | BYTE | BIS remote-access rule published | 外部事件 |
| q8 | bis_rule | TSMC | 台积电叫停 16nm 及以下中国客户订单 | 反应 |
| q9 | blackwell | NVDA | Blackwell B200 发布（GTC 2024） | 主动行为 |
| q10 | capex | AMZN | 亚马逊 Q4 2023 财报电话会：CFO 称 2024 年资本开支将上升 | 状态 |
| q11 | capex | GOOG | Alphabet Q4 2023 财报：Q4 资本开支 110 亿美元，2024 年将显著高于 2023 年 | 状态 |
| q12 | capex | META | Meta Q4/FY2023 财报：2024 年资本开支指引上调至 300-370 亿美元 | 状态 |
| q13 | capex | MSFT | 微软 FY24 Q2 财报：资本开支 115 亿美元，指引下季大幅上调 | 状态 |
| q14 | capex | MSFT | 微软 FY25 Q1 财报：资本开支 200 亿美元 | 状态 |
| q15 | capex | ALI | Alibaba Q2 FY2027 earnings: capex +60% to RMB 50.48B | 状态 |
| q16 | capex | BIDU | Baidu Q3 2026 earnings: capex RMB 7.35B (+116% YoY) | 状态 |
| q17 | capex | BYTE | Bloomberg: ByteDance weighing up to $70B 2026 capex | 状态 |
| q18 | capex | TCE | Tencent Q3 2026 earnings: capex +527% | 状态 |
| q19 | capex | AMZN | 亚马逊 Q3 财报：Q3 现金资本开支 759 亿美元，全年指引约 2200 亿美元 | 状态 |
| q20 | chatgpt | OAI | GPT-4发布 | 主动行为 |
| q21 | chatgpt | OAI | GPT-4o 发布 | 主动行为 |
| q22 | chatgpt | OAI | o1-preview 发布 | 主动行为 |
| q23 | chatgpt | OAI | 旗舰发布反响平淡 | 影响 |
| q24 | chatgpt | OAI | OpenAI 发布 GPT-6.2 Astra 与 Sol | 主动行为 |
| q25 | claude | ANTH | Claude 1发布 | 主动行为 |
| q26 | claude | ANTH | Claude 2发布 | 主动行为 |
| q27 | claude | ANTH | Claude 3 发布（Opus/Sonnet/Haiku） | 主动行为 |
| q28 | claude | ANTH | Claude Opus 4 / Sonnet 4 released | 主动行为 |
| q29 | colossus | MUSK | xAI 宣布 Colossus 落户孟菲斯 | 主动行为 |
| q30 | datacenter | BYTE | 火山引擎宣布自有园区计划 | 主动行为 |
| q31 | datacenter | META | 宣布曼哈顿规模园区计划 | 主动行为 |
| q32 | datacenter | ALI | 广州首个真武国产万卡智算集群投产运营 | 主动行为 |
| q33 | doubao | BYTE | 豆包App上线 | 主动行为 |
| q34 | doubao | BYTE | Doubao-Seed-1.6 announced | 主动行为 |
| q35 | doubao_price_war | BYTE | 火山引擎发布豆包大模型家族并降价 99.3%，引爆价格战 | 主动行为 |
| q36 | energy | MSFT | 三哩岛核电合同。保电力 | 主动行为 |
| q37 | energy | MUSK | 自建燃气电厂抢时间 | 主动行为 |
| q38 | financing | ANTH | 谷歌3亿美元投资Anthropic | 主动行为 |
| q39 | financing | AMZN | 亚马逊投资Anthropic最高40亿美元 | 主动行为 |
| q40 | financing | MUSK | 债务加股权双线融资。最累 | 主动行为 |
| q41 | financing | ORCL | 约 380 亿美元债务包挂单 | 主动行为 |
| q42 | financing | MUSK | xAI $20B Series E closes | 主动行为 |
| q43 | financing | SFTB | 软银 118.7 亿美元定期贷款（为 OpenAI 投资融资） | 主动行为 |
| q44 | financing | ORCL | 甲骨文宣布 OpenAI 基建合同融资已全部落实 | 主动行为 |
| q45 | gemini | GOOG | Bard巴黎发布会演示出错 | 主动行为 |
| q46 | gemini | GOOG | Gemini 1.0发布 | 主动行为 |
| q47 | gemini | GOOG | Gemini 1.5 Pro 发布（100 万 token 上下文） | 主动行为 |
| q48 | gemini | GOOG | Gemini 2.5 Pro/Flash GA | 主动行为 |
| q49 | gemini | GOOG | Google 发布 Gemini 4 Neon | 主动行为 |
| q50 | huang_resign | NVDA | CEO 辞职。单轮重扣 | 主动行为 |
| q51 | hunyuan | TCE | 混元大模型发布 | 主动行为 |
| q52 | hunyuan | TCE | 混元 DiT 开源 | 主动行为 |
| q53 | hunyuan | TCE | 混元 Turbo 发布 | 主动行为 |
| q54 | hunyuan | TCE | Hunyuan-A13B released | 主动行为 |
| q55 | invest_plan | TSMC | 台积电宣布亚利桑那投资增至 400 亿美元、建第二座晶圆厂 | 主动行为 |
| q56 | invest_plan | ALI | 阿里宣布 3800 亿元三年投入计划 | 主动行为 |
| q57 | invest_plan | TCE | 腾讯宣布重投入期。利润换人口 | 主动行为 |
| q58 | llama | META | Llama 1权重种子泄露 | 外部事件 |
| q59 | llama | META | Llama 2开源发布 | 主动行为 |
| q60 | llama | META | Llama 3 发布（8B/70B） | 主动行为 |
| q61 | megaspeed | HUAWEI | NYT Alice Huang / MSS investigation published | 外部事件 |
| q62 | megaspeed | ALI | NYT investigation: Alibaba is Megaspeed's customer and financial backer | 外部事件 |
| q63 | megaspeed | NVDA | FT 调查：Aivres–Megaspeed 46 亿美元芯片通道 | 外部事件 |
| q64 | msft_invest | MSFT | 微软-OpenAI多年数十亿美元投资宣布 | 主动行为 |
| q65 | musk_table | MUSK | 马斯克提出以每股 54.20 美元收购推特 | 主动行为 |
| q66 | musk_table | MUSK | 马斯克联署呼吁暂停训练半年公开信 | 主动行为 |
| q67 | overseas_rental | BYTE | 抢租海外算力报道的主角之一 | 主动行为 |
| q68 | pangu | HUAWEI | 盘古3.0发布 | 主动行为 |
| q69 | pangu | HUAWEI | Pangu 5.5 released at HDC | 主动行为 |
| q70 | r1 | AMZN | R1 on Amazon Bedrock Marketplace and SageMaker JumpStart | 主动行为 |
| q71 | r1 | DPSK | R1 released | 主动行为 |
| q72 | r1 | HUAWEI | Huawei Cloud + SiliconFlow launch R1/V3 on Ascend Cloud | 主动行为 |
| q73 | r1 | TCE | Tencent Cloud deploys R1 on HAI (one-click) | 主动行为 |
| q74 | sec_probe | NVDA | SEC 调查报道。恐慌卖出 | 影响 |
| q75 | spacex_xai | MUSK | xAI宣布成立 | 主动行为 |
| q76 | spacex_xai | MUSK | Grok上线（先向部分测试者开放） | 主动行为 |
| q77 | spacex_xai | MUSK | Grok-1.5 发布 | 主动行为 |
| q78 | spacex_xai | MUSK | Grok 4 released | 主动行为 |
| q80 | stargate | MSFT | Stargate announced at White House; Microsoft exclusivity loosened | 主动行为 |
| q81 | stargate | MSFT | 星门被迫跟投评估 | 反应 |
| q82 | stargate | OAI | 星门绕开微软独家。羁绊松动 | 主动行为 |
| q83 | stargate | ORCL | 星门执行人落位。声量暴涨 | 主动行为 |
| q84 | stargate | SFTB | 星门金主落位。史上最大下注 | 主动行为 |
| q85 | stargate | ORCL | OpenAI confirms $30B/yr Oracle deal (4.5 GW Stargate) | 主动行为 |
| q86 | tongyi | ALI | 通义千问发布（企业邀测） | 主动行为 |
| q87 | tongyi | ALI | Qwen-7B与Qwen-7B-Chat开源 | 主动行为 |
| q88 | tongyi | ALI | Qwen-72B与Qwen-1.8B开源 | 主动行为 |
| q89 | tongyi | ALI | Qwen1.5 发布 | 主动行为 |
| q90 | tongyi | ALI | Qwen2.5 发布（云栖大会，100+ 模型开源） | 主动行为 |
| q91 | tongyi | ALI | Qwen3 released | 主动行为 |
| q92 | v3 | DPSK | DeepSeek-V3 发布（671B MoE，训练成本 557.6 万美元） | 主动行为 |
| q93 | v3 | DPSK | 新版模型编程场景跟进 | 主动行为 |
| q94 | wenxin | BIDU | 百度发布文心一格 | 主动行为 |
| q95 | wenxin | BIDU | 百度官宣文心一言，3 月发布 | 主动行为 |
| q96 | wenxin | BIDU | 文心一言发布（邀测） | 主动行为 |
| q97 | wenxin | BIDU | Baidu announces Ernie Bot free from Apr 1 | 主动行为 |
| q98 | wenxin | BIDU | Ernie 4.5 open-sourced | 主动行为 |
| q99 | acquisition | GOOG | Google 收 Wiz，$32B 全现金 | 主动行为 |
| q100 | acquisition | MUSK | xAI 收 X，全股票 | 主动行为 |
| q101 | acquisition | OAI | OpenAI 收 Jony Ive 的 io，$65 亿全股权 | 主动行为 |
| q102 | acquisition | META | Meta 投 Scale AI $14.3B，换 49% 无投票权股份 | 主动行为 |
| q103 | acquisition | OAI | OpenAI 收 Windsurf $30 亿告吹 | 主动行为 |
| q104 | acquisition | META | Meta 收 Manus，约 $20 亿 | 主动行为 |
| q105 | acquisition | MUSK | SpaceX 收 xAI，全股票 | 主动行为 |
| q106 | acquisition | META | 中国发改委叫停 Meta 收 Manus | 外部事件 |
| q107 | acquisition | MUSK | SpaceX 收 Cursor，$60B 全股票 | 主动行为 |
| q108 | agent | BYTE | 字节 Trae 上线 | 主动行为 |
| q109 | agent | ANTH | Claude Code 有限研究预览上线 | 主动行为 |
| q110 | agent | MANUS | Manus 邀测上线 | 主动行为 |
| q111 | agent | ANTH | Claude Code 正式 GA | 主动行为 |
| q112 | agent | OAI | ChatGPT Atlas 发布 | 主动行为 |
| q113 | agent | BYTE | TRAE SOLO GA | 主动行为 |
| q114 | agent | GOOG | Google Antigravity 公开预览 | 主动行为 |
| q115 | agent | ANTH | Claude Cowork 研究预览上线 | 主动行为 |
| q116 | agent | TCE | 腾讯 WorkBuddy 公开上线 | 主动行为 |
| q117 | agent | MUSK | Grok Build 早期 beta 上线 | 主动行为 |
| q118 | agent | TCE | 腾讯 CodeBuddy NPC 发布 | 主动行为 |
| q119 | agent | MUSK | Grok Bot 早期 beta 上线 | 主动行为 |
| q120 | agent | OPENCLAW | OpenClaw 2.0 发布 | 主动行为 |
| q121 | arr | CURSOR | Cursor ARR 达 $500M | 状态 |
| q122 | arr | OAI | ChatGPT 周活达 5 亿 | 状态 |
| q123 | arr | OAI | OpenAI ARR 达 $10B | 状态 |
| q124 | arr | OAI | ChatGPT 周活达 8 亿 | 状态 |
| q125 | arr | CURSOR | Cursor ARR 达 $1B | 状态 |
| q126 | arr | ANTH | Anthropic run-rate 达 $9B | 状态 |
| q127 | arr | OAI | OpenAI 年化收入超 $20B | 状态 |
| q128 | arr | ANTH | Anthropic run-rate 达 $14B | 状态 |
| q129 | arr | ANTH | Claude Code 年化收入 $2.5B | 状态 |
| q130 | arr | GOOG | Gemini 应用月活达 7.5 亿 | 状态 |
| q131 | arr | ANTH | Anthropic run-rate 超 $30B | 状态 |
| q132 | arr | ANTH | Anthropic run-rate 超 $47B | 状态 |
| q133 | arr | OAI | OpenAI 年化收入超 $40B | 状态 |
| q134 | bis_rule | EU | 欧盟 AI 法案通用模型义务生效 | 外部事件 |
| q135 | bis_rule | CALIF | 加州 SB 53 签署成法 | 外部事件 |
| q136 | blackwell | NVDA | NVIDIA Blackwell Ultra 发布 | 主动行为 |
| q137 | blackwell | GOOG | Google TPU Ironwood 发布 | 主动行为 |
| q138 | blackwell | AMD | AMD MI400 / Helios 机架预览发布 | 主动行为 |
| q139 | blackwell | NVDA | NVIDIA Vera Rubin 平台发布 | 主动行为 |
| q140 | chatgpt | OAI | OpenAI o3 发布 | 主动行为 |
| q141 | chatgpt | OAI | GPT-5.1 推出 | 主动行为 |
| q142 | chatgpt | OAI | GPT-5.2 发布 | 主动行为 |
| q143 | claude | ANTH | Claude 3.7 Sonnet 发布 | 主动行为 |
| q144 | claude | ANTH | Claude Opus 4.1 发布 | 主动行为 |
| q145 | claude | ANTH | Claude Sonnet 4.5 发布 | 主动行为 |
| q146 | claude | ANTH | Claude Haiku 4.5 发布 | 主动行为 |
| q147 | claude | ANTH | Claude Opus 4.5 发布 | 主动行为 |
| q148 | claude | ANTH | Claude Opus 4.6 发布 | 主动行为 |
| q149 | claude | ANTH | Claude Sonnet 4.6 发布 | 主动行为 |
| q150 | claude | ANTH | Claude Opus 4.7 发布 | 主动行为 |
| q151 | claude | ANTH | Claude Opus 4.8 发布 | 主动行为 |
| q152 | claude | ANTH | Claude Fable 5 发布 | 主动行为 |
| q153 | claude | ANTH | Claude Opus 5 发布 | 主动行为 |
| q154 | claude | ANTH | Claude Fable 5.2 发布 | 主动行为 |
| q155 | financing | CRWV | CoreWeave IPO，纳斯达克上市 | 主动行为 |
| q156 | financing | OAI | OpenAI $40B 轮次关闭，投后 $3000 亿 | 主动行为 |
| q157 | financing | ANTH | Anthropic Series G 融资 $30B，投后 $3800 亿 | 主动行为 |
| q158 | financing | OAI | OpenAI $122B 轮次关闭，投后 $8520 亿 | 主动行为 |
| q159 | financing | ANTH | Anthropic Series H 融资 $65B，投后 $9650 亿 | 主动行为 |
| q160 | financing | MUSK | SpaceX IPO 定价 $135 | 主动行为 |
| q161 | gemini | GOOG | Gemini 2.0 发布 | 主动行为 |
| q162 | gemini | GOOG | Gemini 3 Pro 发布 | 主动行为 |
| q163 | gemini | GOOG | Gemini 3.1 Pro 发布 | 主动行为 |
| q164 | glm | ZHIPU | GLM-4.5 发布 | 主动行为 |
| q165 | kimi | KIMI | Kimi K2 发布 | 主动行为 |
| q166 | kimi | KIMI | Kimi K2 Thinking 发布 | 主动行为 |
| q167 | kimi | KIMI | Kimi K2.5 发布 | 主动行为 |
| q168 | kimi | KIMI | Kimi K3 发布 | 主动行为 |
| q169 | kimi | KIMI | Kimi K3.1 Pro 发布 | 主动行为 |
| q170 | llama | META | Llama 4 Scout / Maverick 发布 | 主动行为 |
| q171 | math | GOOG | AlphaProof + AlphaGeometry 2 在 IMO 2024 达银牌标准 | 状态 |
| q172 | math | OAI | OpenAI o3 在 ARC-AGI 达 87.5% | 状态 |
| q173 | math | OAI | OpenAI 实验推理模型在 IMO 2025 达金牌 | 状态 |
| q174 | math | GOOG | Google DeepMind Gemini Deep Think 在 IMO 2025 达金牌 | 状态 |
| q175 | math | DPSK | DeepSeekMath-V2 在 IMO 2025 达金牌 | 状态 |
| q176 | memory | SAMSUNG | 全球存储短缺开始 | 状态 |
| q177 | memory | MICRON | 美光退出 Crucial 消费品牌，产能全转 AI 数据中心 | 主动行为 |
| q178 | memory | SAMSUNG | 三星与 SK 海力士计划 2026 年 Q1 服务器内存再涨最高 70% | 主动行为 |
| q179 | memory | SAMSUNG | DRAM 合约价 2026 年 Q1 环比涨 90–95%（TrendForce 上调预期） | 状态 |
| q180 | minimax | MINIMAX | MiniMax M2 发布 | 主动行为 |
| q181 | muse | META | Muse Spark 发布 | 主动行为 |
| q182 | muse | META | Muse Wonder 发布 | 主动行为 |
| q183 | partnership | META | Meta 成立 Superintelligence Labs（MSL） | 主动行为 |
| q184 | partnership | NVDA | 英伟达拟投 OpenAI 最高 $1000 亿 | 主动行为 |
| q185 | partnership | OAI | OpenAI 与 AMD 签 6GW 协议 | 主动行为 |
| q186 | partnership | OAI | OpenAI 完成重组为营利性公益公司（PBC） | 主动行为 |
| q187 | partnership | NVDA | 英伟达对 OpenAI 投资缩水至 $300 亿股权 | 状态 |
| q188 | partnership | ANTH | Anthropic 与 Google、Broadcom 签 TPU 协议 | 主动行为 |
| q189 | r1 | DPSK | DeepSeek R1-0528 发布 | 主动行为 |
| q190 | social | MSFT | Kevin Roose 与 Bing Sydney 对话见报，微软随后限制 Bing 聊天 | 反应 |
| q191 | social | OAI | OpenAI 约 97% 员工联署要求董事会辞职、Altman 回任 | 反应 |
| q192 | social | GOOG | Google Gemini 演示视频被指造假 | 外部事件 |
| q193 | social | GOOG | Google 暂停 Gemini 生成人物图片 | 反应 |
| q194 | social | COGNITION | Internet of Bugs 发布视频拆穿 Devin 演示 | 外部事件 |
| q195 | social | KARPATHY | Karpathy 在 X 发帖造出“vibe coding”一词 | 主动行为 |
| q196 | social | ANTH | Anthropic 在 Twitch 开播 Claude 玩宝可梦 | 主动行为 |
| q197 | social | OAI | GPT-4o 图片生成上线，吉卜力风图片刷屏 | 影响 |
| q198 | talent | META | Altman 称 Meta 向 OpenAI 员工开 $1 亿签约奖 | 主动行为 |
| q199 | talent | META | 苹果基础模型负责人 Ruoming Pang 跳槽 Meta | 主动行为 |
| q200 | talent | META | 据 WSJ 报道 Meta 向 Andrew Tulloch 开出最高 $15 亿 package，Tulloch 拒绝 | 主动行为 |
| q201 | tongyi | ALI | Qwen3-Coder 发布 | 主动行为 |
| q202 | tongyi | ALI | Qwen3.8-Flash-Next 发布 | 主动行为 |
| q203 | tongyi | ALI | Qwen3.8-Omni-Flash 发布 | 主动行为 |
| q204 | tongyi | ALI | Qwen4-Max 上线 | 主动行为 |
| q205 | v3 | DPSK | DeepSeek V3.2 发布 | 主动行为 |
| q206 | v3 | DPSK | DeepSeek V4 预览发布 | 主动行为 |
| q207 | v3 | DPSK | DeepSeek V4-Pro GA | 主动行为 |
| q208 | v3 | DPSK | DeepSeek V4.1 Flash 发布 | 主动行为 |
| q209 | video | OAI | OpenAI Sora 发布 | 主动行为 |
| q210 | video | GOOG | Google Veo 3 发布 | 主动行为 |
| q211 | video | OAI | OpenAI Sora 2 发布 | 主动行为 |
| q212 | wallstreet | NVDA | 英伟达股价因 DeepSeek R1 单日跌约 17% | 影响 |
| q213 | wallstreet | NVDA | 英伟达市值首破 $4 万亿 | 状态 |
| q214 | wallstreet | ORCL | 甲骨文股价单日涨约 35% | 影响 |
| q215 | wallstreet | CRWV | CoreWeave 股价单日涨约 14% | 影响 |

## 7. 局限

- 分数按种类猜中计，不按事件细节猜中计。第 1 节写明判定逻辑，第 3 节写明偏高估计的两处。
- 反应 5 道、影响 7 道，样本小。分数波动大。
- 分类只看题集文字，不看预测记录。分类由一名工人一次完成，无第二人独立复核。
- q30、q31 的审计排除使主动行为平均分降 2.33 道。结论方向不变：主动行为仍是五类里最强的一类。

## 8. 来源文件

- 题集：`~/workspace/verification/testset-v7.json`。
- 打分：`~/workspace/verification-v1-round11/runs/baseline-retest-2026-11-22/predictions/score-baseline-v7.json`。
- 审计：`~/workspace/verification-v1-round11/runs/baseline-retest-2026-11-22/trial-audit.md`、`audit-baseline-v7.json`。
- 预测记录：`~/workspace/verification-v1-round11/runs/baseline-retest-2026-11-22/predictions/predictions-*.json`，共 93 个文件，645 条记录。
- 分类定义：`~/workspace/verification/design/forecast-ledger-schema.md` 第 3.1 节。
- 第 11 轮报告：`~/workspace/verification-v1-round11/design/round11-vision11-report.md`。