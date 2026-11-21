# 语义种类层（semantic kinds）

2026-11-21。转换器 `convert_data_json.py` 的 `classify_semantic()`，
设计文档与规则表见下。回测 `backtest.py` 已改语义版（见“回测 M1”）。

## 1. 为什么要加这一层

`action_kind` 一直是轮次类型 slug（battle、economy、draft、streak、
civil_war、leverage、settlement、final、wild、event）加 4 个事件种类
（r1、huang_resign、anthropic_ipo、sec_probe）。它说的是“这轮是
什么类型的轮”，不是“这个玩家做了什么动作”。两个下游因此跑不通：

- 场景禁令（`rules/scenarios.json`）用 fixture 的语义种类词汇
  （msft_invest、spacex_xai、stargate、colossus）。真实 trace 的
  action_kind 集合只与它重合 4 种（r1、huang_resign、anthropic_ipo、
  sec_probe），`predict.py --scenarios` 在真实 trace 上直接拒
  （`bans unknown kind 'msft_invest'`）。
- 回测 M1（动作种类全等）在真实 trace 上只量轮次类型预测，不是
  动作预测。

解法：每个 move 保留 `action_kind`（不变），新增 `semantic_kind`
（实质动作线程）。分类只按 move 自己的 action 文本判定，玩家与
轮次编号只用来限定真正有歧义的关键词。

## 2. 词汇表

来源：fixture 的 16 种语义种类（`fixtures/trace-fixture-ok.json`）
加 `overseas_rental`（RV-2026.2 已禁；fixture 的 broken 变体里有
它），再加 2026-11-21 第二次扩展的 14 种（见第 3 节规则 16–29）。
共 31 种，见转换器内 `SEMANTIC_VOCABULARY`。

真实 trace 里实际出现的 29 种（`unknown` 除外）：

| 种类 | 数量 | 说明 |
|---|---|---|
| stargate | 15 | 星门计划线程 |
| anthropic_ipo | 8 | Anthropic 上市线程 |
| msft_invest | 7 | 微软 100 亿美元投资线程 |
| blackwell | 6 | B200 线程 |
| r1 | 6 | R1 线程 |
| musk_table | 6 | 马斯克个人动作线程 |
| colossus | 4 | Colossus 集群线程 |
| spacex_xai | 4 | xAI / Grok 线程 |
| doubao_price_war | 4 | 豆包价格战线程 |
| bis_rule | 4 | BIS 远程规则线程 |
| chatgpt | 3 | ChatGPT / GPT 产品线线程 |
| v3 | 2 | V3 线程 |
| overseas_rental | 2 | 海外算力租赁线程 |
| sec_probe | 1 | SEC 调查线程 |
| huang_resign | 1 | 黄仁勋辞职线程 |
| tongyi | 11 | 通义产品线线程（阿里） |
| hunyuan | 11 | 混元产品线线程（腾讯，含 TCE 微信入口 1 条） |
| wenxin | 11 | 文心产品线线程（百度） |
| ascend | 9 | 昇腾国产卡线程（华为） |
| doubao | 8 | 豆包产品线线程（非价格战部分） |
| pangu | 6 | 盘古行业模型线程（华为） |
| llama | 5 | Llama 开源线线程（豆包拿 Llama 路线 1 条归 doubao，见第 4 节） |
| claude | 5 | Claude 产品线线程 |
| gemini | 4 | Gemini 产品线线程（含 Bard 前身 1 条） |
| open_source | 24 | 开源路线/开源托管线程（产品名已归产品种类的除外） |
| financing | 19 | 融资/债务/借钱线程 |
| capex | 15 | 资本开支线程 |
| energy | 10 | 能源/电力线程（核电 2 条为核心，见第 3 节） |
| megaspeed | 1 | Megaspeed 走私线线程 |

合计 212 条已分类，346 条 `unknown`，共 558 条（2026-11-21
第二次扩展后；扩展前 73 条已分类、485 条 `unknown`）。

**没有实例的两种（从不输出）：**

- `generic`：fixture 里 132 条的兜底种类（普通动作）。真实 trace
  不用它兜底，分不出的标 `unknown`，不得硬归类。
- `openai_mar26`：2026 年 3 月 OpenAI 1220 亿美元轮。move 文本
  里没有任何命中（1220 / 8520 / 1.25万亿 均为 0），故无实例。

## 3. 分类规则（按顺序，第一条命中即定）

每条规则是对 move 的 `action` 文本做子串匹配。规则写死在转换器
内，命中清单由 2026-11-21 对当前 data.json（sha256
`07995677…`）的 558 条 move 文本全量关键词探针得出。

