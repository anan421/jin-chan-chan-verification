# S5 补丁（第 6 轮）报告 — 2026-11-22

分支：`loop/vision-1-round6-s5patch`（工作区 `~/workspace/verification-v1-round6`）。
S5 原已封口。本轮按 Gu 的决定重新打开、补 9 个漏掉的 S5 事件、重验。
主分支未动，未合并，未推 GitHub。

## 1. 9 个补丁

方法与上一轮补丁相同：改写 9 条已有 S5 动作的文字，不加动作。
动作总数仍为 558 条，每轮仍为 18 条。
与上一轮不同：这 9 个事件是新增事件，hp/gold 按事件本身设定，
不是沿用旧值。每个事件先读一手来源，再定 hp/gold。

校准锚点（trace 里已有值）：旗舰发布 GPT-4 +7/+5、Gemini 1.5 +4/+2、
Grok 上线 +2/−3、V3 +10/+3、R1 +11/+5；BIS 规则打 BYTE 5-1 −4/−2；
SEC 调查打 NVDA 6-1 −18/−6；黄仁勋辞职 −16/−4；Anthropic IPO +8/+30。
全链无 hp 封顶命中（都在 0–100 内），金币全为正（最低 MUSK 29）。

### 1.1 OpenAI GPT-6.2 Astra 与 Sol — S5 4-1，OAI，chatgpt
- 事件日期：2026-11-17。来源：OpenAI 官方博客 11-17。
  Astra $8/$40、Sol $2/$10，ChatGPT Work 与 Codex 同日上线，
  Plus/Pro/Enterprise/Edu 与 API 均可用。
- 轮次：S5 4-1（11-12 至 11-18）。
- 旧动作：「最大客户之一。供应担忧」hp −3 / gold −1。
- 新动作：「GPT-6.2 Astra 与 Sol 发布。ChatGPT Work 与 Codex 同日上线」
  hp +4 / gold +1。
- 理由：旗舰模型发布，正向；但属 6.1→6.2 的迭代更新，
  且有 Critical 级网络安全标记，故低于 GPT-4 的 +7/+5。

### 1.2 Google Gemini 4 Neon — S5 5-1，GOOG，gemini
- 事件日期：2026-11-18。来源：Google 官方博客 11-18。
  定位在 Carbon 与 Hydrogen 之间的中端模型，$3/$15，100 万 token 上下文。
- 轮次：S5 5-1（11-18 至 11-20）。
- 旧动作：「股东受益。股价被带跌对冲」hp −1 / gold +2。
- 新动作：「Google 发布 Gemini 4 Neon。中端编码与分析模型」
  hp +3 / gold +1。
- 理由：中端模型发布，正向但低于旗舰；发布当日已列 AA 指数第 3 位。

### 1.3 FT 调查：Aivres–Megaspeed 46 亿美元芯片通道 — S5 5-1，NVDA，megaspeed
- 事件日期：2026-11-20。来源：FT 调查 11-20（FT 原文付费墙，
  本条为 fourweekmba / TNW / RealClearWorld 转述）。
  浪潮未列清单的美国子公司 Aivres 持续与英伟达交易；
  Megaspeed 马来西亚子公司 Speedmatrix 申报自 Aivres 进口约 46 亿美元货物
  （截至 2025 年 12 月，ImportGenius 口径）；英伟达称 2025 年已将
  Megaspeed 列入内部禁售名单。
- 轮次：S5 5-1（例外，见下）。
- 旧动作：「连跌第七日。收 145.98 一线」hp −8 / gold −2。
- 新动作：「FT 调查：Aivres–Megaspeed 芯片通道。Speedmatrix 申报自
  Aivres 进口约 46 亿美元」hp −10 / gold −3。
- 理由：46 亿美元通道被画出，加上英伟达自己承认已内部禁售
  Megaspeed，负面且实质；但低于 SEC 调查的 −18/−6。
- 例外说明：按日期该事件属 S5 6-1，但 NVDA 6-1 已有 SEC 调查问题
  （v4 q64，动作「SEC 调查报道。恐慌卖出」），改写会毁掉那道题。
  故放进 S5 5-1：轮次日期 11-18 比事件晚 2 天，仍是有效预测点。
  S5 6-2（11-21）不采用：轮次日期在事件之后，违反 on/before 原则。

