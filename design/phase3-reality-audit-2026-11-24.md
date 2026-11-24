# Phase 3-A 核对附录：现实层（2026-11-24）

- 阶段：Phase 3-A（现实层）
- 日期：2026-11-25
- 账本：`forecasts/ledger.json`（schema 1.0，4 条预测，1 条结算）
- 账本状态：本次只读账本。未改账本。未改 `data.json`。未改冻结赛季。未改结算口径。
- 核对范围：预测证据 21 条，结算证据 1 条。合计 22 条。
- 核对方法：公开网络检索。检索日 2026-11-25。

## 1. 现实层的定义

### 1.1 什么算一条事实

一条事实是可观测、可定位、可独立复核的陈述。它含四个要素：主体、动作或状态、时间、来源。四个要素缺一不可。缺少任一要素的主张不是事实，是判断。

### 1.2 账本里的一条主张怎样对应一条外部事实

账本每条 `excerpt` 是一条主张。核对时先把主张拆为最小可核查单元。每个单元对应一个外部事实。对应关系写进第 2 节每条的核对方法。主张含多个单元时，全部单元成立才算已核实。任一单元被否定，整条记被反驳。单元无法定位，整条记未核实。

### 1.3 核验梯度

| 结果 | 中文 | 含义 |
| --- | --- | --- |
| `verified` | 已核实 | 一手来源，或权威二手来源，直接支持主张的全部要素。 |
| `unverified` | 未核实 | 未找到支持来源。或主张无可定位的单一事实。 |
| `contradicted` | 被反驳 | 来源直接否定主张的任一要素。或来源本身不可信。 |

被反驳的证据项不得作为支撑主张的唯一证据。被反驳的证据项须先修正主张，再重新核实。修正走版本链。本附录不改账本。

### 1.4 什么来源算一手来源，什么不算

一手来源是发布机构自身发布的原始记录。包括：政府公报（Federal Register）、监管文件、公司财报与法说会记录、官方博客与公告、机构致函原件。

二手来源是独立新闻机构对一手来源的报道。包括：Reuters、Financial Times 等机构的报道。二手来源可作核实依据。关键数字须与一手来源一致，才算已核实。本附录注明每条核实所用的来源是一手还是二手。

下列来源不算独立核实：转述摘要平台、社交媒体帖子、匿名聚合文章、角色扮演源文档。角色扮演源文档是主张的出处，不是独立核实。模型生成的文字不是来源。

### 1.5 时间规则

预测证据的事实须在信息截止日（2026-11-22）之前成立，才可支撑预测。截止日之后发生的事实只能核实结算，不能回填为预测证据。截止日之后发表的报道可以转述截止日之前的事实。核实时区分报道日期与事实日期。

### 1.6 否定主张的核实方法

“未列入”类否定主张用两条间接证据核实：截止日前的公开报道称仍未列入，且首次列入发生在截止日后。直接查阅截止日当日的清单快照是更强的方法。本次未做到直接查阅，相关条目标注为间接核实。

## 2. 逐条核对

账本原文一字未改。来源标识只写公开查到的机构、日期与可定位的标识。没有可定位标识的，写“无”。没有查到的，写未核实。

### 2.1 S6-FC-01（7 条）

#### FC-01-E1

- 账本原文：“BIS 远程接入规则 11-16 发布、11-19 生效。”
- 账本标注：`verified`。
- 核对结果：已核实。
- 来源标识：美国商务部产业安全局（BIS），临时最终规则《Addressing Remote Access to Advanced Semiconductors》，Federal Register 文件号 2026-23529（91 FR 74970）。BIS 发布 2026-11-16。Federal Register 刊登 2026-11-19。生效 2026-11-19。
- 来源地址：`https://regulations.justia.com/regulations/fedreg/2026/11/19/2026-23529.html`（Federal Register 文本转载）；`https://www.willkie.com/publications/2026/11/bis-moves-to-close-the-remote-access-gap-for-advanced-chips`（Willkie 客户简报，2026-11-18）。
- 核对方法：读 Federal Register 文本。读 Willkie 与 Morrison Foerster 客户简报。三方日期一致。
- 备注：“11-16 发布”指 BIS 发布规则文本，不是 Federal Register 刊登日。刊登日是 11-19。摘录未区分两个日期，但两个日期本身都对。本条维持已核实。