| 优先级 | 种类 | 规则 | 命中 move |
|---|---|---|---|
| 1 | sec_probe | 文本含 `SEC` | S5 6-1 NVDA「SEC 调查报道。恐慌卖出」 |
| 2 | huang_resign | 文本含 `辞职` | S5 4-1 NVDA「CEO 辞职。单轮重扣」 |
| 3 | stargate | 文本含 `星门` | 15 条：S4 1-1 MSFT、S4 1-2 NVDA/OAI/MSFT/AAPL/ORCL/TSMC/SFTB、S4 1-3 ORCL/SFTB、S4 4-1 ORCL/SFTB、S5 1-1 SFTB、S5 2-1 ORCL、S5 6-2 SFTB |
| 4 | colossus | 文本含 `Colossus`，或玩家 MUSK 且含 `集群` | 4 条：S2 4-1、S3 1-1、S3 4-1、S4 1-2（均为 MUSK） |
| 5 | spacex_xai | 文本含 `xAI` / `Grok` / `SpaceX` | 4 条：S2 2-1「宣布组建 xAI」、S2 5-1 / S3 3-2 / S4 4-1 Grok |
| 6 | musk_table | 文本含 `马斯克`，或玩家 MUSK 且含 `推特` | 6 条：S1 1-1、S1 2-1、S1 2-5、S1 3-2、S2 1-1、S2 4-5（均为 MUSK） |
| 7 | r1 | 文本含 `R1`，或 S4 1-1 轮且含 `DeepSeek` | 6 条：S4 1-1 AMZN/HUAWEI/DPSK/TSMC（R1）+ TCE/ORCL（DeepSeek） |
| 8 | v3 | 文本含 `V3` | 2 条：S3 6-1 HUAWEI、DPSK |
| 9 | blackwell | 文本含 `B200` / `B300` / `Blackwell` / `GB200` | 6 条：S3 2-1 NVDA/MSFT/GOOG/ALI/ORCL/TSMC |
| 10 | doubao_price_war | 文本含 `价格战` / `降价` / `价格再降` | 4 条：S2 5-1 BIDU「文心年底降价伏笔埋下」、S3 3-2 BYTE「豆包多模态跟进。价格再降」、S3 6-1 BYTE「豆包价格战被验证」、BIDU「文心降价跟随」 |
| 11 | bis_rule | 文本含 `BIS` / `出口管制` / `远程规则` | 4 条：S5 3-2 TSMC「出口管制执行方」、ALI「阿里海外云节点受远程规则关注」、S5 5-1 BYTE「BIS 远程规则收紧」、DPSK「权重开源分发不受远程规则限」 |
| 12 | anthropic_ipo | 文本含 `IPO`（不含 `未上市`）；或玩家 ANTH 且含 `上市`（不含 `未上市`）；或玩家 ANTH 且含 `募资`；或玩家 ANTH 且 S5 1-1 轮含 `承诺` | 8 条：S5 1-1 ANTH「9009 亿美元承诺签字方」、S5 2-1 ANTH「IPO 进程启动」、S5 4-1 ANTH「上市路演期」、S5 5-1 ANTH「分阶段募资到手」、MUSK「后续 IPO 排队者窗口变窄」、SFTB「后续 IPO 窗口变窄」、S5 6-1 ANTH「上市次日跌 8.5%」、S5 6-2 ANTH「募资已到账」 |
| 13 | msft_invest | 玩家 MSFT/OAI 且含 `100 亿美元`；或玩家 MSFT 且含 `追加投资`；或含 `循环图最大投资方` | 7 条：S1 3-2 OAI/MSFT、S2 1-1 OAI/MSFT（100 亿美元）、S1 2-5 MSFT「追加投资谈判启动」、S4 5-1 MSFT/OAI「循环图最大投资方」 |
| 14 | chatgpt | 文本含 `ChatGPT` / `GPT-4`（含 GPT-4o） | 3 条：S1 2-1 BYTE「类 ChatGPT 托管」、S2 2-1 OAI「GPT-4 接入 Bing 和 Office」、S3 3-2 OAI「GPT-4o 声量赢」 |
| 15 | overseas_rental | 文本含 `海外算力` | 2 条：S5 3-2 BYTE「海外算力租赁需求被点名」、S5 4-1 BYTE「抢租海外算力报道的主角之一」 |
| — | unknown | 以上全不命中 | 485 条（扩展前；扩展后 346 条，见下） |

### 第二次扩展：规则 16–29（2026-11-21）

新规则块整体排在 15 条旧规则之后。顺序即优先级，第一条命中
即定。探针方法与第一次相同：对当前 data.json（sha256
`07995677…`）的 558 条 move 文本全量关键词探针，逐项核验与旧规
则的重叠。回归保证：旧 73 条逐项不变（内存模拟先验 + 重抽取后
与备份 trace 逐条比对 0 差异 + 转换器内
`EXPECTED_LEGACY_COUNTS` 冻结 15 种旧种类计数，任一计数移动即
失败）。