### 1.4 广州首个真武国产万卡智算集群投产 — S5 4-1，ALI，datacenter
- 事件日期：2026-11-16。来源：中国电信广东公司 + 阿里云智能集团联合主办
  11-16；广州日报大洋网、21 财经、南方+、凤凰网、新浪均 11-16 报道。
- 位置已核定：广州。六家以上来源一致：发布会在黄埔区中国电信
  创新孵化（南方）基地举行，称「广州首个真武国产万卡智算集群正式
  投产运营」，集群「坐落于广州产业腹地」「扎根广州」，计划扩至 10 万卡，
  TokenHub 平台同步发布。SCMP 的「韶关」读法无任何可检索来源佐证，
  不采用。动作文字写广州。
- 轮次：S5 4-1（11-12 至 11-18）。
- 旧动作：「阿里港股当日承压」hp −2 / gold 0。
- 新动作：「广州首个真武国产万卡智算集群投产运营。计划扩至 10 万卡」
  hp +3 / gold −1。
- 理由：算力能力上升，正向；平台与运营开支继续花钱，金币略负。

### 1.5 台积电叫停 16nm 及以下中国客户订单 — S5 6-1，TSMC，bis_rule
- 事件日期：2026-11-20。来源：路透（经 Taiwan News、Straits Times 11-20）
  与 FT 11-19。受影响订单无许可证即停，仅限 28/40nm，
  无 HBM 与先进封装；触发点为 BIS 临时最终规则 11-19 生效
  （91 FR 74970，doc 2026-23529）。
- 轮次：S5 6-1（11-20 至 11-21）。
- 旧动作：「大盘带跌。相对抗跌」hp −2 / gold −1。
- 新动作：「台积电执行 BIS 规则：叫停 16nm 及以下中国客户订单。
  无许可证改用 28nm/40nm」hp −4 / gold −2。
- 理由：实际停单，负面；强于 S5 3-2「两难」的 −1/0。
  取值 −4/−2，与规则本身打 BYTE 同档——停单是规则落到
  执行层面的直接动作，但只涉部分订单。

### 1.6 甲骨文宣布 OpenAI 基建合同融资全部落实 — S5 6-1，ORCL，financing
- 事件日期：2026-11-20。来源：Oracle 官方声明 11-20。
  「已落实履行与 OpenAI 合同所需的全部资金」；最后一次融资
  约 100 亿美元股票 + 100 亿美元债务；合同约 3000 亿美元、4.5GW；
  声明在收盘后发布，盘后股价 +3.3%。
- 轮次：S5 6-1。
- 旧动作：「债务担忧带跌」hp −5 / gold −1。
- 新动作：「甲骨文宣布 OpenAI 基建合同融资全部落实。
  约 3000 亿美元、4.5GW」hp +3 / gold +2。
- 理由：融资疑虑消除，正向。注意：当日现金时段股价仍下跌，
  盘后才涨；+3/+2 取的是官方宣布本身的信号，不是当日收盘价。

### 1.7 亚马逊 Q3 现金资本开支 759 亿美元、全年指引约 2200 亿美元 — S5 2-1，AMZN，capex
- 事件日期：2026-10-29。来源：亚马逊 Q3 2026 财报电话会 10-29
  （WSJ、TheStreet、10-Q 于 10-30 提交）。
  Q3 现金资本开支 759 亿美元，全年指引约 2200 亿美元（多数投向 AWS），
  2027 年「显著增加」；TTM 自由现金流 −424 亿美元。
- 轮次：S5 2-1（10-06 至 11-05）。23 天提前量，属题集正常范围。
  S5 3-2（11-05）不采用：轮次日期在事件之后。
- 旧动作：「跟涨」hp +2 / gold +1。
- 新动作：「亚马逊 Q3 现金资本开支 759 亿美元。
  全年指引约 2200 亿美元」hp +3 / gold −6。
- 理由：按任务要求，投资势头为正（hp +3），但花钱为实
  （gold −6，对应 759 亿美元季度开支与 −424 亿美元 TTM 自由现金流）。
  注意：市场的实际解读是负面的（开盘 −4.6%，收盘 −1.4%）；
  本补丁取的是「玩家自身投资信号」口径，不是市场收盘口径。