#### FC-01-E2

- 账本原文：“Megaspeed 未列入实体清单。”
- 账本标注：`unverified`。`published_at` 为空。`source_url` 为空。
- 核对结果：已核实（间接核实）。
- 来源标识：BIS 实体清单新增记录。Megaspeed 列入发生在 2026-11-23（Federal Register 文件号 2026-23999）。2026-11-22 前多家公开报道称 Megaspeed 仍未列入。
- 来源地址：`https://www.straitstimes.com/business/economy/megaspeed-on-us-blacklist-what-this-means-for-the-operations-of-the-spore-based-firm`（The Straits Times，2026-11-24 报道，称 11-23 列入）；`https://finance.biggo.com/news/83ca8f44-9ec6-4a3e-b36e-05ac2e47f5a9`（BigGo Finance 转述 Financial Times，2026-11-12 前后，称 Megaspeed 仍未列入）。
- 核对方法：间接核实。按第 1.6 节方法核实。本次未直接查阅 2026-11-22 当日的实体清单快照。

#### FC-01-E3

- 账本原文：“Bessent 10 天通牒约 11-25 到期。”
- 账本标注：`unverified`。`published_at` 为空。`source_url` 为空。
- 核对结果：已核实。
- 来源标识：美国财政部长 Scott Bessent，Fox News 访谈，2026-11-15。Bessent 要求英伟达董事会与外部律师在 10 天内说明情况。10 天自 11-15 起算，约 2026-11-25。
- 来源地址：`https://casrai.org/news/bessent-nvidia-outside-ceo-2026`（CASRAI 整理，2026-11-15 访谈，引用 Reuters 报道）。Fox News 原始访谈视频链接：无（本次未获得可直接引用的 URL）。
- 核对方法：检索 Reuters 相关报道与多家转载。多家来源一致称 10 天要求出自 11-15 访谈。
- 备注：这是公开要求，不是法定截止日。“约”字与此相符。

#### FC-01-E4

- 账本原文：“FT 11-20 调查 Aivres–Megaspeed 46 亿美元通道。”
- 账本标注：`verified`。
- 核对结果：被反驳（日期部分）。
- 来源标识：Financial Times 调查《Alice Huang's links to the chip underworld》，发表于 2026-11-21，不是 11-20。调查内容本身属实：Speedmatrix 自 Aivres 进口申报约 46 亿美元（2024-12 至 2025-12，ImportGenius 贸易数据）。
- 来源地址：`https://www.tradingview.com/news/invezz:79037f59e094b:0-ft-finds-alice-huang-linked-to-chip-network-with-alleged-cambodian-crime-group/`（标注发表时间 2026-11-21T17:31:57Z）；`https://www.siliconreport.com/alice-huang-network-supplied-nvidia-chips-to-china-ft-reports`（称 FT 于 2026-11-21 报道）。FT 原文链接：`https://www.ft.com/content/f3ad8a81-3890-4a8a-8853-ff0a94b08ba9`（由二手来源给出，本次未直接打开，付费墙）。
- 核对方法：检索多家转载报道。TradingView、Silicon Report、NDTV、WION 一致称 FT 调查发表于 2026-11-21。Techmeme 收录编号为 261121。无任何来源支持 11-20。
- 备注：被反驳只针对日期要素。调查内容与 46 亿美元数字已核实。修正日期为 2026-11-21 后，本条可改标已核实。修正走版本链，见第 4 节。

#### FC-01-E5