| 优先级 | 种类 | 规则 | 命中 move（新增数） |
|---|---|---|---|
| 16 | tongyi | 文本含 `通义` | 11 条：S1 1-4 / S1 2-1 / S1 2-5 / S2 2-1 / S2 3-2 / S2 5-1 / S3 3-2 / S3 5-1 / S3 6-1 / S4 1-1 / S4 4-1（均为 ALI；S3 2-1 ALI「通义新版发布。阿里云打包 B200 替代方案」含 B200，旧规则 9 blackwell 优先，仍属 blackwell，不计入此） |
| 17 | hunyuan | 文本含 `混元`，或玩家 TCE 且含 `微信` | 11 条：混元 10 条（S1 1-1 / S1 2-1 / S1 2-5 / S2 2-1 / S2 3-2 / S2 5-1 / S3 2-1 / S3 3-2 / S3 5-1 / S4 4-1）+ TCE S2 1-1「围观。微信入口不押注单队」 |
| 18 | ascend | 文本含 `昇腾` | 9 条：S1 1-1 / S1 2-5 / S2 2-6 / S2 4-1 / S2 5-1 / S3 1-1 / S3 2-1 / S3 5-1 / S5 1-1（均为 HUAWEI；S4 1-1 HUAWEI「昇腾成 R1 落地主平台」旧规则 7 r1 优先，仍属 r1） |
| 19 | doubao | 文本含 `豆包` | 8 条：S1 2-5 / S2 2-1 / S2 3-2（含「拿 Llama 路线做内部版」，doubao 优先于 llama，见第 4 节）/ S2 5-1 / S3 2-1 / S3 5-1 / S4 1-1 / S4 4-1（均为 BYTE；价格战 2 条旧规则 10 优先，仍属 doubao_price_war） |
| 20 | wenxin | 文本含 `文心` | 11 条：S1 1-4 / S1 2-1 / S1 2-5 / S2 1-1 / S2 2-1 / S2 3-2（「文心开源跟进」，wenxin 优先于 open_source）/ S3 2-1（「文心新版。昆仑芯三代流片」）/ S3 3-2 / S3 5-1 / S4 1-1 / S4 4-1（均为 BIDU；降价 2 条旧规则 10 优先，仍属 doubao_price_war） |
| 21 | pangu | 文本含 `盘古` | 6 条：S1 1-4 / S1 2-1 / S2 2-1 / S2 3-2（「盘古开源行业模型」，pangu 优先于 open_source）/ S3 3-2 / S4 4-1（均为 HUAWEI） |
| 22 | llama | 文本含 `Llama` | 5 条：S2 2-1 META「Llama 1 权重流出」、S2 3-2 MSFT/OAI「把 Llama 上架 Azure」/「上架 Llama」、S2 3-2 META「Llama 2 开源」、S3 3-2 META「Llama 3 开源跟进」（BYTE S2 3-2 豆包拿 Llama 路线归 doubao，见规则 19） |
| 23 | claude | 文本含 `Claude` | 5 条：S1 2-1 / S2 2-1 / S2 3-2 / S3 3-2 / S4 4-1（均为 ANTH） |
| 24 | gemini | 文本含 `Gemini` / `Bard` | 4 条：S2 5-1 / S3 3-2 / S4 4-1 Gemini（均为 GOOG）+ S2 2-1 GOOG「Bard 演示出错。市值蒸发」（Bard 为 Gemini 前身产品，同一谷歌对话产品线程） |
| 25 | megaspeed | 文本含 `Megaspeed` | 1 条：S5 3-2 HUAWEI「Megaspeed 线牵连国产链声誉。中方否认间谍叙事」 |
| 26 | energy | 文本含 `核电` / `三哩岛` / `电力` / `绿电` / `燃气电厂` / `供电` | 10 条（全在 S4 3-2 能源轮）：OAI「签核电重启合同。三哩岛入局」、MSFT「三哩岛核电合同。保电力」、ANTH「靠云厂电力间接受益」、META「园区选址被电力拖慢」、AAPL「抢签电力。园区扩张」、MUSK「自建燃气电厂抢时间」、BYTE「火山引擎抢签绿电园区」、ALI「阿里云西部园区与绿电布局占优」、NVDA「卖整柜方案。含供电设计」、HUAWEI「卖整柜含供电方案。国产版」 |
| 27 | financing | 文本含 `融资` / `债务` / `借钱` | 19 条：融资 11 条（ANTH S1 2-5「拿到谷歌等新融资线索」/ S1 3-2「靠融资续命」/ S3 6-1「成本话题对其融资故事不利」、BYTE S1 3-2「国内融资收紧」、DPSK S1 3-2「量化主业供血。不靠融资」、AMZN S3 4-1「项目融资模式扩散」、ORCL S4 5-1「债务加股权双线融资」/ S5 1-1「债务融资继续加码」/ S5 2-1「融资窗口全开」/ S5 6-1「未上市。融资环境骤冷」/ S5 6-2「融资窗口观察中」）+ 纯债务 5 条（AAPL S3 6-1「债务包热销。窗口全开」、ORCL S4 5-1「约 380 亿美元债务包挂单」/ S5 5-1「债务包约 100 亿美元未配售曝光」/ S5 6-1「债务担忧带跌」/ S5 6-2「等债务包配售结果」）+ 纯借钱 3 条（AAPL S2 4-1「借钱扩云。杠杆起步」/ S3 1-1「资本开支翻倍。借钱扩容」/ MSFT S3 4-1「表内借钱稳健。杠杆中等」；其中 S3 1-1 AAPL 同时含资本开支，financing 优先于 capex） |
| 28 | capex | 文本含 `资本开支` | 15 条：S3 1-1 9 条（OAI/MSFT/GOOG/META/AMZN/BYTE/TCE/BIDU/TSMC；AAPL 该轮「资本开支翻倍。借钱扩容」归 financing，规则 27 优先）/ S3 6-1 MSFT「资本开支再上调」/ S4 1-3 MSFT「被带跌。资本开支被质问」/ S5 1-1 BYTE/ALI/TCE / S5 6-2 TCE「等资本开支指引」 |
| 29 | open_source | 文本含 `开源` 且不含 `不开源` | 24 条：S1 1-4 MSFT/META/AMZN/AAPL、S2 1-1 META、S2 3-2 NVDA/GOOG/AMZN/MUSK/AAPL/ORCL/TSMC/SFTB、S2 4-5 META、S2 5-1 META、S3 5-1 META、S3 6-1 META、S4 1-1 META/ORCL、S4 1-3 META、S5 3-2 DPSK、S5 6-1 DPSK、S5 6-2 DPSK。产品名已归产品种类的 11 条不在此（通义 6、混元 1、Llama 2、文心 1、盘古 1）；DPSK S5 5-1「权重开源分发不受远程规则限」旧规则 11 bis_rule 优先；GOOG S1 1-4「Imagen 不开源」被排除，仍 unknown |