### 1.8 软银 118.7 亿美元定期贷款（为 OpenAI 投资融资）— S5 1-1，SFTB，financing
- 事件日期：2026-09-14。来源：彭博 9-14（经 Japan Times、Business Times）。
  两年期贷款 118.7 亿美元，约 20 家银行承诺，原目标 100 亿美元，
  超额认购；以 OpenAI 持股作抵押。
- 轮次：S5 1-1（01-01 至 10-06）。
- 旧动作：「星门资金链被盘问」hp −10 / gold −21。
- 新动作：「软银落实 118.7 亿美元两年期定期贷款。
  为 OpenAI 投资融资」hp +2 / gold −2。
- 理由：贷款超额认购，资金悬念解除，正向但温和（+2）。
  金币略负：同一周软银偿还 259 亿美元过桥贷款（400 亿美元中的一部分，
  9-15 到期），当周净现金流出约 140 亿美元——这是再融资，
  不是新增净现金。
- 附带：S5 1-1 的 reconciliation 里 SFTB 的 `moveTo`/`breakpoint`
  也随之更新（hp moveTo −10→+2，breakpoint −8→+4；
  gold moveTo −21→−2，breakpoint −19→0）。

### 1.9 xAI Grok 4.8 软发布 — S5 5-1，MUSK，spacex_xai
- 事件日期：2026-11-18。来源：马斯克本人的 X 帖子（多家媒体引述：
  explainx.ai、penchan、grokshelf、aitoolsrecap）。
  11-10：预训练完成，正在用重写的 C++ 栈做 RL，本周晚些时候向
  Grok Bot 用户软推出；11-18（凌晨）：「我们确实向部分 Bot 用户
  做了软推出，但全面发布前还需一到两周打磨。」
- 核验说明：无 xAI 新闻稿、无 API 发布、无基准分数；xAI 文档
  仍列 4.7 为最新版。任务要求「至少一个可信来源」已满足
  （马斯克本人帖子为一手来源），故纳入补丁；但来源等级低于
  官方博客，事件日期取 11-18（马斯克确认软推出的当日）。
- 轮次：S5 5-1。
- 旧动作：「后续 IPO 排队者窗口变窄」hp −4 / gold −2。
- 新动作：「xAI Grok 4.8 开始向部分 Bot 用户软发布」hp +2 / gold −1。
- 理由：软推出为真，但明确不是全面发布，正向但小（+2/−1）。

## 2. 补丁后的 S5 期末

新 S5 期末（hp/gold）：OAI 67/50（原 60/48）、GOOG 76/69（72/70）、
NVDA 36/54（38/55）、ALI 73/47（68/48）、TSMC 64/67（66/68）、
ORCL 64/43（56/40）、AMZN 65/55（64/62）、SFTB 64/57（52/38）、
MUSK 56/29（50/28)。

新 S5 排名（按血量降序，同分保持 players 数组原顺序）：
1 GOOG 76、2 ANTH 74、3 BYTE 74、4 ALI 73、5 HUAWEI 72、6 AAPL 70、
7 DPSK 70、8 MSFT 68、9 OAI 67、10 TCE 66、11 AMZN 65、12 ORCL 64、
13 TSMC 64、14 SFTB 64、15 META 58、16 BIDU 58、17 MUSK 56、18 NVDA 36。
段位影响（70–79 为钻石）：ALI 68→73，进入钻石；GOOG 仍为钻石；
BYTE 74 不变（钻石）。