- 账本原文：“众议院 12-01 闭门访谈、参议院作证。”
- 账本标注：`unverified`。`published_at` 为空。`source_url` 为空。
- 核对结果：已核实。
- 来源标识：众议院外交事务委员会、美中战略竞争特设委员会、情报委员会三主席联名信，2026-11-12。信件要求黄仁勋于 2026-12-01 接受闭门转录访谈，11-13 美东 20:00 前书面确认，否则发传票。参议院银行委员会主席 Tim Scott 同日致信，要求黄仁勋 2026-12-03、商务部长 Lutnick 2026-12-10 出席。
- 来源地址：`https://www.nacionale.com/en/articles/will-jensen-huang-testify-under-oath-closed-door-congress-what-it-means`（转述 ABC News 与 CBS News 报道）。众议院外交事务委员会 2026-11-12 信函原件链接：无（本次未获得可直接引用的 URL）。
- 核对方法：检索 NBC News、ABC News、Reuters 相关报道（经多家二手来源转述）。三方日程一致。
- 备注：截至 11-13 至 11-14，未见黄仁勋公开确认 12-01 日期。双方后于 11-16 至 11-20 达成一致。摘录只写日程，不写是否确认。日程本身已核实。

#### FC-01-E6

- 账本原文：“英伟达 2025-06 起内部禁售名单含 Megaspeed。”
- 账本标注：`unverified`。来源写角色扮演源文档。
- 核对结果：已核实。
- 来源标识：美国商务部与司法部联合声明，2026-11-16。声明称 2025-06 英伟达把 Megaspeed 列入内部禁售名单（"no sell" list）。声明日早于信息截止日 2026-11-22。
- 来源地址：`https://www.channelnewsasia.com/business/us-megaspeed-probe-jensen-huang-nvidia-2024-6557971?cid=internal_sharetool_iphone_17112026_cna`（CNA，2026-11-16，引用联合声明）；`https://www.reuters.com/business/retail-consumer/what-we-know-about-megaspeed-nvidia-customer-blacklisted-by-us-2026-11-24/`（Reuters，2026-11-24 解释文章，引用联合声明）。
- 核对方法：读 CNA 2026-11-16 报道。读 Reuters 2026-11-24 解释文章。读 Wall Street Journal 相关报道转述。三方一致。
- 备注：账本 `publisher` 写角色扮演源文档。真实来源是商务部与司法部联合声明。升级时改 `publisher` 与 `source_url`，见第 4 节。

#### FC-01-E7

- 账本原文：“路透 SEC 会计调查报道。”
- 账本标注：`unverified`。`published_at` 为空。`source_url` 为空。
- 核对结果：已核实。
- 来源标识：Reuters 独家报道，Chris Prentice 与 Alexandra Alper，标题《Nvidia's accounting is a focus of US SEC investigation, sources say》，2026-11-20（美国时间；格林尼治时间 2026-11-21 03:13，GMT+8）。报道称 SEC 执法人员审查英伟达会计做法。
- 来源地址：无（本次未获得 Reuters 原文可直接引用的 URL）。Reuters 官方 Threads 帖子 2026-11-20 转载同一标题。Reuters 2026-11-24 报道亦确认英伟达面临 SEC 与司法部调查：`https://www.reuters.com/legal/transactional/nvidia-boards-huang-reversal-raises-doubts-about-independence-critics-say-2026-11-24/`。
- 核对方法：检索 Reuters 官方账号帖子与多家转载。多家来源一致称 Reuters 于 11-20 独家报道。
- 备注：调查不等于认定违规。摘录只写“报道”，不写认定。摘录本身已核实。

### 2.2 S6-FC-02（5 条）

#### FC-02-E1

- 账本原文：“Azure AI 需求强劲。”
- 账本标注：`unverified`。来源写角色扮演源文档。`published_at` 写 2026-11-22。
- 核对结果：已核实。
- 来源标识：微软 FY26 Q1 财报，2026-10-28（季度截至 2026-09-30）。Azure 收入 331.7 亿美元，同比增长 48%。微软指引 FY26 Q2 Azure 增长 49% 至 50%。
- 来源地址：`https://www.businesstimes.com.sg/companies-markets/microsofts-cloud-growth-cash-flow-offer-respite-ai-spending-fears`（The Business Times，2026-10-29 左右，转述 Reuters 报道）。
- 核对方法：读多家财报报道。Azure 增长 48% 与指引 49% 至 50% 在多家来源一致。
- 备注：账本 `published_at` 写 2026-11-22，这是源文档日期，不是财报日期。升级时改为 2026-10-28，`publisher` 改为微软。

#### FC-02-E2