新规则共从 unknown 池分类 139 条：tongyi 11、hunyuan 11、
ascend 9、doubao 8、wenxin 11、pangu 6、llama 5、claude 5、
gemini 4、megaspeed 1、energy 10、financing 19、capex 15、
open_source 24。合计已分类 73 + 139 = 212 条，unknown 346 条
（62.0%）。拟合窗口 S1–S3 已分类 129/324 条（扩展前 32 条）；
回测窗口 S4–S5 M1 分母 83 条（扩展前 41 条）。

## 4. 刻意排除的歧义（探针已核验）

- `100 亿美元` 限定 MSFT/OAI：ORCL S5 5-1「债务包约 100 亿美元
  未配售曝光」是甲骨文的债，不是微软的投资。
- `上市` 限定 ANTH：SFTB S1 2-1「ARM 上市筹备」是 Arm 的 IPO，
  不是 Anthropic 的。
- `IPO` / `上市` 排除 `未上市`：MUSK 的「未上市。无股价扣血」
  （S4 1-3）、「未上市。融资环境骤冷」（S5 6-1）与 BYTE 的「字节
  未上市无股价」（S5 2-1）都是“没上市”，不是上市动作。
- `承诺` 只认 ANTH S5 1-1：`承诺` 全表 16 命中，其余是采购承诺
  （ANTH S3 4-1「云厂承诺式采购」、S4 5-1「承诺采购规模被盘问」）
  或其他玩家的收款方表述（S5 1-1 NVDA/OAI/MSFT/GOOG/META/AMZN/
  HUAWEI/ORCL/TSMC 等），都不是 Anthropic 上市线程。
- `定价权` 不是价格战：TSMC S2 2-1、NVDA S2 2-6 与 S3 4-1 的
  「定价权升/拉满」是卖方定价权，不归入 doubao_price_war。
- `扩散` 不归入 bis_rule：AMZN S3 4-1「项目融资模式扩散」是融资
  模式扩散，不是 AI 扩散规则。
- `循环图` 只认 `循环图最大投资方`：NVDA S4 5-1「循环图中心节点」
  与 ALI「国内循环图成型」不是投资动作。
- `不参与星门`（AAPL S4 1-2）仍算 stargate：拒绝参与是针对该
  线程的立场，不是无关动作。
- `豆包` / `通义` / `混元` / `昇腾` 等产品名本身不对应任何种类
  （见第 5 节），只有它们的价格战动作（第 10 条）才进
  doubao_price_war。——**此条已废止（2026-11-21 第二次扩展）**：
  产品名现在对应产品种类（规则 16–24：tongyi、hunyuan、ascend、
  doubao、wenxin、pangu、llama、claude、gemini）。保留原文作废
  止记录，见第 5 节更新后的缺口表。

## 4a. 第二次扩展的歧义排除（探针已核验）

- 产品规则优先于通用规则：产品 move 里常含 `开源`（通义 6 条、
  混元 1 条、Llama 2 条、文心 1 条、盘古 1 条），一律归产品种类，
  不归 open_source。open_source 只收产品名未命中的剩余开源动作。
- `豆包拿 Llama 路线做内部版`（BYTE S2 3-2）归 doubao，不归
  llama：句子的主语是豆包，Llama 是路线/方法；BYTE 的动作是做
  自己的豆包内部版。doubao 规则排在 llama 之前。
- `不开源` 排除：GOOG S1 1-4「Imagen 不开源。先手让出」是“不
  开源”，不是开源动作，仍 unknown。open_source 规则显式排除
  `不开源`。
- `融资` 不过宽（全量探针）：`融资` 11 命中全是融资线程（拿融资
  线索、靠融资续命、融资收紧、融资故事、融资窗口、融资环境）。
  边界两例也收入 financing：DPSK「量化主业供血。不靠融资」是
  资金来源表态，仍属融资线程；AMZN「项目融资模式扩散」是融资
  模式扩散（旧排除只说它不是 bis_rule，不冲突）。`债务` 7 命中
  全是债务包/债务融资线程（其中 2 条同时含融资）；`借钱` 3 命中
  全是借款扩容。`融资`/`债务`/`借钱` 三词在已分类 move 里 0 命
  中（与 anthropic_ipo 的 `募资` 是不同词，无重叠）。
- `债务包约 100 亿美元`（ORCL S5 5-1）归 financing，不归
  msft_invest：旧规则 13 的 MSFT/OAI 限定不变；该 move 现在由
  规则 27 的 `债务` 命中，进 financing——这是甲骨文的债，与微
  软投资无关，分类与旧排除一致。
- `资本开支` 与 `融资`/`借钱` 的唯一重叠：AAPL S3 1-1「资本开
  支翻倍。借钱扩容」同时含两词，financing 优先（规则 27 在 28
  之前），记为 financing。理由：该 move 的动作是借钱扩容，资本
  开支是用途。其余 15 条资本开支 move 不含融资/债务/借钱。