语义分布变化（脚本核验，非手算）：unknown 344→339、chatgpt 3→4、
gemini 4→5、megaspeed 2→3、bis_rule 4→5、financing 19→20、capex 16→17、
stargate 15→14、anthropic_ipo 8→7、spacex_xai 4→5；已分类 214→219。
9 条改写动作的旧种类：unknown ×6（OAI、GOOG、NVDA、ALI、TSMC、AMZN）、
financing ×1（ORCL）、stargate ×1（SFTB「星门资金链被盘问」）、
anthropic_ipo ×1（MUSK「后续 IPO 排队者窗口变窄」——分类器 artifact，
指 xAI 的 IPO 窗口，不是 Anthropic 的 IPO）。
新种类：chatgpt、gemini、megaspeed、unknown（ALI 真武——datacenter
无分类器规则，沿用 v3 的既定模式：问题种类 datacenter、trace 种类
unknown）、bis_rule、financing、capex、financing、spacex_xai。
`convert_data_json.py` 的 `EXPECTED_LEGACY_COUNTS` 已更新 5 项
（stargate 15→14、anthropic_ipo 8→7、spacex_xai 4→5、bis_rule 5、
chatgpt 4），其余不变；守卫仍会在任何意外动作上报错。
新动作文字已按分类器规则写定，避免误触发
（NVDA 文字含 Megaspeed 但无 SEC/BIS/出口管制/远程规则，
因 bis_rule 在 megaspeed 之前检查；SFTB 文字含「融资」但无「星门」，
因 stargate 在 financing 之前检查；OAI 文字含 ChatGPT，
因单写 GPT-6.2 触发不了 chatgpt 规则）。

页面证据：9 条新动作各加 1 条 roundEvidence（+ move 指针），
共 9 条；无轮次的 verified/opinion 状态改动。
页面 data.json 已同步（见第 5 节）。

## 3. 题集修复（与补丁同时做）

### 3.1 日期修复
原则：轮次日期（预测点）必须在事件日期当日或之前。

- q13（v4 q13，MSFT capex，S3 6-1）：轮次日期 20241201→20241030
  （事件日期）。原差 32 天。
- S5 1-1 六道题（v4 q_ids 0、14、15、16、17、38）：
  轮次日期 20260101→各题事件日期。
  ANTH anthropic_ipo → 20261110；ALI capex → 20261119；
  BIDU capex → 20261116；BYTE capex → 20260527；
  TCE capex → 20261118；MUSK financing → 20260106。
  逐题事件日期，不取单一日期：S5 1-1 无单一真实日期
  （事件从 2026-01-06 到 2026-11-19；页面标签「2026 年上半年」
  不描述其内容）。单一日期都失败：2026-10-26（S-1 递交日，
  该轮 headline）在 1 月 6 日（xAI Series E）与 5 月 27 日
  （字节）事件之后；2026-06-30（上半年末）在 1 月 6 日事件之后。
  只有逐题事件日期对全部 6 道题都满足 on/before。
  新 SFTB 1-1 问题同法处理（轮次日期 = 事件日期 20260914，
  不是 trace 日期 20260101）。
- q31（v4 q32 = v3 q31，MSFT energy，S4 3-2）：轮次日期
  20250601→20240920（事件日期）。原差约 8 个月。
- 每道修过日期的问题带 `round_date_note` 字段。
- AMZN 2-1 的 23 天提前量未动（轮次日期是真实日期，在事件之前，
  在题集正常提前量范围内）；S4 3-2 q33（MUSK energy，
  事件 20250702 对轮次 20250601，31 天提前量）同样未动。

### 3.2 q57 去重：无题删除，题集为 99 道而非 98 道
任务假定 q57 与另一题重复。核验结果：重复的是 old83 q58
（S5 3-2 BYTE overseas_rental，与 old83 q65 同一事件——
彭博 11-17 Aolani 报道）；v3 重设计时已删 q58、留 q65
（`design/testset-redesign-vision1.md`；`old83-review.json`
两题初评均为 keep，去重后只留 q65）。
testset-v4 里 overseas_rental 只有 1 道（v4 q59 = v3 q57 = old83 q65）。
第 5 轮报告的第 6 项写自过时来源注（「与 q58 同一事件」）。
删 v4 q59 会使该种类剩 0 道题，与「留一道」相悖。
故：90 + 9 − 0 = 99。builder 断言 overseas_rental 恰为 1 道。