- 账本原文：“微软资本开支为 AI 基建持续上升。”
- 账本标注：`unverified`。来源写角色扮演源文档。`published_at` 写 2026-11-22。
- 核对结果：已核实。
- 来源标识：微软 FY26 Q1 财报，2026-10-28。资本开支与融资租赁合计 452 亿美元，高于上年同期的 349 亿美元，同比上升约 30%。CFO Amy Hood 指引 FY26 Q2 资本开支超过 500 亿美元。
- 来源地址：同 FC-02-E1。
- 核对方法：读多家财报报道。452 亿美元与 349 亿美元在多家来源一致。
- 备注：账本 `published_at` 须改为 2026-10-28。`publisher` 改为微软。

#### FC-02-E3

- 账本原文：“微软是 OpenAI 主要投资方（星门项目）。”
- 账本标注：`unverified`。来源写角色扮演源文档。`published_at` 写 2026-11-22。
- 核对结果：被反驳（括号部分）。
- 来源标识：微软累计向 OpenAI 投资逾 130 亿美元，持股 27%。这部分属实。星门项目（Stargate）合伙方是 OpenAI、软银、甲骨文。微软不是星门合资方。括号把微软与星门项目直接关联，与事实不符。
- 来源地址：`https://substack.frontierfoundry.com/p/ai-giants-pt-5-microsofts-80b-gamble`（微软投资 138 亿美元，持股 27%）；`https://dev.to/genieinfotech/the-250-billion-frenemy-pact-why-the-microsoft-openai-marriage-is-over-and-the-war-has-begun-1943`（星门项目由 OpenAI、软银、甲骨文发起，不含微软）。
- 核对方法：检索星门项目结构报道。2026-02 公开报道确认星门三方合资未招聘员工、未建合资数据中心。OpenAI 转向双边交易。微软未列入星门合资方。
- 备注：被反驳只针对括号部分。投资方部分属实。修正方法是删除“（星门项目）”，或拆分为两条主张。修正走版本链，见第 4 节。

#### FC-02-E4

- 账本原文：“FY26 Q1 财报 Azure 增长强劲。”
- 账本标注：`unverified`。来源写角色扮演源文档。`published_at` 写 2026-11-22。
- 核对结果：已核实。
- 来源标识：微软 FY26 Q1 财报，2026-10-28。Azure 收入 331.7 亿美元，同比增长 48%。
- 来源地址：同 FC-02-E1。
- 核对方法：同 FC-02-E1。
- 备注：账本 `published_at` 须改为 2026-10-28。`publisher` 改为微软。

#### FC-02-E5

- 账本原文：“微软在建数据中心。”
- 账本标注：`unverified`。来源写角色扮演源文档。`published_at` 写 2026-11-22。
- 核对结果：已核实。
- 来源标识：微软 FY26 Q4 财报电话会，2026-07-29。FY2026 全年新增 88 座数据中心。Q4 新增 31 座与约 1 GW 容量。2026 年资本开支约 1750 亿美元。沙特东部区域 2026-11 上线。
- 来源地址：`https://www.zacks.com/stock/news/2983729/microsofts-ai-datacenter-expansion-a-game-changer-for-the-stock`（Zacks，2026-09-02）；`https://convergedigest.com/microsoft-plans-175-billion-in-2026-capital-spending/`（Converge Digest，FY26 Q4 财报整理）。
- 核对方法：读 Zacks 与 Converge Digest 财报整理。新增数据中心数量在两处来源一致。
- 备注：账本 `published_at` 写 2026-11-22，这是源文档日期。升级时改为 2026-07-29（FY26 Q4 财报）。

### 2.3 S6-FC-03（4 条）

#### FC-03-E1

- 账本原文：“Gemini 4 Neon 11-18 发布。”
- 账本标注：`unverified`。`published_at` 写 2026-11-18。
- 核对结果：已核实。
- 来源标识：Google 官方博客《Introducing Gemini 4 Neon》，2026-11-18。
- 来源地址：`https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-neon/?utm_source=deepmind.google&utm_medium=referral&utm_campaign=gdm&utm_content=`。
- 核对方法：读 Google 官方博客原文。日期与名称一致。