- energy 的边界：`省电` 不进 energy（AAPL S2 4-1「M 系列芯片
  省电优势」是芯片能效，不是能源采购）；`电商` 不进 energy
  （ALI S1 3-2「电商现金流供血」含电字但与能源无关）。energy
  的 6 个关键词（核电/三哩岛/电力/绿电/燃气电厂/供电）全表命
  中 10 条，全在 S4 3-2 能源轮，无一已分类 move 被命中。
- `微信` 只认 TCE：`微信` 全表 5 命中全是 TCE，其中 4 条同时含
  混元（已归 hunyuan），第 5 条 S2 1-1「围观。微信入口不押注
  单队」由 TCE 限定补入 hunyuan。其他玩家无微信 move。
- `昆仑芯` 不建种类：BIDU 3 条含昆仑芯，其中 S3 2-1 同时含文
  心（已归 wenxin）；其余 2 条（S2 2-6「昆仑芯自研对冲卡价」、
  S2 4-1「昆仑芯订单升。对冲见效」）只有 2 条，暂留 unknown，
  见第 5 节。
- 扩散词不建种类（全量探针核验）：`订单` 28 命中、`推理` 23 命
  中、`算力` 10 命中、`云厂` 9 命中、`火山引擎` 9 命中、`芯片`
  7 命中、`股价` 7 命中、`产能` 5 命中、`Azure` 5 命中、`流片`
  4 命中、`Copilot` 2 命中等，都是跨玩家的通用业务词或云平台
  提及，没有单一动作线程；`Vision Pro 发布。与 AI 无关` 明确
  写了与 AI 无关。以上全部留 unknown，见第 5 节。

## 5. 词汇缺口（有实质线程，但 fixture 词汇里没有种类）

以下 move 文本里有明确的产品/事件线程，但 fixture 的 16 种里没有
对应种类，按“不得编造种类”一律标 `unknown`。将来扩展词汇时再议，
本次不加：

| 线程 | 命中数 | 备注 |
|---|---|---|
| Claude（Anthropic 产品线） | 5 | ANTH S1 2-1 至 S4 4-1 |
| Gemini（谷歌产品线） | 3 | GOOG S2 5-1、S3 3-2、S4 4-1 |
| Llama（Meta 开源线） | 6 | META/OAI/MSFT/BYTE |
| 昇腾（华为国产卡线） | 10 | HUAWEI 全季 |
| 豆包（非价格战部分） | 7 | BYTE（价格战 3 条已分类） |
| 混元（腾讯产品线） | 10 | TCE 全季 |
| 通义（阿里产品线） | 12 | ALI 全季 |
| 核电/电力合同 | 2 | OAI/MSFT S4 3-2 三哩岛 |
| Megaspeed 线 | 1 | HUAWEI S5 3-2 |
| 融资/资本开支/开源（泛） | 多 | 通用经济动作，无专属种类 |

后果：`unknown` 占 485/558（87%）。这是诚实分类的结果，不是
分类器失效。回测 M1 只在可分类子集上量（见第 7 节）。

**更新（2026-11-21 第二次扩展）：上表已全部覆盖。** 通义 12 条
中 11 条归 tongyi（1 条已是 blackwell）；混元 10 条归 hunyuan；
昇腾 10 条中 9 条归 ascend（1 条已是 r1）；豆包非价格战 8 条归
doubao（价格战 2 条本就已分类；本表旧数 7 是探针口径差异——
豆包全表 10 条，价格战 2 条，非价格战 8 条）；Llama 6 条中 5 条
归 llama（1 条归 doubao）；Claude 5 条归 claude；Gemini 3 条 +
Bard 1 条归 gemini；核电 2 条扩为 energy 10 条（同轮的电力/绿
电/燃气/供电动作是同一能源线程）；Megaspeed 1 条归 megaspeed；
融资/资本开支/开源归 financing 19 条、capex 15 条、open_source
24 条。另补两条任务清单之外的同形产品线：文心 11 条（BIDU）、
盘古 6 条（HUAWEI）——与通义/混元同形，探针发现后一并覆盖，
见第 3 节规则 20–21。

**剩余缺口（第二次扩展后，346 条 unknown）：**

| 线程/词 | 命中数 | 不建种类的理由 |
|---|---|---|
| 订单（订单簿/订单涨） | 28 | 跨玩家通用业务词，无单一动作线程 |
| 推理（推理需求/推理线） | 23 | 跨玩家能力词，S3 5-1 轮遍布各家 |
| 算力（算力需求/算力差距） | 10 | 通用资源词 |
| 云厂/火山引擎（云平台提及） | 9 / 9 | 云厂商提及，无单一线程；火山引擎的 capex/energy/bis 动作已各归其类 |
| 芯片（芯片订单/自研芯片） | 7 | 通用词；星门芯片 1 条已归 stargate |
| 股价/市值（市场反应词） | 7 / 2 | 市场状态词，不是动作 |
| 产能/出货/流片 | 5 / 2 / 4 | 供应链通用词；910B 出货 1 条已在昇腾 move 内归 ascend |
| Azure / AWS / Copilot / Bedrock | 5 / 3 / 2 / 1 | 云平台子线程，条数少且含义杂（托管、上架、扩容混在一起） |
| 昆仑芯（百度自研卡） | 2 | 只有 2 条纯命中（第 3 条已归 wenxin），太薄 |
| 抖音基本盘 / 微信入口（非混元） | 1 / 1 | 单条提及；微信 1 条已补入 hunyuan |
| Vision Pro 发布 | 1 | 文本自述“与 AI 无关” |