### 3.3 上一轮种类字段已移除（`prev_round_kinds`）
根因：第 5 轮 S5 3-2 污染——预测员在 S5 4-1 的问题文件里
通过 `prev_round_kinds` 提前看到 S5 3-2 的种类，q5/q6 须丢弃重跑。
修复位置：新 builder `build_questions_v5.py`（本工作区）
在 context 层就不生成该字段，不只在输出层去掉。
保留的是玩家自己的历史（`player_history_counts`、
`player_most_frequent`、`player_last_kind`、`player_last3`），
那是玩家自己的过去，不是本轮答案。
核验：新生成的 28 个轮次问题文件 + `context-all-v5.json` 里
`prev_round_kinds` 出现 0 次；禁答字段（kind、action、
action_kind、hp_delta、gold_delta）同样 0 次。
问题文件按轮次单独发放（`runs/s5patch-round6-2026-11-22/questions/`），
每道题自带 `round_date`（预测点），文件头带 `round_date` =
trace 轮次日期；两者不同时问题带 `round_date_override`
（共 9 处：8 道修日期题 + 新 SFTB 题）。
词汇表 34 种，取自本工作区 `design/kind-boundary-rules.md`。

## 4. testset-v5

- 总数：99 道（v4 保留 90 道 + 新 9 道 − 去重 0 道）。
  A 集 50 道，B 集 49 道。缺口到 140 道：41 道。
- 分法：与 v4 相同（按 kind/season/round/player 排序，交替分 A/B；
  单边轮次/种类用跨种类交换规则修，两个守卫不变）。
  本轮无单边种类、无单边轮次（≥2 道的种类与轮次均在两侧出现）。
- 9 道新题（v5 q_id）：OAI chatgpt q24（S5 4-1）、GOOG gemini q49
  （S5 5-1）、NVDA megaspeed q63（S5 5-1）、ALI datacenter q32
  （S5 4-1）、TSMC bis_rule q8（S5 6-1）、ORCL financing q44
  （S5 6-1）、AMZN capex q19（S5 2-1）、SFTB financing q43
  （S5 1-1）、MUSK spacex_xai q79（S5 5-1）。
- 前缀：每道新题的前缀 = 该轮次之前全部 trace 动作；
  事实只取更早轮次且事实日期 ≤ 事件真实日期；本轮次事实一律排除。
  前缀违规 0 条，事实日期违规 0 条。
- 事实库：由当前 data.json 的 roundEvidence 重建
  （`runs/s5patch-round6-2026-11-22/facts-roundEvidence-v5.json`），
  与旧的修正版事实库 diff 只允许新增：新增 11 条 =
  上一轮补丁的 2 条（百度 S5 1-1、阿里 NYT S5 5-1）+ 本轮 9 条。
  S3:3-2 的 o1-preview 半句删除沿用旧修正（data.json 里仍有
  「；o1-preview 与 o1-mini 2024-09-12 发布」，修正版事实库已去掉）。
- 事实审计（人工逐条读）：18 条 check-3 标记全部读过，0 条泄题。
  标记分三类：旧历史（2023–2025 年事实）、其他玩家动作
  （如 SFTB 贷款事实出现在 OAI 问题的事实集里——OpenAI 只是抵押物，
  描述的是软银的贷款）、同日其他玩家事件
  （百度 Q3 事实出现在 ALI 问题里；FT 事实出现在 TSMC/ORCL 问题里，
  日期等于事件日期，builder 规则 fact_date ≤ event_real_date 允许，
  且事实来自更早轮次、描述的是其他玩家的动作）。
  审计结论写进 `prefix-audit-v5-new.json` 的 `manual_audit` 段。

## 5. S5 重验结果

- 补丁脚本：`patch_data_round6.py`（本工作区）。
  产出：`runs/s5patch-round6-2026-11-22/patch-summary.json`。
- 页面同步：页面 data.json 先备份为
  `assets/data.json.bak-2026-11-22-round6`（sha256 7eda7ce4…，补丁前），
  再覆写为补丁后文件。新页面 data.json sha256：
  `78c35f31837f3160918d79d1b756cb7b7ff97e874bce509f83d0fae7d1584d3b`。
- 转换：`python3 convert_data_json.py data.json --page <page>/index.html
  --out raw-trace-real.json --provenance raw-trace-real.provenance.json`，
  通过（558 条动作、12 个持仓、10 张关键卡、137 项 reconciliation
  核对；语义 219 已分类 / 339 unknown；既有提示：1 处 roundRV
  不匹配 S5:5-1，记录 RV-2026.2 对解析 RV-2026.1）。