#### FC-03-E2

- 账本原文：“OpenAI GPT-6.2 11-17 发布。”
- 账本标注：`unverified`。`published_at` 写 2026-11-17。
- 核对结果：已核实。
- 来源标识：OpenAI 开发者社区官方公告《GPT-6.2 Astra and Sol are now available》，2026-11-17 18:00。GPT-6.2 Astra 与 Sol 同日上线。
- 来源地址：`https://community.openai.com/t/gpt-6-2-astra-and-sol-are-now-available/1417531?ref=apidog.com`。
- 核对方法：读 OpenAI 开发者社区公告原文。日期与名称一致。
- 备注：公告载于 OpenAI 开发者社区，不是 openai.com 主站博客。内容仍是 OpenAI 官方发布。

#### FC-03-E3

- 账本原文：“谷歌与 OpenAI 模型发布节奏竞逐。”
- 账本标注：`unverified`。来源写角色扮演源文档。`published_at` 写 2026-11-22。
- 核对结果：未核实。
- 来源标识：无。本条无单一可定位事实。
- 核对方法：检索发布记录。支撑事实存在：GPT-6.2 发布于 2026-11-17，Gemini 4 Neon 发布于 2026-11-18，两者相隔一日（见 FC-03-E1、FC-03-E2）。但“竞逐”是推断，不是事实。推断不能写成已核实。
- 备注：升级条件是把主张改写为带日期的具体事实，例如“GPT-6.2 与 Gemini 4 Neon 相隔一日发布”。改写须走版本链。

#### FC-03-E4

- 账本原文：“Gemini 定期出新模型。”
- 账本标注：`unverified`。来源写角色扮演源文档。`published_at` 写 2026-11-22。
- 核对结果：未核实。
- 来源标识：无。本条无单一可定位事实。
- 核对方法：检索发布记录。支撑事实存在：Gemini 4 系列在约七周内发布四款模型。Neon 是第四款，发布于 2026-11-18。但“定期”无明确周期与次数，无法逐项核对。
- 备注：升级条件是把主张改写为带数字与日期的具体事实，例如“Gemini 4 系列七周内发布四款模型”，并补来源。改写须走版本链。

### 2.4 S6-FC-04（5 条）

#### FC-04-E1

- 账本原文：“台积电 2nm 为下一代制程、在爬坡。”
- 账本标注：`unverified`。来源写角色扮演源文档。`published_at` 写 2026-11-22。
- 核对结果：已核实。
- 来源标识：台积电 2026 年 Q3 法说会，2026-10-15（董事长兼 CEO C.C. Wei）。N2 于 2025 年 Q4 进入量产，在新竹与高雄爬坡顺利。Q3 占晶圆收入 8%。
- 来源地址：`https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/2026-10/eba4fac72873bf546b669bd2b5d973df5c93215d/TSMC%203Q26%20Transcript.pdf`（台积电投资者关系网站，法说会记录）。
- 核对方法：读法说会记录转述（The Motley Fool 转录本）与台积电官方记录。量产时间与收入占比一致。
- 备注：账本 `published_at` 须改为 2026-10-15。`publisher` 改为台积电。

#### FC-04-E2

- 账本原文：“CoWoS 先进封装是瓶颈。”
- 账本标注：`unverified`。来源写角色扮演源文档。`published_at` 写 2026-11-22。
- 核对结果：已核实。
- 来源标识：台积电 2026 年 Q2 法说会，2026-07-16（C.C. Wei 原话）：“packaging capacity is so tight that now it's limiting my customers' growth.”（封装产能非常紧张，现在已限制客户增长。）
- 来源地址：无（本次未获得法说会记录可直接引用的 URL）。引文见 SiliconAnalysts 整理：`https://siliconanalysts.com/analysis/foundry-allocation-status-q1-2026`。
- 核对方法：检索法说会引文。多家行业分析引用同一原话。引文日期为 2026-07-16。
- 备注：产能数字（约 9 万片/月）来自行业分析，未用作出处。升级时 `published_at` 改为 2026-07-16，`publisher` 改为台积电。

#### FC-04-E3