结论与第一次相同：`unknown` 占 346/558（62.0%）仍是诚实分类
的结果。第二次扩展证明：覆盖率可以继续涨，但拟合没有因此出现
信号（见 design/fitting-layer.md 第二次真拟合附录）——瓶颈已
从词汇转向模型族。

## 6. 没有采用轮次主题默认规则

曾考虑：按轮次标题（如 S4 1-3「血崩日」→ r1）给整轮 move 默认
种类。否决，原因：fixture 里“整轮同一种”是合成生成器的粗糙
写法；真实 trace 里同一轮常有不同线程（S5 5-1 轮里 BYTE 是
bis_rule、ANTH 是 anthropic_ipo；S2 1-1 轮里 GOOG 是 Bard 演示
事故，与 msft_invest 无关）。按轮次默认会错标。分类只认 move
自己的文本；轮次编号只在第 7 条（DeepSeek 限 S4 1-1）与第 12 条
（承诺限 ANTH S5 1-1）里做限定。

## 7. 回测 M1（语义版）

`backtest.py` 已改语义版（`predict.py` 未动，禁区）：

- 候选种类：prefix 里出现过的 semantic_kind，排除 `unknown`
  （它不是玩家能做的动作）与当轮被禁种类；若全被禁，回退到该轮
  记录的 semantic_kind（若已知），否则回退到全部语义种类。
- 期望增量：本地复刻 `predict.expected_deltas` 的逻辑，按
  semantic_kind 分组（逐玩家、全局两张均值表），再调
  `P.make_expectation` 与 `P.best_response`（二者对种类名通用）。
- M1：预测种类 == 记录的 semantic_kind，且记录的种类已知才算
  命中；`unknown` 记录不计入 M1 分母（记 `m1_unknown_n`）。
  M2–M5 不变（不依赖种类）。
- 无 semantic_kind 字段的 trace（如 fixture）回退到 action_kind，
  fixture 回测数字与改前逐项相同（回归已验：M1 5.56%、M2
  49.57%、M3 61.11%、M4 45.73%、M5 81.62%）。

**真实 trace 回测（2026-11-21，`runs/2026-11-21_123045/`，测试窗
S4–S5，n=234）：**

| 指标 | 命中率 | 基线 | 裕度 | 信号 |
|---|---|---|---|---|
| M1（语义动作） | 0.0%（0/41） | 9.55% | −9.55pp | 否 |
| M2（Δ血方向） | 35.47% | 50% | −14.53pp | 否 |
| M3（Δ金方向） | 25.21% | 50% | −24.79pp | 否 |
| M4（段位段） | 32.05% | 12.5% | +19.55pp | 是 |
| M5（量级 ±10） | 81.2% | 82.93% | −1.74pp | 否 |

M1 分母 41（S4 22 条、S5 19 条），193 条 unknown 被排除。可分类
41 条的记录种类分布：stargate 15、anthropic_ipo 8、r1 6、bis_rule
4、msft_invest 2、overseas_rental 2、colossus 1、spacex_xai 1、
huang_resign 1、sec_probe 1。模型在 41 条上预测的种类：v3 33 次、
blackwell 4 次、r1 4 次——一次未中（v3 在测试窗可分类集里一次
也没实际出现；占位参数下它的历史均值增量最优，模型反复选它）。
全量 S1–S5（样本内，非校准）：M1 8.33%，m1_n=72（S1 1-1 轮因
prefix 为空被跳过，含 1 条可分类 move：MUSK「马斯克忙于收购推
特」）。

只记录，不评判。校准是下一步（真拟合），不在本任务内。

### 第二次扩展后的回测（2026-11-21，`runs/fit-real-2026-11-21-02/`，测试窗 S4–S5，n=234）

| 指标 | 拟合 v1 投影 | 占位 v2 | 基线 | 拟合信号 |
|---|---|---|---|---|
| M1（语义动作） | 2.41%（2/83） | 0.0%（0/83） | 4.30% | 否 |
| M2（Δ血方向） | 34.19% | 35.04% | 50% | 否 |
| M3（Δ金方向） | 24.79% | 25.21% | 50% | 否 |
| M4（段位段） | 35.90% | 36.32% | 12.5% | 是（两者都有） |
| M5（量级 ±10） | 82.48% | 82.05% | 82.93% | 否 |

M1 分母 83（S4 48 条、S5 35 条），151 条 unknown 被排除。拟合
的 2 次 M1 命中都在 S4（2/48，4.17%），S5 0/35。拟合相对占位：
M1 +2.41pp、M5 +0.43pp，M2 −0.85pp、M3 −0.42pp、M4 −0.42pp——
混合，未达到采用标准（见 design/fitting-layer.md 第二次真拟合
附录）。拟合 M1 仍低于随机基线 4.30%（种类从 15 增至 29，基线
从 9.55% 降至 4.30%）。全量 S1–S5（样本内）：拟合 M1 4.78%
（m1_n=209），占位 M1 7.66%——样本内拟合也不如占位。

## 8. 场景禁令：数据侧已通，代码侧还差一行

