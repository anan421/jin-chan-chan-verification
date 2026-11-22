# 种类边界规则（2026-11-22，题集重设计）

原则：种类由动作本身决定，不由提及决定。产品发布 = 产品种类。基建建设 = 基建种类。具名产品开源 = 产品种类。开源作为策略（无具名产品）= open_source。每条规则只认动作本身，提及不算。

| 种类 | 规则（一句话） |
|---|---|
| stargate | 星门计划本身：宣布、投资、出资、建设星门园区。拒绝参与星门也算（针对该线程的立场）。 |
| anthropic_ipo | Anthropic 上市线程：S-1 递交、定价、上市、募资到账。只认 ANTH（其他公司的上市不算）。 |
| msft_invest | 微软对 OpenAI 的投资：100 亿美元、追加投资、循环图最大投资方。只认 MSFT/OAI。 |
| blackwell | B200/B300/Blackwell/GB200 芯片线程：发布、采购、上架。 |
| r1 | DeepSeek R1 线程：R1 发布、R1 落地。S4 1-1 轮含 DeepSeek 也算。 |
| musk_table | 马斯克个人动作：公开表态、推特、谈判桌动作。只认 MUSK。 |
| colossus | Colossus 集群建设/扩建：集群规模、装机、扩建计划。模型在 Colossus 上训练不算（那是模型发布）。 |
| spacex_xai | xAI/Grok/SpaceX 产品线程：Grok 发布、xAI 组建、SpaceX 相关产品动作。Grok 4 发布算 spacex_xai，不算 colossus。 |
| doubao_price_war | 豆包价格战：价格战、降价。只认价格动作，不认产品发布。 |
| bis_rule | BIS 远程规则线程：BIS、出口管制、远程规则。规则发布、规则收紧、规则执行。 |
| chatgpt | ChatGPT/GPT 产品线：GPT-4、GPT-4o、ChatGPT 接入。 |
| v3 | DeepSeek V3 线程：V3 发布。 |
| overseas_rental | 海外算力租赁：海外算力租赁需求、抢租海外算力。 |
| huang_resign | 黄仁勋辞职：辞职本身。 |
| sec_probe | SEC 调查：SEC 调查报道。 |
| tongyi | 通义产品线：通义发布、通义更新。只认 ALI。 |
| hunyuan | 混元产品线：混元发布、混元更新；TCE 微信入口也算。只认 TCE。 |
| ascend | 昇腾芯片线：昇腾发布、量产、出货。只认 HUAWEI。模型在昇腾上落地不算（那是模型种类）。 |
| doubao | 豆包产品线：豆包发布、豆包更新（非价格战部分）。只认 BYTE。 |
| wenxin | 文心产品线：文心发布、文心更新、文心开源。文心 4.5 开源算 wenxin，不算 open_source。只认 BIDU。 |
| pangu | 盘古模型线：盘古发布、盘古开源。盘古 5.5 算 pangu，不算 ascend。只认 HUAWEI。 |
| llama | Llama 线：Llama 发布、Llama 开源、Llama 上架。豆包拿 Llama 路线做内部版算 doubao（主语是豆包）。 |
| claude | Claude 产品线：Claude 发布、Claude 更新。只认 ANTH。 |
| gemini | Gemini 产品线：Gemini 发布、Gemini 更新；Bard（前身）也算。只认 GOOG。 |
| megaspeed | Megaspeed 线：Megaspeed 走私、调查、牵连。 |
| energy | 能源/电力线程：核电合同、电力采购、绿电、燃气电厂、供电方案。必须是具体的能源动作（合同、采购、签约），带可查的公开来源。状态描述（“能源团队老练”“并网排队中”）不算公开事件。 |
| financing | 融资/债务/借钱线程：融资、发债、借钱。必须是具体的融资动作（宣布、完成、挂单），带可查的公开来源。状态描述（“融资窗口观察中”）不算公开事件。 |
| capex | 资本开支线程：资本开支宣布、上调、被质问。必须是财报或公告里的具体数字，带可查的公开来源。等待状态（“等资本开支指引”）不算公开事件。 |
| open_source | 开源策略线程：开源发布、开源托管。只收产品名未命中的剩余开源动作。具名产品开源归产品种类。“不开源”不算。 |
| datacenter | 数据中心园区线程：园区计划、园区建设。必须是具体的园区动作（宣布、签约、交付），带可查的公开来源。叙事判断（“被迫评估更大园区计划”“不建园区。轻资产到底”“无园区负担”）不算公开事件。 |
| compliance | 合规自查线程：自查动作。自查本来就是低调的内部动作，没有公开宣布。原则上不算公开事件，除非有公开来源（监管公告、公司公告）写明自查。 |
| invest_plan | 宣布投资计划线程：宣布投入、投资计划。必须是公开宣布的计划（公告、发布会），带金额或规模，带可查的公开来源。 |
| generic | 不用。真实 trace 不用兜底种类。 |
| openai_mar26 | OpenAI 2026 年 3 月 1220 亿美元轮。目前无实例。 |

## 三处已知边界（已定）
- Grok 4 发布 = spacex_xai，不是 colossus。模型发布是产品种类；集群建设才是 colossus。证据：前瞻指引实验 S4 4-1 MUSK，正确答案是 spacex_xai。
- 文心 4.5 开源 = wenxin，不是 open_source。具名产品开源归产品种类。
- 盘古 5.5 = pangu，不是 ascend。模型发布是模型种类；芯片才是 ascend。证据：前瞻指引实验 S4 4-1 HUAWEI，正确答案是 pangu。