- 账本原文：“台积电 11-20 叫停 16nm 及以下中国客户订单。”
- 账本标注：`unverified`。`published_at` 写 2026-11-20。
- 核对结果：已核实。
- 来源标识：Reuters，2026-11-20（两位知情人士；台积电指引文件）。受影响订单须获美国出口许可，否则暂停 16nm 及以下制程。Financial Times 2026-11-19 率先报道台积电与三星暂停部分对华出货。
- 来源地址：`https://www.businesstimes.com.sg/international/global/tsmc-reportedly-tightens-china-ai-chip-curbs-new-us-rules-close-manufacturing-loophole`（The Business Times，2026-11-20，转述 Reuters）；`https://www.taiwannews.com.tw/news/6478978`（Taiwan News，2026-11-20，转述 Reuters）。
- 核对方法：读多家转载报道。暂停范围（16nm 及以下）与触发原因（BIS 新规 11-19 生效）在多家来源一致。
- 备注：账本 `publisher` 写台积电。实际来源是 Reuters 报道。台积电未证实具体订单安排，只表示知悉并遵守新规。升级时 `publisher` 改为 Reuters。

#### FC-04-E4

- 账本原文：“亚利桑那厂在扩。”
- 账本标注：`unverified`。来源写角色扮演源文档。`published_at` 写 2026-11-22。
- 核对结果：已核实。
- 来源标识：台积电 2026 年 Q3 法说会，2026-10-15。第二座厂建设完成，进入设备搬入，量产定于 2027 年 Q3。第三座厂在建。2026-07-16 台积电追加 1000 亿美元投资，总额达 2650 亿美元。
- 来源地址：`https://azbigmedia.com/business/tsmc-arizona-accelerates-production-timeline-as-earnings-soar/`（AZ Big Media，转述 Q3 法说会）；`https://betanews.com/article/tsmc-100-billion-arizona-chip-expansion/`（BetaNews，2026-07-16 追加投资）。
- 核对方法：读多家报道。法说会日期与追加投资日期在多家来源一致。
- 备注：账本 `published_at` 须改为 2026-10-15。`publisher` 改为台积电。

#### FC-04-E5

- 账本原文：“AI 需求拉动先进制程。”
- 账本标注：`unverified`。来源写角色扮演源文档。`published_at` 写 2026-11-22。
- 核对结果：未核实。
- 来源标识：无。本条无单一可定位事实。
- 核对方法：检索台积电财报。支撑数字存在：台积电 Q3 收入 467.2 亿美元，同比增长 41.2%。HPC 占销售额 68%。C.C. Wei 称需求远超供给，未见放缓迹象。但“拉动”是因果归因，不是事实。归因不能写成已核实。
- 备注：升级条件是把主张改写为带数字与日期的具体事实，例如“台积电 Q3 HPC 占销售额 68%，收入同比增长 41.2%”，并补来源。改写须走版本链。

### 2.5 结算证据 S6-FC-01（1 条）

#### R1-01

- 账本原文：“BIS 于 2026-11-23 发布最终规则，将 Megaspeed 及 6 家关联实体列入实体清单。联邦纪事文件号 2026-23999，2026-11-25 刊登。规则于 2026-11-23 提交联邦纪事公示，当日生效。7 家实体：马来西亚 MSFusion、PT Megaspeed International、Speedmatrix；新加坡 Apex Enterprise Solutions、Megaspeed International、Swiftdata；泰国 Megaspeed (Thailand)。”
- 账本标注：`verified`。
- 核对结果：已核实。
- 来源标识：美国商务部产业安全局（BIS），最终规则，Federal Register 文件号 2026-23999。2026-11-23 16:15 提交联邦纪事公示。定于 2026-11-25 刊登。自公示起具法律效力。7 家实体名单与账本摘录逐一相符。
- 来源地址：`https://www.straitstimes.com/business/economy/megaspeed-on-us-blacklist-what-this-means-for-the-operations-of-the-spore-based-firm`（The Straits Times）；`https://www.aljazeera.com/economy/2026/11/24/us-adds-megaspeed-firm-at-centre-of-nvidia-scandal-to-export-control-list?traffic_source=rss`（Al Jazeera，2026-11-24）；`https://tsnmedia.org/megaspeed-entity-list-malaysia-miti/`（TSN，文件号与公示时间）。
- 核对方法：读三家报道。三家名单一致。三家文件号一致。三家日期一致。
- 备注：账本写“2026-11-25 刊登”，与 TSN 报道一致。账本写“当日生效”，与 TSN“自公示起具法律效力”一致。本条维持已核实。Brier 分 0.16 不在本次核对范围。