**语义校验（数据侧）：通过。**真实 trace 的 semantic_kind 集合
含全部 4 个被禁种类（msft_invest 7 条、spacex_xai 4 条、stargate
15 条、colossus 4 条）。四条分支的禁令在语义集里全部可寻：

- SC-BASE：无禁令。
- SC-BIS-TIGHTEN：禁 msft_invest、spacex_xai——语义集里有。
- SC-RASA：再禁 stargate、colossus——语义集里有。
- SC-TRUCE-EXPIRE：禁 msft_invest、spacex_xai，hp_cap 100→80。

**`predict.py --scenarios`（代码侧）：仍拒绝，exit 2。**

```
predict: scenario SC-BIS-TIGHTEN bans unknown kind 'msft_invest'
(not in the trace kind set)
```

原因：`predict.py` 的种类集只读 `action_kind`，不读
`semantic_kind`。本任务禁区不许改 `predict.py`，故未动。需另行
授权的最小改动（共 3 处，加一个 `kind_of` 辅助函数，
semantic_kind 优先、缺失时回退 action_kind，与 `backtest.py` 的
做法相同）：

1. `expected_deltas`（约 142–143 行）：按 `m["action_kind"]`
   分组 → 按 semantic_kind 分组。
2. `run_scenarios`（约 690 行）：`all_kinds = sorted({m["action_kind"]
   for m in trace["moves"]})` → semantic_kind。
3. `main`（约 844 行 `all_kinds`、约 855 行 `start_actions`）：
   同上改 semantic_kind；第 895–901 行的禁令校验随 `all_kinds`
   自动生效。

另注意：`predict.py` 约 312 行的 agent-claim fork 路径也按
`action_kind` 查禁令（`move["action_kind"] in banned`），语义禁令
在该路径同样查不到——与场景路径同类问题，改时一并评估，不在本
任务内。

## 9. 与检查层的关系（未动）

- C5 只查 `action_kind`（轮次类型 slug 与 4 个事件种类），不查
  semantic_kind。`overseas_rental` 在语义层有 2 个实例（BYTE S5
  3-2、S5 4-1），但 C5 不认语义种类——这是检查层与语义层词汇
  不一致的已知缺口，本任务不改 `check.py`，记在这里，待后续任务
  定夺（是否把语义禁令纳入 C5）。
- 转换器自检新增三项硬检查：4 个 EVENT_KINDS move 的
  semantic_kind 必须等于其事件种类（语义规则复现事件种类）；
  每个输出的 semantic_kind 必须在 `SEMANTIC_VOCABULARY` 内或为
  `unknown`；15 种旧种类的计数冻结在 `EXPECTED_LEGACY_COUNTS`
 （第二次扩展新增：新规则只能从 unknown 池分类，偷旧命中即
  失败）。分布只记日志，不失败。

## 10. 本次重抽取

- 页面 data.json：`~/workspace/ts-spaces/jin-chan-chan-fu-pan-ai-da-ting-2022-2026/assets/data.json`，
  194,222 字节，sha256
  `07995677f405f030d66188e6ab910450bb50db96dbcc3549556f066d941f365d`
  （2026-11-21 12:29 拷贝；内含集成众数并列展示新增的
  `forecast.ensemble`，不影响 move 数据——与旧 raw trace 逐条
  比对，忽略 semantic_kind 后 0 差异）。
- Raw trace：`raw-trace-real.json`（schema v3），provenance：
  `raw-trace-real.provenance.json`（新增 `semantic_kinds` 节）。
- Canonical trace：`traces/trace-latest.json`（schema v4，558 条，
  全部含 semantic_kind），meta trace_sha256
  `7d8dfe58667c602b100c2ba4dbc3bf356fff0f0ae17015140679f9cecafd26d8`
  （文件实测 sha256
  `fd79d114387f30e19139c91d086446ac63df1fa4efdb8894e302abfbc4b99a63`；
  二者不同是 extract.py 的既有行为：meta 哈希在嵌入哈希字段
  之前算出）。
- 历史层重跑：`runs/2026-11-21_123024/` 总体 **pass**（检查器
  0 失败、0 gap，Lean 构建退出码 0）。C5 跨度规则与 C6 不同卡计数
  未动、未回退。
- 预测层重跑：`runs/2026-11-21_123045/` 总体 **pass**（历史层
  pass；预测章 fail，按规矩判——回测低于阈值；符号动力 pass）。

## 11. 本次重抽取（第二次扩展，2026-11-21）

- 词汇扩展：规则 16–29（见第 3 节），词汇表 17 → 31 种；转换
  器自检新增 `EXPECTED_LEGACY_COUNTS` 冻结检查（15 种旧种类计
  数任一移动即失败）；provenance 的 `semantic_kinds` 节自动同
  步（词汇表与分布由代码生成，无手写）。
- 页面 data.json：未动，仍为 `07995677…`（194,222 字节；重拷
  贝后 sha256 逐字节相同）。
- 旧 trace 备份：`traces/trace-2026-11-21-2fd0b38f.json`（重抽
  取前 trace-latest.json 的原样拷贝，以旧 meta.trace_sha256
  `2fd0b38f…` 命名）。
- Raw trace：`raw-trace-real.json`（schema v3），provenance：
  `raw-trace-real.provenance.json`（`semantic_kinds` 节已同步新
  分布）。