- 提取：`python3 extract.py raw-trace-real.json`，通过；
  trace sha `0f640493059c2b7b8288c596aff66f634ca4667bedbc88609d2a2b72767ce93c`；
  文件 sha256
  `02eb527e1b0c8cf97243f25013eb0948e0dbfd002e230703c1a01fcf30c6c1fc`。
- **`./run.sh` 退出码 0 — S5 重验通过。** 运行目录
  `runs/2026-11-22_054658/`（合并报告 overall pass；fast checker
  pass 3/0/0，覆盖 558 条动作 / 18 名玩家 / 5 个赛季 / 90 个排名 /
  12 条不变量；Lean 构建退出 0；agent gate 跳过，无 claims）。

## 6. 待审池更新

`s6-pending-pool.json`：missed_s5 9→0（空列表）；
meta：testset_n 90→99，gap_to_140 50→41，
last_run_date 2026-11-22，note 记录本轮补丁。
kind_gap 仍为 4（Bonta 起诉 OpenAI、xAI deepfake 诉讼仍在其中；
未新增诉讼/执法种类，Gu 未就此表态）。

## 7. 偏差、未决与后续

1. **题集 99 道，不是任务假定的 98 道。** 原因见 3.2
   （q57 的重复项在 v3 已删，无题可再删）。
2. **旧题集另有 23 处同类日期违规未修。** 本轮只修任务指定的
   3 处（q13、S5 1-1、q31）。全集扫描发现另有 23 道题的轮次日期
   在事件日期之后，最大 500 天（v5 q40，MUSK financing，
   S4 5-1 轮次 20251201 对事件 20250701），其次 372 天（q91，
   ALI tongyi）、286 天（q47，GOOG gemini）、279 天（q28，
   ANTH claude）。多为轮次跨多月的粗粒度标签所致。
   `build_questions_v5.py` 对新题与修日期题强制 on/before，
   其余 23 处记为警告（`runs/s5patch-round6-2026-11-22/
   question-file-warnings-v5.txt`）。是否在下一轮修，由 Gu 定。
3. **S5 1-1 前缀的既有年代错位。** S5 1-1 的动作带虚构 trace 日期
   20260101，但真实事件在 2026 年 1–11 月；按轮次取前缀时，
   后续 S5 轮次的问题前缀会含 S5 1-1 里真实日期晚于本问题事件的
   背景（如 OAI 4-1 问题的腾讯 11-18 资本开支）。
   这不是泄题（无一条描述本问题自己的轮次动作），是 v4 已有的
   结构问题，随 S5 1-1 的虚构日期而来。已记进审计文件。
4. **Grok 4.8 来源等级。** 无 xAI 官方公告，以马斯克 X 帖子为准
   （见 1.9）。若 Gu 要求官方公告才算数，该题须从题集撤下。
5. **FT Megaspeed 放 5-1 是例外。** 见 1.3。
6. **预测实验室看板与 3D 弈盘已过期。** 看板仍显示 90 道题与旧 S5 期末；
   3D 弈盘未动，与页面数据已不一致。两者都不在本任务范围内，
   须另派任务更新。
7. **基线 48/88 未重跑。** 那是 88 道题的参照数；v5 的基线实验是
   下一轮的事。
8. **页面 data.json 备份。** 补丁前版本在
   `assets/data.json.bak-2026-11-22-round6`。

## 8. 交付物（本分支，未合并，未推送）

- `design/s5patch-round6-2026-11-22.md`（本文件）
- `data.json`（已补丁）、`raw-trace-real.json`、
  `raw-trace-real.provenance.json`、`traces/trace-2026-11-22.json`、
  `traces/trace-latest.json`
- `convert_data_json.py`（EXPECTED_LEGACY_COUNTS 更新 5 项）
- `patch_data_round6.py`、`build_testset_v5.py`、`build_questions_v5.py`
- `testset-v5.json`（99 道，A 50 / B 49）
- `s6-pending-pool.json`（missed_s5 0）
- runs/（不入版本库）：`runs/s5patch-round6-2026-11-22/`
  （patch-summary、facts-roundEvidence-v5、prefixes-v5-new、
  prefix-audit-v5-new 含人工审计结论、context-all-v5、
  questions/ 28 个轮次文件、question-file-warnings-v5）、
  `runs/2026-11-22_054658/`（重验运行目录）