## 3. 统计

### 3.1 本次核对结果

| 范围 | 已核实 | 未核实 | 被反驳 | 合计 |
| --- | --- | --- | --- | --- |
| FC-01 预测证据 | 6 | 0 | 1 | 7 |
| FC-02 预测证据 | 4 | 0 | 1 | 5 |
| FC-03 预测证据 | 2 | 2 | 0 | 4 |
| FC-04 预测证据 | 4 | 1 | 0 | 5 |
| 预测证据合计 | 16 | 3 | 2 | 21 |
| FC-01 结算证据 | 1 | 0 | 0 | 1 |
| 全部合计 | 17 | 3 | 2 | 22 |

全部 22 条：已核实 17 条（77.3%）。未核实 3 条（13.6%）。被反驳 2 条（9.1%）。

### 3.2 与账本标注的对比

账本标已核实 3 条：FC-01-E1、FC-01-E4、R1-01。本次确认 FC-01-E1 与 R1-01。FC-01-E4 的日期被反驳，见第 3.3 节。

账本标未核实 19 条。本次核对：15 条可升级为已核实。1 条改为被反驳（FC-02-E3）。3 条保持未核实（FC-03-E3、FC-03-E4、FC-04-E5）。

### 3.3 被反驳项（2 条）

1. FC-01-E4。被反驳要素：发表日期。账本写 FT 调查发表于 11-20。多家来源证实发表于 2026-11-21。调查内容与 46 亿美元数字本身已核实。只须修正日期。
2. FC-02-E3。被反驳要素：括号“（星门项目）”。微软是 OpenAI 主要投资方，这部分属实。星门项目合伙方是 OpenAI、软银、甲骨文，不含微软。括号把微软与星门项目直接关联，与事实不符。只须删除括号，或拆分为两条主张。

被反驳项共 2 条。两条都只错一部分。两条的核心事实都已核实。两条都可修正后升级，见第 4 节。

## 4. 拟升级清单（只列清单，不改账本）

协调员走版本链统一改。本清单共 17 条：15 条直接升级，2 条先修正再升级。

### 4.1 直接升级为已核实（15 条）

| 编号 | 拟改 `verification_result` | 拟补 `publisher` | 拟补 `published_at` | 拟补 `source_url`（或来源标识） |
| --- | --- | --- | --- | --- |
| FC-01-E2 | `verified` | BIS（实体清单） | 2026-11-22 前状态；首次列入 2026-11-23 | Federal Register 文件号 2026-23999（反向证明）；Financial Times 2026-11-12 前后报道（仍未列入） |
| FC-01-E3 | `verified` | 美国财政部（Bessent） | 2026-11-15 | Fox News 访谈 2026-11-15（原始视频链接无；CASRAI 整理见正文） |
| FC-01-E5 | `verified` | 美国众议院 / 参议院 | 2026-11-12 | 众议院三主席联名信 2026-11-12；参议院银行委员会致信 2026-11-12 |
| FC-01-E6 | `verified` | 美国商务部 / 司法部（联合声明） | 2026-11-16 | CNA 2026-11-16 报道；Reuters 2026-11-24 解释文章 |
| FC-01-E7 | `verified` | Reuters | 2026-11-20 | Reuters 独家报道《Nvidia's accounting is a focus of US SEC investigation, sources say》（原文链接无） |
| FC-02-E1 | `verified` | 微软 | 2026-10-28 | 微软 FY26 Q1 财报 2026-10-28（Azure 收入 331.7 亿美元，同比增长 48%） |
| FC-02-E2 | `verified` | 微软 | 2026-10-28 | 微软 FY26 Q1 财报 2026-10-28（资本开支与融资租赁合计 452 亿美元） |
| FC-02-E4 | `verified` | 微软 | 2026-10-28 | 微软 FY26 Q1 财报 2026-10-28（Azure 同比增长 48%） |
| FC-02-E5 | `verified` | 微软 | 2026-07-29 | 微软 FY26 Q4 财报电话会 2026-07-29（全年新增 88 座数据中心） |
| FC-03-E1 | `verified` | 谷歌（Google DeepMind） | 2026-11-18 | Google 官方博客《Introducing Gemini 4 Neon》 |
| FC-03-E2 | `verified` | OpenAI | 2026-11-17 | OpenAI 开发者社区公告《GPT-6.2 Astra and Sol are now available》 |
| FC-04-E1 | `verified` | 台积电（TSMC） | 2026-10-15 | 台积电 2026 年 Q3 法说会记录（N2 量产，占晶圆收入 8%） |
| FC-04-E2 | `verified` | 台积电（TSMC） | 2026-07-16 | 台积电 2026 年 Q2 法说会（C.C. Wei 原话） |
| FC-04-E3 | `verified` | Reuters | 2026-11-20 | Reuters 2026-11-20 报道（16nm 及以下订单暂停） |
| FC-04-E4 | `verified` | 台积电（TSMC） | 2026-10-15 | 台积电 2026 年 Q3 法说会记录（亚利桑那第二座厂建设完成） |