- Canonical trace：`traces/trace-latest.json`（schema v4，558 条，
  全部含 semantic_kind），meta trace_sha256
  `4ec473d21acb568928a14718ad19dbdb0f673a0d1016aeb664c1b873adf8b572`
  （文件实测 sha256
  `f4bcebd971bb563440705cd056ef54553895086497fa81438ed0ec457a8a2608`；
  二者不同是 extract.py 的既有行为：meta 哈希在嵌入哈希字段
  之前算出），meta source_sha256 `07995677…`（= data.json）。
  回归检查：与备份比对，非语义字段 0 差异；旧已分类 73 条逐项
  不变；新分类 139 条，全部来自 unknown 池。
- 历史层重跑：`runs/2026-11-21_131852/` 总体 **pass**（检查器
  0 失败、0 gap，Lean 构建退出码 0）。C5 跨度规则与 C6 不同卡
  计数未动、未回退。
- 覆盖率：212 条已分类、346 条 unknown（62.0%）；拟合窗口
  S1–S3 已分类 129/324 条；回测窗口 S4–S5 M1 分母 83 条。

## 12. 本次重抽取（第三次扩展，2026-11-22；第 5 轮样本扩大）

- 目的：第 5 轮锦标赛样本扩大——把 S4–S5 可分类题从 83 道扩到 105 道，
  让方法之间的比较更可靠（83 道太少，测不出小差距；排定名次前约需
  140 个已结算预测）。纪律与前两次相同：全量关键词探针、第一命中即定、
  只按 move 自己的 action 文本判定、分不出标 unknown 不硬归类；新规则
  排在全部旧规则之后，只能从 unknown 池分类（EXPECTED_LEGACY_COUNTS
  冻结 15 种旧种类计数，任一移动即失败）。
- 规则 30 datacenter（数据中心园区线程）：文本含“园区”或“数据中心”。
  “园区”全表 14 命中（4 条已是 energy，10 条 unknown）；“数据中心”
  全表 2 命中（全 unknown）。新分类 11 条：S4 1-2 7 条（GOOG、ANTH、
  META、AMZN、BYTE、HUAWEI、DPSK）、S4 3-2 4 条（AAPL、BIDU、DPSK、
  TSMC）。S4 3-2 P12 TCE（腾讯云园区并网排队中）因“并网”先归 energy。
- 规则 31 compliance（合规自查线程）：文本含“自查”。全表 5 命中，
  全 unknown，全在 S5 3-2（MSFT、GOOG、AMZN、ORCL、TCE）。P6 AMZN
  的“无关本线”前缀是边界，已标出。
- 规则 32 invest_plan（宣布投资计划线程）：文本同时含“宣布”和“投入”。
  全表 4 命中（S3 1-1 P11 ALI；S4 1-2 P11 ALI、P12 TCE、P13 BIDU），
  S4–S5 新分类 3 条。裸词“投入”全表 9 命中（5 条是状态，如“搜索守成。
  AI 投入最早”），是扩散词，不建种类。
- 规则 26 energy 扩两个关键词（“能源”、“并网”）：各全表 2 命中，
  全 unknown，全在 S4 3-2（GOOG、AMZN、TCE），新分类 3 条。
- 刻意不分类的：S4 1-1 的市场反应（先跌后稳、相对抗跌等 6 条）、
  S4 1-3 的带跌（14 条）、S4 5-1 的循环图位置描述（14 条）、S5 1-1
  的承诺收款方角色（11 条）、S5 2-1 的跟涨（15 条）、S5 3-2 的无关
  本线（5 条）、S5 4-1 与 S5 6-1 的被带跌/大盘带跌、S5 6-2 的守阵
  （8 条，守阵是非动作）、“守阵”、“循环”、“订单”（28 命中）、
  “推理”（23 命中）等扩散词、“旗舰发布”（仅 1 条，太薄）、
  “承建/收款方/承诺”（角色，非动作）。剩余 S4–S5 unknown 129 条，
  是诚实分类的结果，不是分类器失效。
- 边界（须做敏感性分析）：S4 1-2 P15 DPSK“不建园区”（拒绝，沿用
  星门先例“不参与星门仍算 stargate”）；S4 3-2 P15 DPSK“无园区负担”
  （状态，非动作）；S5 3-2 P6 AMZN“无关本线、云合规自查”。
- 重抽取验证：转换器首次不带 `--page` 跑失败（FACTS 交叉检查：
  '1073.4' 不在页面文本里，FACTS 表过期）；带
  `--page ~/workspace/ts-spaces/jin-chan-chan-fu-pan-ai-da-ting-2022-2026/index.html`
  后通过：558 条，235 已分类 / 323 unknown（原 212/346），+23 条；
  15 种旧种类计数全部冻结未动；新 trace
  `traces/trace-latest.json`（schema v4），与旧 trace 比对：非语义
  字段 0 差异、旧已分类 212 条逐项不变、新分类 23 条全部来自 unknown 池；
  meta source_sha256 `07995677…`（= data.json，data.json 未动）；
  S4–S5：234 条，105 已分类 / 129 unknown。
- 题集：test105.json（105 道：S4 65 道、S5 40 道；全新种类 39 道，
  原 83 道里 24 道；新题 22 道：S4 17 道、S5 5 道）。first_appearance
  是轮次级（该种类从未在任何更早的轮次出现；同一轮内的 move 互不计数），
  与 test83 比对 0/83 差异（按 move 算差 15 道，按玩家算差 12 道）。