### 4.2 先修正再升级（2 条）

| 编号 | 拟修正内容 | 修正后拟标结果 | 来源标识 |
| --- | --- | --- | --- |
| FC-01-E4 | `published_at` 由 2026-11-20 改为 2026-11-21。`excerpt` 日期同步改为 11-21。补 FT 标题《Alice Huang's links to the chip underworld》。 | `verified` | Financial Times，2026-11-21 |
| FC-02-E3 | `excerpt` 删除“（星门项目）”。或拆分为两条：一条写微软是 OpenAI 主要投资方；一条写星门项目合伙方（OpenAI、软银、甲骨文），不列入本预测证据。 | `verified`（投资方部分） | 微软累计投资逾 130 亿美元，持股 27%（2025-10 重组协议公开报道） |

### 4.3 保持未核实（3 条，不进升级清单）

- FC-03-E3。主张是趋势判断，无单一可定位事实。升级须先改写主张。
- FC-03-E4。主张无明确周期与次数，无法逐项核对。升级须先改写主张。
- FC-04-E5。主张是因果归因，无单一可定位事实。升级须先改写主张。

改写主张须走版本链。本附录不改写账本原文。

## 5. 方法与局限

- 检索日是 2026-11-25。来源是公开网络。未用付费数据库。未联系任何机构。
- Financial Times 原文未直接打开（付费墙）。FT 调查的日期与内容依据多家二手来源：TradingView、Silicon Report、NDTV、WION、AI Weekly。五家日期一致（2026-11-21）。
- Reuters SEC 独家报道原文链接本次未获得。核实依据 Reuters 官方账号帖子、多家转载与 Reuters 2026-11-24 后续报道。
- FC-01-E2 是间接核实。本次未直接查阅 2026-11-22 当日的实体清单快照。直接查阅快照是更强的方法。协调员升级时可补快照。
- 时区说明：Reuters SEC 报道按美国时间是 2026-11-20，按格林尼治时间是 2026-11-21 03:13（GMT+8）。本附录写 2026-11-20（美国时间）。
- 角色扮演源文档只作主张出处。凡账本 `publisher` 写角色扮演源文档而外部来源已找到的条目，升级时把 `publisher` 改为真实发布机构。共 11 条：FC-01-E6、FC-02-E1、FC-02-E2、FC-02-E4、FC-02-E5、FC-03-E3、FC-03-E4、FC-04-E1、FC-04-E2、FC-04-E4、FC-04-E5。其中 FC-03-E3、FC-03-E4、FC-04-E5 保持未核实，暂不改。
- Brier 分 0.16 与命中判定不在本次核对范围。本次只核对证据事实。
- 本附录不改账本。全部升级与修正由协调员走版本链统一执行。
