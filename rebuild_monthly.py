#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""金铲铲复盘：按月重组 + 前传赛季 S0（2018-06 ~ 2022-12）重建脚本。
输入： ts-spaces/.../assets/data.json（单一事实源，751 条）
      verification/gpt1-to-2022-events.json（106 条，2018-06 ~ 2022-12）
输出： 同一 data.json（新结构）+ verification/rebuild_monthly_report.json（核对报告）
规则：
- S0：单赛季，55 个月，每月一轮；开局 100 血 / 0 金；Δ 采用压缩计分
  （时代级 +4~+6，重要 +2~+3，常规 +0~+1，挫折 -1~-3；金币只加不减），
  使 55 个月累加后血量仍在 [0,140]、金币 >= 0（页内检查器 V3/V6 的量程）。
- S1~S5：动作按月重组，不改任何 Δ 数值；只拆分/合并轮次。
- 2026-11：S5 11 月轮（117 条）与 S6 1-1（Pachocki、黄仁勋复任、Megaspeed，3 条）分属两季，
  因 S5 季末 / S6 开局必须与现有值一致（OAI 79/58、ANTH 121/113、NVDA 36/54），
  Pachocki 动作（OAI +3/+1）若并入 S5 将使 S5 季末 OAI 变为 82/59。
  故 11 月保留两轮（同月、不同季），Pachocki 不重复。
注意：本脚本为一次性迁移脚本，2026-11-23 已跑。当前 data.json 的轮次代码已是按月代码，
重跑本脚本会在 ROUTES 处失败；原始 643 条输入未进仓库，无从重跑。
"""
import json, re, copy, collections

WS = '/home/hatch/workspace/'
SRC = WS + 'ts-spaces/jin-chan-chan-fu-pan-ai-da-ting-2022-2026/assets/data.json'
EVF = WS + 'verification/gpt1-to-2022-events.json'
OUT = SRC
REPORT = WS + 'verification/rebuild_monthly_report.json'

d = json.load(open(SRC))
ev = json.load(open(EVF))['events']
assert len(ev) == 106, len(ev)

# ---------------------------------------------------------------- 新玩家（8 名）
# 决策：8 个新代码全部加为玩家。HF/STAB/MJ/AI21 是公司；UCB 是学术机构
# （MMLU 基准）；EU/USGOV/ACM 是机构/规则制定方，无相关玩家可归并，
# 归并即编造归属，故单独立席。单事件玩家已有先例（PANW/OPENCLAW 各 1 条）。
NEW_PLAYERS = [
    {"id": "HF", "code": "HF", "name": "Hugging Face", "color": "#f59e0b", "sym": "HF",
     "role": "开源枢纽 · 模型超市", "style": "不造最大模型。造所有人分发模型的地方。",
     "open": "Transformers 库 + 模型 hub", "weak": "自己没有旗舰模型。靠生态抽成",
     "bond": "开源羁绊：全桌受益"},
    {"id": "STAB", "code": "STAB", "name": "Stability AI", "color": "#db2777", "sym": "ST",
     "role": "开源图像 · 颠覆位", "style": "把最贵的图像模型免费发出去。拆所有人的城墙。",
     "open": "Stable Diffusion 开源", "weak": "没有收入。烧钱换声量",
     "bond": "开源羁绊：与 Meta、Hugging Face 同触发"},
    {"id": "MJ", "code": "MJ", "name": "Midjourney", "color": "#0ea5e9", "sym": "MJ",
     "role": "图像新锐 · 社区位", "style": "不融资。不打广告。靠社区口碑长大。",
     "open": "Discord 社区 + 图像审美", "weak": "没有自己的云与资本",
     "bond": "开源图像羁绊"},
    {"id": "AI21", "code": "AI21", "name": "AI21 Labs", "color": "#16a34a", "sym": "A2",
     "role": "大模型新军 · 以色列位", "style": "小实验室。大参数。先发再说。",
     "open": "Jurassic-1 大模型", "weak": "声量小。融资轮次少",
     "bond": "无"},
    {"id": "UCB", "code": "UCB", "name": "加州大学伯克利分校", "color": "#65a30d", "sym": "UC",
     "role": "学术界 · 基准制定者", "style": "不下场打产品。制定量人的尺子。",
     "open": "MMLU 基准 + 学术声誉", "weak": "没有产品。没有收入",
     "bond": "学术羁绊"},
    {"id": "EU", "code": "EU", "name": "欧盟", "color": "#1e40af", "sym": "EU",
     "role": "规则制定方 · 布鲁塞尔", "style": "不造模型。造所有人必须遵守的规则。",
     "open": "AI 法案 + 200 亿欧元协调计划", "weak": "没有自己的旗舰实验室",
     "bond": "规则桌羁绊：规则落回一层即新版本"},
    {"id": "USGOV", "code": "USGOV", "name": "美国政府", "color": "#b91c1c", "sym": "US",
     "role": "规则制定方 · 华盛顿", "style": "不造模型。用行政令与法案定方向。",
     "open": "美国 AI 倡议 + 国家 AI 倡议法案", "weak": "换届即可能改向",
     "bond": "规则桌羁绊：规则落回一层即新版本"},
    {"id": "ACM", "code": "ACM", "name": "美国计算机学会", "color": "#6b7280", "sym": "AC",
     "role": "学术荣誉 · 图灵奖", "style": "不下场。给历史定调。",
     "open": "图灵奖", "weak": "一年只发一次",
     "bond": "学术羁绊"},
]
# 新玩家在 players 列表中的位置：接在现有 24 名之后（保持既有顺序不动）
# S0 meta（赛季末人口/标签，模型输入，与各季 meta 同性质）
S0_META = [
    {"id": "GOOG", "pop": 7, "label": "搜索城池"},
    {"id": "OAI", "pop": 4, "label": "先手成型"},
    {"id": "NVDA", "pop": 5, "label": "装备商"},
    {"id": "META", "pop": 6, "label": "社交城池"},
    {"id": "MSFT", "pop": 6, "label": "云厂就位"},
    {"id": "ANTH", "pop": 2, "label": "安全小队"},
    {"id": "HUAWEI", "pop": 4, "label": "昇腾出货"},
    {"id": "HF", "pop": 3, "label": "开源枢纽"},
    {"id": "STAB", "pop": 2, "label": "开源图像"},
    {"id": "MJ", "pop": 2, "label": "图像新锐"},
    {"id": "AI21", "pop": 2, "label": "大模型新军"},
    {"id": "UCB", "pop": 2, "label": "学术基准"},
    {"id": "EU", "pop": 3, "label": "规则制定"},
    {"id": "USGOV", "pop": 3, "label": "政策制定"},
    {"id": "ACM", "pop": 1, "label": "学术荣誉"},
]

# ---------------------------------------------------------------- S0 Δ（按 日期+玩家 匹配，避免下标错位）
# 计分：时代级 +4~+6 / 重要 +2~+3 / 常规 +0~+1 / 挫折 -1~-3；金币 0~+3，只加不减。
S0_DELTA_LIST = [
    ("2018-06", "OAI", 1, 1),     # Five 首胜 Dota 2 业余队
    ("2018-06-11", "OAI", 5, 2),  # GPT-1
    ("2018-07-19", "OAI", 0, 0),  # Five 宣布 8 月对阵前职业队
    ("2018-08-13", "NVDA", 2, 1), # Turing 架构
    ("2018-09-28", "GOOG", 1, 0), # BigGAN
    ("2018-10-11", "GOOG", 5, 2), # BERT
    ("2018-11-02", "GOOG", 1, 1), # 开源 BERT
    ("2018-12", "GOOG", 2, 1),    # AlphaFold CASP13
    ("2018-12-07", "EU", 1, 1),   # 欧盟 AI 协调计划
    ("2018-12-12", "NVDA", 1, 0), # StyleGAN
    ("2019-01-24", "GOOG", 1, 1), # AlphaStar 首胜星际 2 职业选手
    ("2019-02-11", "USGOV", 1, 1),# 美国 AI 倡议行政令
    ("2019-02-14", "OAI", 3, 1),  # GPT-2 124M
    ("2019-03-11", "OAI", 1, 1),  # OpenAI 改制上限利润公司
    ("2019-03-27", "ACM", 0, 0),  # 图灵奖三先驱
    ("2019-04-04", "GOOG", -2, 0),# 谷歌解散 ATEAC
    ("2019-04-08", "EU", 1, 1),   # 欧盟可信 AI 伦理指南
    ("2019-05", "OAI", 0, 0),     # GPT-2 355M
    ("2019-06-19", "GOOG", 1, 0), # XLNet
    ("2019-07-22", "MSFT", 2, 2), # 微软投 OpenAI 10 亿美元
    ("2019-07-26", "META", 1, 0), # RoBERTa
    ("2019-08-20", "OAI", 0, 0),  # GPT-2 774M
    ("2019-09-17", "NVDA", 1, 0), # Megatron-LM
    ("2019-09-26", "GOOG", 0, 0), # ALBERT
    ("2019-10-02", "HF", 1, 1),   # DistilBERT
    ("2019-10-23", "GOOG", 1, 1), # T5
    ("2019-10-25", "GOOG", 1, 1), # 谷歌搜索上线 BERT
    ("2019-10-30", "GOOG", 0, 0), # AlphaStar 宗师级
    ("2019-11-05", "OAI", 1, 1),  # GPT-2 1.5B
    ("2019-11-19", "GOOG", 1, 1), # MuZero
    ("2019-12-03", "NVDA", 1, 0), # StyleGAN2
    ("2020-01-23", "OAI", 1, 1),  # Scaling Laws
    ("2020-02", "GOOG", 0, 0),    # T5-11B
    ("2020-02-13", "MSFT", 1, 1), # Turing-NLG
    ("2020-03-05", "GOOG", 1, 0), # DeepMind 新冠蛋白结构预测
    ("2020-03-28", "HUAWEI", 1, 1),# MindSpore 开源
    ("2020-04-29", "META", 1, 0), # Blender 94 亿参数
    ("2020-05-14", "NVDA", 3, 2), # A100/Ampere
    ("2020-05-28", "OAI", 6, 2),  # GPT-3
    ("2020-06-11", "OAI", 1, 1),  # GPT-3 API 内测
    ("2020-06-30", "GOOG", 0, 0), # GShard
    ("2020-07-28", "GOOG", 0, 0), # ScaNN 开源
    ("2020-08-04", "GOOG", 0, 0), # AlphaFold 新冠预测更新
    ("2020-09-07", "UCB", 1, 1),  # MMLU
    ("2020-09-22", "MSFT", 2, 1), # 微软独家授权 GPT-3
    ("2020-10", "GOOG", 0, 0),    # mT5（与 ViT 同月，需用标题区分，见下）
    ("2020-10", "GOOG", 1, 0),    # ViT（同上）
    ("2020-11-30", "GOOG", 5, 2), # AlphaFold 2 CASP14
    ("2020-12-23", "GOOG", 1, 1), # MuZero 登 Nature
    ("2021-01-01", "USGOV", 1, 1),# 国家 AI 倡议法案生效
    ("2021-01-05", "OAI", 2, 1),  # DALL-E（与 CLIP 同日，需标题区分）
    ("2021-01-05", "OAI", 1, 1),  # CLIP（同上）
    ("2021-01-11", "GOOG", 1, 0), # Switch Transformer
    ("2021-01-26", "ANTH", 2, 1), # Anthropic 成立
    ("2021-02-19", "GOOG", -3, 0),# 谷歌解雇 Mitchell
    ("2021-03-04", "META", 1, 0), # SEER
    ("2021-04-21", "EU", 1, 1),   # 欧盟 AI 法案草案
    ("2021-05-18", "GOOG", 1, 1), # LaMDA
    ("2021-05-28", "ANTH", 1, 1), # Anthropic A 轮
    ("2021-06-29", "MSFT", 2, 1), # Copilot 技术预览
    ("2021-07-07", "OAI", 1, 1),  # Codex 论文
    ("2021-07-15", "GOOG", 1, 1), # AlphaFold 2 论文与数据库
    ("2021-07-16", "META", 0, 0), # BlenderBot 2.0
    ("2021-08-04", "AI21", 1, 1), # Jurassic-1
    ("2021-08-10", "OAI", 0, 0),  # Codex API 内测
    ("2021-09-03", "GOOG", 0, 0), # FLAN
    ("2021-10-11", "MSFT", 1, 1), # MT-NLG 530B
    ("2021-10-28", "META", 1, 1), # Facebook 更名 Meta
    ("2021-11-18", "OAI", 0, 0),  # 取消 GPT-3 API 等候名单
    ("2021-12-08", "GOOG", 1, 0), # Gopher
    ("2021-12-14", "OAI", 0, 0),  # 开放 GPT-3 微调
    ("2022-01-27", "OAI", 2, 1),  # InstructGPT
    ("2022-01-28", "GOOG", 1, 1), # 思维链提示论文
    ("2022-02-15", "ANTH", 1, 0), # Anthropic 可预测与意外论文
    ("2022-03-15", "OAI", 1, 1),  # GPT-3.5 系列
    ("2022-03-21", "GOOG", 0, 0), # GopherCite
    ("2022-03-22", "NVDA", 4, 2), # Hopper/H100
    ("2022-03-29", "GOOG", 2, 1), # Chinchilla
    ("2022-04", "ANTH", 2, 2),    # Anthropic B 轮 5.8 亿
    ("2022-04-04", "GOOG", 2, 2), # PaLM
    ("2022-04-06", "OAI", 2, 1),  # DALL-E 2
    ("2022-04-28", "GOOG", 1, 0), # Flamingo
    ("2022-05-03", "META", 2, 1), # OPT-175B
    ("2022-05-09", "HF", 1, 3),   # HF C 轮 1 亿美元
    ("2022-05-11", "GOOG", 0, 0), # LaMDA 2 与 AI Test Kitchen
    ("2022-05-12", "GOOG", 0, 0), # Gato
    ("2022-05-23", "GOOG", 1, 1), # Imagen
    ("2022-06-11", "GOOG", -2, 0),# Lemoine 称 LaMDA 有知觉
    ("2022-06-15", "GOOG", 1, 0), # 涌现能力论文
    ("2022-06-29", "GOOG", 0, 0), # Minerva
    ("2022-07-12", "HF", 2, 1),   # BLOOM（与 Midjourney 同日，需标题区分）
    ("2022-07-12", "MJ", 1, 1),   # Midjourney 公测
    ("2022-07-20", "OAI", 0, 0),  # DALL-E 2 百万人候补
    ("2022-08-22", "STAB", 3, 2), # Stable Diffusion 开源
    ("2022-09-21", "OAI", 1, 1),  # Whisper 开源
    ("2022-09-28", "GOOG", 0, 0), # Sparrow
    ("2022-10-04", "USGOV", 1, 1),# 白宫 AI 权利法案蓝图
    ("2022-10-05", "GOOG", 1, 0), # AlphaTensor 登 Nature
    ("2022-10-17", "STAB", 2, 2), # Stability AI 融资 1.01 亿
    ("2022-11-15", "META", 0, 0), # Galactica（发布三天后撤回，计 0）
    ("2022-11-24", "STAB", 1, 1), # Stable Diffusion 2.0
    ("2022-11-28", "OAI", 0, 0),  # text-davinci-003
    ("2022-11-30", "OAI", 6, 3),  # ChatGPT
    ("2022-12-06", "EU", 1, 1),   # 欧盟理事会 AI 法案总体立场
    ("2022-12-08", "OAI", 0, 0),  # Whisper large-v2
    ("2022-12-15", "ANTH", 2, 1), # 宪法 AI 论文
]
# 同（日期，玩家）出现两次的条目用标题关键词区分：
# 2020-10 GOOG：mT5(0,0) / ViT(1,0)；2021-01-05 OAI：DALL-E(2,1) / CLIP(1,1)；
# 2022-07-12：HF BLOOM(2,1) / MJ(1,1)（玩家不同，已区分）。
# 2020-10 与 2021-01-05 的同键条目按文件顺序配对。
def build_s0_delta():
    by_key = collections.defaultdict(list)
    for (dt, pl, dh, dg) in S0_DELTA_LIST:
        by_key[(dt, pl)].append((dh, dg))
    out = {}
    used = collections.Counter()
    for i, e in enumerate(ev):
        k = (e['date'], e['player'])
        lst = by_key.get(k)
        assert lst, f"无 Δ：{e}"
        n = used[k]
        assert n < len(lst), f"Δ 不足：{e}"
        out[i] = lst[n]
        used[k] += 1
    assert len(out) == 106, len(out)
    assert sum(used.values()) == 106
    return out
S0_DELTA = build_s0_delta()

# ---------------------------------------------------------------- S0 每月文案
# 标题 = 当月最具代表性事件的标题；headline 覆盖少数 max 规则不适用的月份。
HEADLINE_OVERRIDE = {
    "2019-04": 15, "2019-10": 25, "2019-11": 29, "2020-03": 34,
    "2021-07": 61, "2021-10": 67, "2022-04": 79, "2022-05": 82, "2022-06": 87,
}
# 每月 (global, verdict)。global 1~2 句；verdict 胜/负各一句。Δ 均为模型分，不证数字。
S0_TEXT = {
 "2018-06": ("GPT-1 发布。生成式预训练范式确立。同月 OpenAI Five 首胜 Dota 2 业余队。",
             "胜：OpenAI。GPT-1 立住生成式预训练范式。负：无。"),
 "2018-07": ("OpenAI Five 宣布 8 月对阵前职业队。Dota 2 的下一场硬仗约好了。",
             "胜：OpenAI。约战前职业队。负：无。"),
 "2018-08": ("英伟达发布 Turing 架构 GPU。光线追踪进显卡，AI 训练也有了新装备。",
             "胜：英伟达。Turing 架构上市。负：无。"),
 "2018-09": ("DeepMind 发布 BigGAN。大规模 GAN 训练，生成图像上了一个台阶。",
             "胜：谷歌。BigGAN 大规模生成。负：无。"),
 "2018-10": ("谷歌发布 BERT 论文。双向预训练，自然语言理解换了底座。",
             "胜：谷歌。BERT 双向预训练。负：无。"),
 "2018-11": ("谷歌开源 BERT 代码与预训练模型。所有人都能站在 BERT 肩上。",
             "胜：谷歌。BERT 开源。负：无。"),
 "2018-12": ("DeepMind AlphaFold 赢得 CASP13。蛋白质结构预测第一次被 AI 拿下。同月欧盟发布 AI 协调计划，投 200 亿欧元。英伟达发布 StyleGAN。",
             "胜：谷歌。AlphaFold 赢得 CASP13。负：无。"),
 "2019-01": ("DeepMind AlphaStar 首胜星际争霸 2 职业选手。实时战略游戏也被 AI 打穿。",
             "胜：谷歌。AlphaStar 首胜职业选手。负：无。"),
 "2019-02": ("GPT-2 发布，只放 124M 版防滥用。同月美国发布行政令，启动美国 AI 倡议。",
             "胜：OpenAI。GPT-2 发布。负：无。"),
 "2019-03": ("OpenAI 改制为上限利润公司。同月深度学习三先驱获 2018 图灵奖。",
             "胜：OpenAI。改制完成，融资通道打开。负：无。"),
 "2019-04": ("谷歌解散 AI 伦理委员会 ATEAC。成立一周即解散。同月欧盟发布可信 AI 伦理指南。",
             "胜：无。负：谷歌。伦理委员会一周解散。"),
 "2019-05": ("GPT-2 分阶段放出 355M 版。OpenAI 的分阶段发布走到第二步。",
             "胜：OpenAI。分阶段发布继续。负：无。"),
 "2019-06": ("谷歌与 CMU 发布 XLNet，超 BERT。预训练的排列组合又进一步。",
             "胜：谷歌。XLNet 超 BERT。负：无。"),
 "2019-07": ("微软向 OpenAI 投资 10 亿美元。同月 Facebook 发布 RoBERTa，优化 BERT 训练。",
             "胜：微软。10 亿美元锁死羁绊。负：无。"),
 "2019-08": ("GPT-2 放出 774M 版，并发布分阶段报告。分阶段发布走到第三步。",
             "胜：OpenAI。分阶段发布继续。负：无。"),
 "2019-09": ("英伟达发布 Megatron-LM，83 亿参数。同月谷歌发布 ALBERT，轻量版 BERT。",
             "胜：英伟达。Megatron-LM 83 亿参数。负：无。"),
 "2019-10": ("谷歌发布 T5，统一文本到文本框架。同月 Hugging Face 发布 DistilBERT，谷歌搜索上线 BERT，AlphaStar 达宗师级。",
             "胜：谷歌。T5 统一框架。负：无。"),
 "2019-11": ("DeepMind 发布 MuZero，无规则自学规划。同月 GPT-2 完整 15 亿参数版发布。",
             "胜：谷歌。MuZero 无规则自学。负：无。"),
 "2019-12": ("英伟达发布 StyleGAN2，画质再提升。生成人脸又真了一档。",
             "胜：英伟达。StyleGAN2 画质再升。负：无。"),
 "2020-01": ("Scaling Laws 论文发布，揭示规模定律。越大越好，第一次有了定量形状。",
             "胜：OpenAI。规模定律立住。负：无。"),
 "2020-02": ("微软发布 170 亿参数 Turing-NLG。同月谷歌发布 T5-11B 统一文本到文本模型。",
             "胜：微软。Turing-NLG 170 亿参数。负：无。"),
 "2020-03": ("DeepMind 发布新冠病毒蛋白结构预测。疫情当月，AI 直接上了抗疫前线。同月华为 MindSpore 框架正式开源。",
             "胜：谷歌。新冠蛋白结构预测。负：无。"),
 "2020-04": ("Facebook 开源 94 亿参数聊天机器人 Blender。对话模型开源到百亿级。",
             "胜：Meta。Blender 开源。负：无。"),
 "2020-05": ("GPT-3 论文发布，1750 亿参数少样本学习。同月英伟达发布 A100 与 Ampere 架构。",
             "胜：OpenAI。GPT-3 少样本学习。负：无。"),
 "2020-06": ("GPT-3 API 开启私人内测。同月谷歌发表 GShard 论文，6000 亿参数稀疏模型。",
             "胜：OpenAI。GPT-3 API 内测。负：无。"),
 "2020-07": ("谷歌开源向量检索库 ScaNN。检索基础设施免费可用。",
             "胜：谷歌。ScaNN 开源。负：无。"),
 "2020-08": ("DeepMind 更新新冠蛋白 AlphaFold 预测。疫情预测继续迭代。",
             "胜：谷歌。AlphaFold 预测更新。负：无。"),
 "2020-09": ("微软独家授权 GPT-3 模型。同月伯克利发布 MMLU 基准，57 学科多任务评测。",
             "胜：微软。独家授权 GPT-3。负：无。"),
 "2020-10": ("谷歌发布视觉 Transformer 论文 ViT。同月发布 101 语言多语言模型 mT5。",
             "胜：谷歌。ViT 把 Transformer 带进视觉。负：无。"),
 "2020-11": ("DeepMind AlphaFold 2 赢得 CASP14。蛋白质结构预测基本被解决。",
             "胜：谷歌。AlphaFold 2 赢得 CASP14。负：无。"),
 "2020-12": ("DeepMind MuZero 论文登 Nature，无规则学棋。规划能力不需要人类规则。",
             "胜：谷歌。MuZero 登 Nature。负：无。"),
 "2021-01": ("OpenAI 发布文生图模型 DALL-E 与图文对比模型 CLIP。同月美国国家 AI 倡议法案生效，谷歌发布 Switch Transformer，Anthropic 正式成立。",
             "胜：OpenAI。DALL-E 与 CLIP 同月发布。负：无。"),
 "2021-02": ("谷歌解雇 AI 伦理团队负责人 Mitchell。伦理团队连遭重创。",
             "胜：无。负：谷歌。解雇伦理团队负责人。"),
 "2021-03": ("Facebook 发布自监督视觉模型 SEER。视觉自监督上量。",
             "胜：Meta。SEER 自监督视觉。负：无。"),
 "2021-04": ("欧盟委员会公布人工智能法案草案。全球第一部全面 AI 立法进入程序。",
             "胜：欧盟。AI 法案草案公布。负：无。"),
 "2021-05": ("谷歌 I/O 发布对话模型 LaMDA。对话模型进入产品线。同月 Anthropic 完成 1.24 亿美元 A 轮融资。",
             "胜：谷歌。LaMDA 发布。负：无。"),
 "2021-06": ("GitHub Copilot 开启技术预览。AI 第一次坐进编辑器写代码。",
             "胜：微软。Copilot 技术预览。负：无。"),
 "2021-07": ("AlphaFold 2 论文与数据库在 Nature 发表。同月 OpenAI 发布 Codex 论文，Facebook 发布 BlenderBot 2.0。",
             "胜：谷歌。AlphaFold 2 论文与数据库发表。负：无。"),
 "2021-08": ("AI21 发布 1780 亿参数 Jurassic-1。同月 OpenAI Codex API 开启私人内测。",
             "胜：AI21。Jurassic-1 发布。负：无。"),
 "2021-09": ("谷歌发表 FLAN 论文，指令微调提升零样本能力。对齐路线的早期一步。",
             "胜：谷歌。FLAN 指令微调。负：无。"),
 "2021-10": ("Facebook 公司更名为 Meta。同月微软与英伟达发布 5300 亿参数 MT-NLG。",
             "胜：Meta。公司更名，元宇宙 All in。负：无。"),
 "2021-11": ("OpenAI 取消 GPT-3 API 等候名单。GPT-3 正式向所有人开放。",
             "胜：OpenAI。GPT-3 API 全面开放。负：无。"),
 "2021-12": ("谷歌 DeepMind 发布 2800 亿参数语言模型 Gopher。同月 OpenAI 开放 GPT-3 微调功能。",
             "胜：谷歌。Gopher 发布。负：无。"),
 "2022-01": ("OpenAI 发布 InstructGPT，RLHF 规模化。同月谷歌发表思维链提示论文。",
             "胜：OpenAI。InstructGPT，RLHF 规模化。负：无。"),
 "2022-02": ("Anthropic 发表大模型可预测与意外论文。安全派的早期方法论。",
             "胜：Anthropic。大模型可预测性论文。负：无。"),
 "2022-03": ("英伟达发布 Hopper 架构与 H100。同月 OpenAI 上线 GPT-3.5 系列，DeepMind 发表 Chinchilla 缩放定律，发布 GopherCite。",
             "胜：英伟达。Hopper 与 H100 发布。负：无。"),
 "2022-04": ("谷歌发布 5400 亿参数 PaLM。同月 Anthropic 完成 5.8 亿美元 B 轮，OpenAI 发布 DALL-E 2，DeepMind 发布 Flamingo。",
             "胜：谷歌。PaLM 5400 亿参数。负：无。"),
 "2022-05": ("Meta 发布 OPT-175B 开放模型。同月 Hugging Face 完成 1 亿美元 C 轮，谷歌发布 LaMDA 2、Gato 与 Imagen。",
             "胜：Meta。OPT-175B 开放。负：无。"),
 "2022-06": ("谷歌工程师称 LaMDA 有知觉，引争议。同月谷歌等发表大模型涌现能力论文，发布数学推理模型 Minerva。",
             "胜：无。负：谷歌。LaMDA 知觉争议。"),
 "2022-07": ("BigScience 发布 1760 亿参数 BLOOM。同月 Midjourney 开放公测，DALL-E 2 进入百万人候补测试。",
             "胜：Hugging Face。BLOOM 发布。负：无。"),
 "2022-08": ("开源发布 Stable Diffusion 模型。文生图门槛一夜归零。",
             "胜：Stability AI。Stable Diffusion 开源。负：无。"),
 "2022-09": ("OpenAI 开源语音识别模型 Whisper。同月 DeepMind 发布对话智能体 Sparrow。",
             "胜：OpenAI。Whisper 开源。负：无。"),
 "2022-10": ("Stability AI 融资 1.01 亿美元，估值 10 亿。同月白宫发布 AI 权利法案蓝图，DeepMind AlphaTensor 登 Nature。",
             "胜：Stability AI。融资 1.01 亿，估值 10 亿。负：无。"),
 "2022-11": ("OpenAI 发布 ChatGPT。同月 Meta 发布 Galactica（三天后撤回），Stability 发布 Stable Diffusion 2.0，OpenAI 发布 text-davinci-003。",
             "胜：OpenAI。ChatGPT 发布。负：Meta。Galactica 三天撤回。"),
 "2022-12": ("Anthropic 发表宪法 AI 论文。同月欧盟理事会通过 AI 法案总体立场，OpenAI 发布 Whisper large-v2。",
             "胜：Anthropic。宪法 AI 论文。负：无。"),
}
print('S0_TEXT months:', len(S0_TEXT))

# ---------------------------------------------------------------- S1~S5 按月重组
# 路由：(旧季, 旧轮) -> 新轮次列表，每项 (新轮 code, [旧动作下标] 或 'ALL')
# 新轮次文案：1:1 轮继承旧文案（日期改为月份）；合并/拆分轮用 NEW_TEXT。
OLD = {s['id']: {r['code']: r for r in s['rounds']} for s in d['seasons']}
def moves_of(sid, code, idxs):
    r = OLD[sid][code]
    if idxs == 'ALL':
        return [list(m) for m in r['moves']]
    return [list(r['moves'][i]) for i in idxs]

def month_date(y, m):
    return f"{y} 年 {m} 月"

# (季, 新轮) -> (标题, 类型, global, verdict)；缺省则继承首个来源轮的文案
NEW_TEXT = {
 ("S1", "2022-12"): ("连胜扩大：全桌开始转阵容", "连胜轮",
   "ChatGPT 的连胜扩大，全桌开始转阵容。微软备好大额选秀金，100 亿美元投资落袋前夜。",
   "胜：OpenAI。ChatGPT 连胜扩大。负：Meta。元宇宙亏损拖累全季结算。"),
 ("S2", "2023-06"): ("苹果发布 Vision Pro：与 AI 无关", "事件",
   "苹果在 6 月 5 日 WWDC 发布 Vision Pro 头显。空间计算入场。AI 大厅的当轮争夺与它无关。",
   "胜：无。负：无。Vision Pro 发布与 AI 争夺无关，苹果本轮只记一笔小额动作。"),
 ("S3", "2024-02"): ("Qwen1.5 发布：开源节奏不停", "事件",
   "阿里发布 Qwen1.5。72B 版本上线。开源节奏不停。",
   "胜：阿里。开源节奏不停。负：无。"),
 ("S4", "2025-01"): ("DeepSeek R1 发布：效率阵容打出三星效果", "对战",
   "1 月 20 日 DeepSeek R1 发布。1 月 21 日星门计划 5000 亿美元宣布。1 月 27 日英伟达单日跌约 17%，血崩日。",
   "胜：DeepSeek。效率阵容打出三星效果。负：英伟达。单日跌约 17%，全桌最重的一刀。"),
 ("S4", "2025-06"): ("文心 4.5 开源：百度跟进开源潮", "事件",
   "百度在 6 月 30 日开源文心 4.5。跟进开源潮。",
   "胜：百度。开源跟进。负：无。"),
 ("S4", "2025-09"): ("Claude Sonnet 4.5 发布：编程新标杆", "事件",
   "9 月 29 日 Anthropic 发布 Claude Sonnet 4.5。SWE-bench 领先。9 月 30 日 OpenAI 发布 Sora 2。视频真实感再升。",
   "胜：Anthropic。Sonnet 4.5 成编程新标杆。负：无。"),
 ("S4", "2025-10"): ("ChatGPT Atlas 发布：浏览器 Agent 入场", "事件",
   "10 月 15 日 Anthropic 发布 Claude Haiku 4.5。10 月 21 日 OpenAI 发布 ChatGPT Atlas。浏览器 Agent 入场。10 月 27 日 MiniMax 发布 M2。开源 Agent 模型跟进。",
   "胜：OpenAI。Atlas 把 Agent 放进浏览器。负：无。"),
 ("S4", "2025-11"): ("Gemini 3 发布：十一月模型大战", "事件",
   "11 月 4 日字节 TRAE SOLO 正式上线。11 月 6 日 Kimi 发布 K2 Thinking。11 月 12 日 OpenAI 推出 GPT-5.1。11 月 18 日谷歌发布 Gemini 3 Pro 与 Antigravity。11 月 24 日 Anthropic 发布 Claude Opus 4.5。三家旗舰同月换代。",
   "胜：谷歌。Gemini 3 夺回旗舰声量。负：无。十一月三家同换代，无人掉队。"),
 ("S5", "2026-01"): ("Claude Cowork 研究预览上线：Agent 进文件夹", "事件",
   "1 月 12 日 Anthropic 上线 Claude Cowork 研究预览。Agent 进文件夹。1 月 27 日月之暗面发布 Kimi K2.5。Agent 再进一步。",
   "胜：Anthropic。Cowork 把 Agent 放进文件夹。负：无。"),
 ("S5", "2026-02"): ("五角大楼传召 Amodei：拒绝移除护栏", "事件",
   "2 月五角大楼传召 Amodei。威胁断供与国防生产法。Anthropic 拒绝移除护栏，被列为供应链风险。同月 Claude Opus 4.6 与 Sonnet 4.6 发布，Gemini 3.1 Pro 上线。",
   "胜：无。负：Anthropic。传召与断供威胁同月，护栏之争公开化。"),
 ("S5", "2026-03"): ("腾讯 WorkBuddy 公开上线：办公 Agent", "事件",
   "3 月 9 日腾讯 WorkBuddy 公开上线。办公 Agent 入场。",
   "胜：腾讯。办公 Agent 上线。负：无。"),
 ("S5", "2026-04"): ("Claude Opus 4.7 发布：旗舰迭代", "事件",
   "4 月 8 日 Meta 发布 Muse Spark。4 月 16 日 Anthropic 发布 Claude Opus 4.7。4 月 24 日 DeepSeek 发布 V4 预览。",
   "胜：Anthropic。Opus 4.7 旗舰迭代。负：无。"),
 ("S5", "2026-05"): ("Claude Opus 4.8 发布：旗舰迭代", "事件",
   "5 月 27 日彭博报道字节在考虑最高 700 亿美元 2026 年资本开支。5 月 28 日 Anthropic 发布 Claude Opus 4.8。同月 xAI Grok Build 早期 beta 上线。",
   "胜：Anthropic。Opus 4.8 旗舰迭代。负：字节。资本开支计划高增。"),
 ("S5", "2026-06"): ("Claude Fable 5 发布：长篇写作模型", "事件",
   "6 月 9 日 Anthropic 发布 Claude Fable 5。长篇写作模型。",
   "胜：Anthropic。Fable 5 长篇写作。负：无。"),
 ("S5", "2026-07"): ("Claude Opus 5 发布：新一代旗舰", "事件",
   "7 月 16 日月之暗面发布 Kimi K3。7 月 23 日腾讯发布 CodeBuddy NPC。7 月 24 日 Anthropic 发布 Claude Opus 5。新一代旗舰。",
   "胜：Anthropic。Opus 5 新一代旗舰。负：无。"),
 ("S5", "2026-08"): ("DeepSeek V4-Pro GA：旗舰正式版", "事件",
   "8 月 11 日 xAI Grok Bot 早期 beta 上线。8 月 13 日 DeepSeek 发布 V4-Pro GA。8 月 26 日阿里发布 Qwen3.8-Flash-Next。8 月 31 日 OpenClaw 2.0 发布。",
   "胜：DeepSeek。V4-Pro 旗舰正式版。负：无。"),
 ("S5", "2026-09"): ("软银 118.7 亿美元贷款落地：为 OpenAI 投资融资", "事件",
   "9 月 10 日 DeepSeek 发布 V4.1 Flash。9 月 14 日软银落实 118.7 亿美元两年期定期贷款，以 OpenAI 持股作抵押。9 月 18 日阿里发布 Qwen3.8-Omni-Flash。",
   "胜：软银。贷款落地，OpenAI 投资融资有着落。负：无。"),
 ("S5", "2026-11"): ("选秀大轮：Anthropic 上市，BIS 新规同日生效", "事件",
   "11 月 5 日 BIS 远程接入规则公布。11 月 10 日 Anthropic 招股文件列明约 9009 亿美元算力承诺。11 月 12 日黄仁勋辞职，英伟达开盘跌约 13%。11 月 18–19 日 Anthropic 上市，BIS 新规同日生效。11 月 20 日 SEC 会计调查曝光，单日跌 14.01%。11 月 21 日结算继续。",
   "胜：Anthropic。上市募资到手，血量全桌第一。负：英伟达。辞职、调查、规则三张牌同月打出，血量垫底。"),
}
# (季, 新轮) -> [(旧季, 旧轮, [下标] 或 'ALL')]，按拼接顺序
ROUTES = {
 "S1": [
   ("2022-01", [("S1", "1-1", 'ALL')]),
   ("2022-08", [("S1", "1-4", 'ALL')]),
   ("2022-11", [("S1", "2-1", 'ALL')]),
   ("2022-12", [("S1", "2-5", 'ALL'), ("S1", "3-2", 'ALL')]),
 ],
 "S2": [
   ("2023-01", [("S2", "1-1", 'ALL')]),
   ("2023-03", [("S2", "2-1", 'ALL')]),
   ("2023-05", [("S2", "2-6", list(range(0, 14)) + [15, 16, 17])]),
   ("2023-06", [("S2", "2-6", [14])]),
   ("2023-07", [("S2", "3-2", 'ALL')]),
   ("2023-09", [("S2", "4-1", 'ALL')]),
   ("2023-11", [("S2", "4-5", 'ALL')]),
   ("2023-12", [("S2", "5-1", 'ALL')]),
 ],
 "S3": [
   ("2024-01", [("S3", "1-1", list(range(0, 18)))]),
   ("2024-02", [("S3", "1-1", [18])]),
   ("2024-03", [("S3", "2-1", 'ALL')]),
   ("2024-05", [("S3", "3-2", 'ALL')]),
   ("2024-07", [("S3", "4-1", 'ALL')]),
   ("2024-09", [("S3", "5-1", 'ALL')]),
   ("2024-12", [("S3", "6-1", 'ALL')]),
 ],
 "S4": [
   ("2025-01", [("S4", "1-1", 'ALL'), ("S4", "1-2", 'ALL'), ("S4", "1-3", 'ALL')]),
   ("2025-06", [("S4", "3-2", [18])]),
   ("2025-07", [("S4", "3-2", list(range(0, 18)) + [19, 20, 21]), ("S4", "4-1", [15])]),
   ("2025-08", [("S4", "4-1", list(range(0, 15)) + [16, 17, 18, 19, 20])]),
   ("2025-09", [("S4", "4-1", [21, 22])]),
   ("2025-10", [("S4", "4-1", [23, 24, 25])]),
   ("2025-11", [("S4", "4-1", [26, 27, 28, 29, 30, 31])]),
   ("2025-12", [("S4", "5-1", 'ALL')]),
 ],
 "S5": [
   ("2026-01", [("S5", "1-1", [18, 19])]),
   ("2026-02", [("S5", "1-1", [20, 21, 22, 39, 40])]),
   ("2026-03", [("S5", "1-1", [23])]),
   ("2026-04", [("S5", "1-1", [24, 25, 26])]),
   ("2026-05", [("S5", "1-1", [27, 8, 28])]),
   ("2026-06", [("S5", "1-1", [29])]),
   ("2026-07", [("S5", "1-1", [30, 31, 32])]),
   ("2026-08", [("S5", "1-1", [33, 34, 35, 36])]),
   ("2026-09", [("S5", "1-1", [37, 17, 38])]),
   ("2026-10", [("S5", "2-1", 'ALL')]),
   ("2026-11", [("S5", "1-1", list(range(0, 8)) + list(range(12, 17)) + [9, 10, 11]),
                ("S5", "3-2", 'ALL'), ("S5", "4-1", 'ALL'), ("S5", "5-1", 'ALL'),
                ("S5", "6-1", 'ALL'), ("S5", "6-2", 'ALL')]),
 ],
}
# S4 2025-07 的 global 追加一句（星门大单）
S4_JUL_GLOBAL_EXTRA = "同月 OpenAI 确认与甲骨文的星门大单（300 亿美元/年，4.5GW）。"
print('routes defined')

# ---------------------------------------------------------------- 构建 S0 赛季
def extract_url(src):
    m = re.search(r'https?://[^\s"\)\]]+', src or '')
    if not m:
        return None
    u = m.group(0).rstrip('.,)')
    return 'https://' + u[len('http://'):] if u.startswith('http://') else u

months = sorted({e['date'][:7] for e in ev})
assert len(months) == 55, months
by_month = collections.defaultdict(list)
for i, e in enumerate(ev):
    by_month[e['date'][:7]].append(i)

s0_rounds = []
s0_evidence = {}
s0_rv = {}
s0_end = {}
for m in months:
    idxs = by_month[m]
    y, mm = m.split('-')
    # 标题事件：覆盖优先，否则 Δ 最大（dh+dg，文件顺序破平）
    if m in HEADLINE_OVERRIDE:
        h = HEADLINE_OVERRIDE[m]
    else:
        h = max(idxs, key=lambda i: (S0_DELTA[i][0] + S0_DELTA[i][1], -i))
    he = ev[h]
    title = he['title']
    g, v = S0_TEXT[m]
    mv = [[ev[i]['player'], ev[i]['title'], S0_DELTA[i][0], S0_DELTA[i][1]] for i in idxs]
    code = m
    s0_rounds.append({"code": code, "date": month_date(int(y), int(mm)), "type": "事件",
                      "title": title, "global": g, "verdict": v, "moves": mv})
    url = extract_url(he.get('source', ''))
    month_only = len(he['date']) == 7
    note = "前传赛季月轮；Δ 均为模型分；来源见本轮事件。" + (
        "标题事件仅核实到月，未编造具体日。" if month_only else "")
    s0_evidence[f"S0:{code}"] = {
        "status": "verified" if url else "opinion",
        "items": [{"kind": "url", "ref": url, "label": title}] if url else [],
        "moves": {}, "note": note}
    s0_rv[f"S0:{code}"] = f"RV-{y}.1"
    # S0 季末累计（用于校验与报告）
    for (pl, _t, dh, dg) in mv:
        hp, gd = s0_end.get(pl, (100, 0))
        s0_end[pl] = (hp + dh, gd + dg)

# S0 前缀范围校验（页面约束：血量 0~140，金币 >= 0）
S0_PLAYERS = [m['id'] for m in S0_META]
cur = {p: [100, 0] for p in S0_PLAYERS}
s0_prefix_min, s0_prefix_max, s0_gold_min = 100, 100, 0
for r in s0_rounds:
    for (pl, _t, dh, dg) in r['moves']:
        cur[pl][0] += dh; cur[pl][1] += dg
    s0_prefix_min = min(s0_prefix_min, min(v[0] for v in cur.values()))
    s0_prefix_max = max(s0_prefix_max, max(v[0] for v in cur.values()))
    s0_gold_min = min(s0_gold_min, min(v[1] for v in cur.values()))
assert s0_prefix_min >= 0 and s0_prefix_max <= 140 and s0_gold_min >= 0, (
    s0_prefix_min, s0_prefix_max, s0_gold_min)
print('S0 rounds:', len(s0_rounds), 'S0 end:', dict(sorted(s0_end.items(), key=lambda kv: -kv[1][0])))

S0_SEASON = {
    "id": "S0", "year": "2018–2022", "title": "前传赛季",
    "patch": ["版本改动：生成式 AI 解锁。GPT-1 到 ChatGPT，论文先行，产品后至。",
              "旧阵容退环境：规则未成型。出口管制与 AI 立法都在起草中。",
              "关键规则：先手在论文里。BERT、GPT-3、AlphaFold 2 先定义版本，产品随后跟进。"],
    "start": "2018 年 6 月", "end": "2022 年 12 月",
    "theme": "GPT-1 到 ChatGPT。生成式 AI 从论文走向产品。先手在论文里，不在产品里。",
    "meta": S0_META,
    "rounds": s0_rounds,
}

# ---------------------------------------------------------------- 重组 S1~S5，S6 不变
# 旧动作 -> 新动作 的索引映射：(旧季, 旧轮, 旧下标) -> (新季, 新轮, 新下标)
MOVE_MAP = {}
new_seasons = []
SEASON_META = {"S1": ("2022 年 1 月", "2022 年 12 月"), "S2": ("2023 年 1 月", "2023 年 12 月"),
               "S3": ("2024 年 1 月", "2024 年 12 月"), "S4": ("2025 年 1 月", "2025 年 12 月"),
               "S5": ("2026 年 1 月", "2026 年 11 月")}
for s in d['seasons']:
    sid = s['id']
    if sid == 'S6':
        new_seasons.append(copy.deepcopy(s))
        continue
    if sid == 'S0':
        continue
    rounds = []
    for (code, srcs) in ROUTES[sid]:
        y, m = code.split('-')
        mv = []
        for (osid, ocode, idxs) in srcs:
            old = OLD[osid][ocode]
            ii = range(len(old['moves'])) if idxs == 'ALL' else idxs
            for i in ii:
                MOVE_MAP[(osid, ocode, i)] = (sid, code, len(mv))
                mv.append(list(old['moves'][i]))
        # 文案：NEW_TEXT 优先；否则继承首个来源轮
        if (sid, code) in NEW_TEXT:
            title, typ, g, v = NEW_TEXT[(sid, code)]
        else:
            first = OLD[srcs[0][0]][srcs[0][1]]
            title, typ, g, v = first['title'], first['type'], first['global'], first['verdict']
        if (sid, code) == ("S4", "2025-07"):
            g = g + S4_JUL_GLOBAL_EXTRA
        rounds.append({"code": code, "date": month_date(int(y), int(m)), "type": typ,
                       "title": title, "global": g, "verdict": v, "moves": mv})
    ns = copy.deepcopy(s)
    ns['rounds'] = rounds
    ns['start'], ns['end'] = SEASON_META[sid]
    new_seasons.append(ns)
new_seasons.insert(0, S0_SEASON)

# 校验：S1~S5 每季每玩家 Δ 总和不变
old_sums = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
for s in d['seasons']:
    for r in s['rounds']:
        for (pl, _t, dh, dg) in r['moves']:
            old_sums[s['id']][pl][0] += dh; old_sums[s['id']][pl][1] += dg
new_sums = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
for s in new_seasons:
    for r in s['rounds']:
        for (pl, _t, dh, dg) in r['moves']:
            new_sums[s['id']][pl][0] += dh; new_sums[s['id']][pl][1] += dg
for sid in ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']:
    assert dict(old_sums[sid]) == dict(new_sums[sid]), sid
print('season sums preserved S1-S6 OK')

# ---------------------------------------------------------------- 证据与 RV 重映射
new_evidence = {}
new_rv = {}
# 旧证据按旧轮聚合到新轮（items 去重按 ref）
def add_items(dst, items):
    seen = {it['ref'] for it in dst}
    for it in items:
        if it.get('ref') not in seen:
            dst.append(copy.deepcopy(it)); seen.add(it.get('ref'))
RV_MAP = {
    ("S1", "2022-12"): "RV-2022.2",
    ("S4", "2025-01"): "RV-2025.1",
    ("S5", "2026-11"): "RV-2026.2",
}
for s in d['seasons']:
    sid = s['id']
    if sid == 'S6':
        continue
    for r in s['rounds']:
        key = f"{sid}:{r['code']}"
        evd = d['roundEvidence'].get(key)
        if not evd:
            continue
        # 该旧轮的动作落到哪些新轮
        targets = {}
        for i in range(len(r['moves'])):
            nsid, ncode, nidx = MOVE_MAP[(sid, r['code'], i)]
            targets.setdefault((nsid, ncode), []).append((i, nidx))
        for (nsid, ncode), pairs in targets.items():
            nk = f"{nsid}:{ncode}"
            ent = new_evidence.setdefault(nk, {"status": "opinion", "items": [], "moves": {}, "note": ""})
            add_items(ent['items'], evd.get('items', []))
            for (oi, ni) in pairs:
                mk = f"{oi}:{r['moves'][oi][0]}"
                if mk in evd.get('moves', {}):
                    ent['moves'][f"{ni}:{r['moves'][oi][0]}"] = copy.deepcopy(evd['moves'][mk])
            # status 取最强
            order = {"verified": 3, "opinion": 2, "pending": 1}
            if order.get(evd.get('status'), 0) > order.get(ent['status'], 0):
                ent['status'] = evd['status']
        # RV：1:1 继承；合并轮用 RV_MAP；拆分轮用原轮 RV
        for (nsid, ncode) in targets:
            rk = f"{nsid}:{ncode}"
            if (nsid, ncode) in RV_MAP:
                new_rv[rk] = RV_MAP[(nsid, ncode)]
            else:
                new_rv[rk] = d['roundRV'][key]
# S0 证据/RV 并入
new_evidence.update(s0_evidence)
new_rv.update(s0_rv)
# S6 证据/RV 保持
for k, v in d['roundEvidence'].items():
    if k.startswith('S6:'):
        new_evidence[k] = copy.deepcopy(v)
for k, v in d['roundRV'].items():
    if k.startswith('S6:'):
        new_rv[k] = v
# S5 1-1 的 items 拆分修正：BIDU 去 11 月轮，SFTB 去 9 月轮；其余 Jan~Aug 轮清空 items
s5_11 = new_evidence['S5:2026-11']
s5_09 = new_evidence['S5:2026-09']
bidu_items = [it for it in s5_11['items'] if 'zacks' in (it.get('url') or '').lower() or 'BIDU' in (it.get('label') or '') or '百度' in (it.get('label') or '')]
sftb_items = [it for it in s5_09['items'] if 'japantimes' in (it.get('url') or '').lower() or 'SFTB' in (it.get('label') or '') or '软银' in (it.get('label') or '')]
# 若按 label/url 抓不到，退回按 1-1 旧证据 items 顺序（第 1 项 BIDU，第 2 项 SFTB）
old11 = d['roundEvidence']['S5:1-1']['items']
if not bidu_items and old11:
    bidu_items = [old11[0]]
if not sftb_items and len(old11) > 1:
    sftb_items = [old11[1]]
s5_11['items'] = [it for it in s5_11['items'] if it not in bidu_items] + bidu_items
s5_09['items'] = sftb_items
s5_09['status'] = 'verified'
for m in ['2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06', '2026-07', '2026-08']:
    ent = new_evidence[f'S5:{m}']
    ent['items'] = []
    ent['status'] = 'opinion'
    ent['moves'] = {}
print('evidence keys:', len(new_evidence), 'rv keys:', len(new_rv))

# ---------------------------------------------------------------- 证据修正：拆分轮不继承父轮 items
def set_opinion(nk):
    ent = new_evidence[nk]
    ent['items'] = []; ent['status'] = 'opinion'; ent['moves'] = {}
set_opinion('S2:2023-06')
set_opinion('S4:2025-06')
set_opinion('S4:2025-09')
set_opinion('S4:2025-10')
set_opinion('S4:2025-11')
# S4 2025-07 只保留 3-2 轮的 items；2025-08 只保留 4-1 轮的 items
new_evidence['S4:2025-07']['items'] = copy.deepcopy(d['roundEvidence']['S4:3-2']['items'])
new_evidence['S4:2025-08']['items'] = copy.deepcopy(d['roundEvidence']['S4:4-1']['items'])
# S5 1-1 的断点 note 归属 11 月轮（断点动作在 11 月轮）
S5_11_NOTE_EXTRA = ("本轮其余大动作（NVDA、GOOG、META、HUAWEI、DPSK、AAPL、ORCL、TSMC、SFTB）无逐动作证据："
    "S5 首轮增量含跨季对账断点（S5 英伟达金币、Anthropic 血量硬错误均记入首轮，见验证章），数值为对账后的模型分，非单一事件分。")
# note：1:1 轮继承原 note；合并轮拼接原 note；以下覆盖写明月份判定依据
EVIDENCE_NOTES = {
 "S1:2022-01": "开局选秀轮，无单一公开事件；全部动作为模型分。原轮次日期'2022 年初'，取 1 月（约定，非事件日期）。",
 "S1:2022-11": "ChatGPT 发布于 2022-11-30。",
 "S1:2022-12": "原 2-5 轮与 3-2 轮合并；3-2 轮原日期'2022 年底'，取 12 月（约定）。经济轮，无交战；'微软账上金币最厚'为模型内比较，非财报口径。",
 "S2:2023-05": "Vision Pro 动作另拆 2023-06 轮。",
 "S2:2023-06": "本轮由原 S2 2-6 轮按月拆分；Vision Pro 发布于 2023-06-05（WWDC）。Δ 均为模型分。",
 "S3:2024-01": "经济轮：四家云厂资本开支指引上调为多家财报电话会口径的合成判断；本轮未逐家挂证据。Qwen1.5 动作另拆 2024-02 轮。原轮次日期'2024 年初'，取 1 月（约定）。",
 "S3:2024-02": "本轮由原 S3 1-1 轮按月拆分；Qwen1.5 发布于 2024-02-05（题集 testset-v7 q89 实测日期）。Δ 均为模型分。",
 "S3:2024-07": "本轮无单一事件日期；原轮次日期为'2024 年下半年'，取首月 7 月（约定，非事件日期）。机制指针为 CoreWeave 2024-05 75 亿美元 GPU 抵押融资（见原证据）。Δ 均为模型分。",
 "S4:2025-01": "本轮由原 S4 1-1、1-2、1-3 三轮合并；1 月 20 日 R1 发布、1 月 21 日星门宣布、1 月 27 日血崩日。本轮 ORCL、SFTB 的大动作无逐动作证据：为模型分，非单一事件分。",
 "S4:2025-06": "本轮由原 S4 3-2 轮按月拆分；文心 4.5 开源于 2025-06-30（题集 testset-v7 q98 实测日期）。Δ 均为模型分。",
 "S4:2025-07": "原轮次日期'2025 年年中'； dated 动作集中在 2025-06-30 至 07-28，取 7 月为主月，文心 4.5 开源（06-30）另拆 6 月轮；甲骨文星门大单（2025-07-22，300 亿美元/年，4.5GW）由原 4-1 轮并入。",
 "S4:2025-08": "原轮次日期'2025 年 8 月起'，取 8 月为主月；9~11 月发布另拆。",
 "S4:2025-09": "本轮由原 S4 4-1 轮按月拆分；Sonnet 4.5 发布于 2025-09-29，Sora 2 发布于 2025-09-30（题集 testset-v7 q145；覆盖计划）。Δ 均为模型分。",
 "S4:2025-10": "本轮由原 S4 4-1 轮按月拆分；Haiku 4.5 发布于 2025-10-15，ChatGPT Atlas 发布于 2025-10-21，MiniMax M2 发布于 2025-10-27（题集 q146、q112；公开资料）。Δ 均为模型分。",
 "S4:2025-11": "本轮由原 S4 4-1 轮按月拆分；TRAE SOLO GA 2025-11-04，Kimi K2 Thinking 2025-11-06，GPT-5.1 2025-11-12，Gemini 3 与 Antigravity 2025-11-18，Opus 4.5 2025-11-24（题集 q166、q147；公开资料）。Δ 均为模型分。",
 "S4:2025-12": "原轮次日期'2025 年末'，取 12 月；GPT-5.2（12-11）与 DeepSeek V3.2（12-01）均在 12 月。疲劳轮：'循环融资'为媒体与审计章的定性判断；OpenAI 2026-03 轮中的供应商融资见审计章，但属 S5 年份，不作本轮证据。本轮无单一硬指针。",
 "S5:2026-01": "本轮由原 S5 1-1 轮按月拆分；Cowork 研究预览 2026-01-12（q115），Kimi K2.5 2026-01-27（q167）。Δ 均为模型分。",
 "S5:2026-02": "本轮由原 S5 1-1 轮按月拆分；Opus 4.6 2026-02-05（q148），Sonnet 4.6 2026-02-17（q149），Gemini 3.1 Pro 2026-02-19（q163）；五角大楼传召与护栏之争为 2026 年 2 月。Δ 均为模型分。",
 "S5:2026-03": "本轮由原 S5 1-1 轮按月拆分；WorkBuddy 2026-03-09（q116）。Δ 均为模型分。",
 "S5:2026-04": "本轮由原 S5 1-1 轮按月拆分；Muse Spark 2026-04-08（q181），Opus 4.7 2026-04-16（q150），DeepSeek V4 预览 2026-04-24（q206）。Δ 均为模型分。",
 "S5:2026-05": "本轮由原 S5 1-1 轮按月拆分；Grok Build 2026 年 5 月（q117，仅到月），字节资本开支 2026-05-27（q17），Opus 4.8 2026-05-28（q151）。Δ 均为模型分。",
 "S5:2026-06": "本轮由原 S5 1-1 轮按月拆分；Fable 5 2026-06-09（q152）。Δ 均为模型分。",
 "S5:2026-07": "本轮由原 S5 1-1 轮按月拆分；Kimi K3 2026-07-16（q168），CodeBuddy NPC 2026-07-23（q118），Opus 5 2026-07-24（q153）。Δ 均为模型分。",
 "S5:2026-08": "本轮由原 S5 1-1 轮按月拆分；Grok Bot 2026-08-11（q119），V4-Pro GA 2026-08-13（q207），Qwen3.8-Flash-Next 2026-08-26（q202），OpenClaw 2.0 2026-08-31（q120）。Δ 均为模型分。",
 "S5:2026-09": "本轮由原 S5 1-1 轮按月拆分；V4.1 Flash 2026-09-10（q208），软银贷款 2026-09-14（q43），Qwen3.8-Omni-Flash 2026-09-18（q203）。Δ 均为模型分。",
 "S5:2026-11": ("承诺类动作以 S-1/A No.2（2026-11-10）披露的 9009 亿美元承诺总额为锚；原 1-1 轮日期'2026 年上半年'与内容不符"
    "（内容含 2026-11-16 百度财报与 2026-09-14 软银贷款），已按题集实测日期拆分；原 6-2 轮'结算中'证伪条件未触发，合并后状态以已核实动作计。" + S5_11_NOTE_EXTRA),
}
# 1:1 轮继承原 note；其余未覆盖的轮保留通用聚合 note（空则留空）
for (sid, code), srcs in ROUTES.items():
    nk = f"{sid}:{code}"
    if nk in EVIDENCE_NOTES:
        new_evidence[nk]['note'] = EVIDENCE_NOTES[nk]
    elif len(srcs) == 1 and srcs[0][2] == 'ALL':
        old_note = d['roundEvidence'].get(f"{srcs[0][0]}:{srcs[0][1]}", {}).get('note', '')
        new_evidence[nk]['note'] = old_note
print('evidence notes assigned')

# ---------------------------------------------------------------- 玩家、开局、元数据
NEW_PLAYERS = {
 "HF": {"id": "HF", "code": "HF", "name": "Hugging Face", "color": "#f59e0b", "sym": "HF",
        "role": "开源模型枢纽 · 2019 年起进场",
        "style": "开源枢纽：模型库与社区是基本盘。", "open": "开源模型库", "weak": "平台而非模型厂",
        "bond": "绑定开源社区：BLOOM 与 DistilBERT 的家。"},
 "STAB": {"id": "STAB", "code": "STAB", "name": "Stability AI", "color": "#db2777", "sym": "ST",
          "role": "开源文生图 · 2022 年 8 月进场",
          "style": "开源文生图：Stable Diffusion 一夜改写门槛。", "open": "开源文生图模型", "weak": "商业化薄弱",
          "bond": "绑定开源文生图：Stable Diffusion 的家。"},
 "MJ": {"id": "MJ", "code": "MJ", "name": "Midjourney", "color": "#0ea5e9", "sym": "MJ",
        "role": "AI 绘画社区 · 2022 年 7 月进场",
        "style": "社区驱动绘画：审美即护城河。", "open": "社区订阅制绘画", "weak": "只做绘画",
        "bond": "绑定 AI 绘画社区：Discord 里的画室。"},
 "AI21": {"id": "AI21", "code": "AI21", "name": "AI21 Labs", "color": "#16a34a", "sym": "A2",
          "role": "大模型 · 2021 年 8 月进场",
          "style": "以色列大模型：Jurassic 系列。", "open": "Jurassic 大模型", "weak": "规模不及头部",
          "bond": "绑定大模型第二梯队：Jurassic-1 的家。"},
 "UCB": {"id": "UCB", "code": "UCB", "name": "加州大学伯克利分校", "color": "#65a30d", "sym": "UC",
         "role": "学术机构 · 2020 年 9 月进场",
         "style": "学术基准制定者：MMLU 影响全行业评测。", "open": "学术研究与基准", "weak": "不做产品",
         "bond": "绑定学术界：MMLU 基准的家。"},
 "EU": {"id": "EU", "code": "EU", "name": "欧盟", "color": "#1e40af", "sym": "EU",
        "role": "监管机构 · 2018 年 12 月进场",
        "style": "规则制定者：AI 法案是全桌的规则桌。", "open": "AI 法案与伦理指南", "weak": "不直接参赛",
        "bond": "绑定规则桌：AI 法案的制定者。"},
 "USGOV": {"id": "USGOV", "code": "USGOV", "name": "美国政府", "color": "#b91c1c", "sym": "US",
           "role": "政策机构 · 2019 年 2 月进场",
           "style": "政策制定者：行政令与法案定方向。", "open": "AI 倡议与法案", "weak": "不直接参赛",
           "bond": "绑定政策桌：美国 AI 倡议的制定者。"},
 "ACM": {"id": "ACM", "code": "ACM", "name": "美国计算机学会", "color": "#6b7280", "sym": "AC",
         "role": "学术机构 · 2019 年 3 月进场",
         "style": "学术荣誉制定者：图灵奖定义先驱。", "open": "图灵奖", "weak": "不直接参赛",
         "bond": "绑定学术界：图灵奖的颁发者。"},
}
# 新玩家在 data.players 末尾追加（保持原 24 人顺序不变）
for code, p in NEW_PLAYERS.items():
    d['players'].append(dict(p))
# playerCards 追加：值为关键牌名数组；前传新玩家无专属关键牌，记空数组
for code in NEW_PLAYERS:
    d['playerCards'][code] = []

# 开局：S0 100 血 / 0 金（15 名 S0 玩家）；S1~S6 不变
d['openings']['S0'] = {"hp": {p: 100 for p in S0_PLAYERS},
                       "gold": {p: 0 for p in S0_PLAYERS}}
d['seasons'] = new_seasons
d['roundRV'] = new_rv
d['roundEvidence'] = new_evidence

# 总图点数：renderChart 按 s.meta（赛季 roster）画点，每名玩家每季一个点
chart_points = sum(len(s['meta']) for s in new_seasons)
assert chart_points == 139, chart_points
d['meta']['title'] = "金铲铲复盘：AI 大厅 2018–2026 — 页面数据（单一事实源）"
d['meta']['accounting'] = (
    "单一事实源。第一层：S0 前传赛季（2018-06 至 2022-12，55 个月轮，106 条事件，"
    "15 名玩家，100 血 / 0 金起算）；S1–S5 按月重组（642 条动作，Δ 未动，轮次从旧 31 轮变为 38 轮，"
    "2026 年 11 月 S5 轮与 S6 1-1 轮分立，见下）；S6 1-1 轮（Pachocki 提案、黄仁勋复任、Megaspeed 列入实体清单，3 条）。动作总数 751，轮次总数 94，"
    "玩家 32 名（新增 HF、STAB、MJ、AI21、UCB、EU、USGOV、ACM，均为 S0 进场）。"
    "S1 开局为冻结开局，不承接 S0 季末（S0 与 S1 在 2022 年日历重叠，属前传与正赛双轨）；"
    "S2–S6 开局承接上季季末。2026 年 11 月分立原因：Pachocki 提案为 OpenAI +3 血 / +1 金，"
    "若并入 S5 轮会使 S5 季末 OpenAI 变为 82 血 / 59 金，与已冻结的 79 血 / 58 金冲突；"
    "黄仁勋复任为 NVDA +6 血 / +3 金、Megaspeed 列入实体清单为 NVDA -5 血 / -2 金，"
    "若并入 S5 轮还会使 S5 季末 NVDA 变为 37 血 / 55 金，与已冻结的 36 血 / 54 金冲突，"
    "故 S5 11 月轮（117 条）与 S6 1-1 轮（3 条）并存，同月不同季。S5 11 月轮标签为 11 月 1–21 日，"
    "S6 1-1 轮标签为 11 月 22–30 日。S5 季末与 S6 开局值不变（OpenAI 79 血 / 58 金，"
    "Anthropic 121 血 / 113 金，英伟达 36 血 / 54 金）。"
    "其余核算口径与旧版一致：回合增量含跨季对账断点，断点记入每季首轮（S1 1-1、S2 1-1、S3 1-1、S4 1-1、S5 1-1 均为旧轮次代码，"
    "见 reconciliation 的 137 条对账记录，代码为重组前轮次代码）；'上月'指上一轮次的季内累计值，"
    "不含前一赛季的承接值。证据状态：verified = 有公开来源；opinion = 模型推断或无逐动作来源；"
    "pending = 结算中。金币为模型内结算单位，非财报口径。"
)
d['meta']['derived']['chart'] = (
    f"总图折线 {chart_points} 个点由程序从算出的赛季末血量生成。按季节内顺序走。"
)
d['meta']['derived']['roundStart'] = (
    "开局规则：S0 为 100 血 / 0 金。S1 为冻结开局，不承接 S0 季末。S2–S6 为上季季末承接值。"
    "冻结开局不等于当季实盘起点：S1 冻结开局只作为当季第一轮的基数。"
)
# formulas 口径：S0→S1 冻结开局断点；实测最高血量 135
d['formulas']['accounting']['carry'] = (
    "跨季承接。S0 以 100 血 / 0 金开局。S1 以冻结开局表为准（见验证章附表），不承接 S0 季末"
    "（前传与正赛双轨，S0 与 S1 在 2022 年日历重叠）。S2–S6 的开局血量与开局金币等于上一季的赛季末数值。"
    "除 S0→S1 冻结开局断点外，不存在与上季季末断裂的开局值。卡池与估值按结算面板重置。血量与金币不重置。"
)
d['formulas']['accounting']['note'] = d['formulas']['accounting']['note'] + (
    "2026-11-23 按月重组：新增 S0 前传赛季（55 轮 106 条），S1–S5 按月重组（Δ 未动），"
    "S5 季末与 S6 开局不变；血量量程仍为 0–140（实测最高 135，S0 OpenAI 季末）。"
)
# meta.audit14 保留原文字（其 counts 由页面 checker 动态核对，不再是静态事实）
# ---------------------------------------------------------------- 终验
def standings(sid):
    hp = dict(d['openings'][sid]['hp']); gd = dict(d['openings'][sid]['gold'])
    for s in new_seasons:
        if s['id'] != sid:
            continue
        for r in s['rounds']:
            for (pl, _t, dh, dg) in r['moves']:
                hp[pl] = hp.get(pl, 0) + dh; gd[pl] = gd.get(pl, 0) + dg
    return hp, gd

report = {"generated": "2026-11-23", "s0_events": len(ev), "s0_months": len(months),
          "rounds_total": 0, "moves_total": 0, "players_total": len(d['players']),
          "new_players": list(NEW_PLAYERS.keys()),
          "rounds_by_season": {}, "moves_by_season": {}, "s0_end": {}, "s0_prefix": {},
          "s5_end_check": {}, "s6_end_check": {}, "s0_s1_gap": {}, "evidence_summary": {},
          "chart_points": chart_points, "reconciliation_check": {}, "per_player_moves": {}}
for s in new_seasons:
    report['rounds_by_season'][s['id']] = len(s['rounds'])
    report['moves_by_season'][s['id']] = sum(len(r['moves']) for r in s['rounds'])
    report['rounds_total'] += len(s['rounds'])
    report['moves_total'] += sum(len(r['moves']) for r in s['rounds'])
report['s0_end'] = {p: list(v) for p, v in sorted(s0_end.items(), key=lambda kv: -kv[1][0])}
report['s0_prefix'] = {"hp_min": s0_prefix_min, "hp_max": s0_prefix_max, "gold_min": s0_gold_min}
hp5, gd5 = standings('S5')
report['s5_end_check'] = {"OAI": [hp5['OAI'], gd5['OAI']], "ANTH": [hp5['ANTH'], gd5['ANTH']],
                          "NVDA": [hp5['NVDA'], gd5['NVDA']],
                          "expected": {"OAI": [79, 58], "ANTH": [121, 113], "NVDA": [36, 54]}}
assert (hp5['OAI'], gd5['OAI']) == (79, 58) and (hp5['ANTH'], gd5['ANTH']) == (121, 113) \
    and (hp5['NVDA'], gd5['NVDA']) == (36, 54), report['s5_end_check']
hp6, gd6 = standings('S6')
report['s6_end_check'] = {"OAI": [hp6['OAI'], gd6['OAI']]}
assert (hp6['OAI'], gd6['OAI']) == (82, 59)
# S0→S1 断点：S1 开局与 S0 季末的差（有意为之）
for p in ['OAI', 'GOOG', 'NVDA']:
    report['s0_s1_gap'][p] = {"s0_end": list(s0_end[p]), "s1_opening": [d['openings']['S1']['hp'][p],
                              d['openings']['S1']['gold'][p]]}
# 证据：每轮必有条目；move 键可解析；url 全为 https
all_round_keys = {f"{s['id']}:{r['code']}" for s in new_seasons for r in s['rounds']}
assert set(new_evidence) == all_round_keys, set(new_evidence) ^ all_round_keys
assert set(new_rv) == all_round_keys, set(new_rv) ^ all_round_keys
for k, ent in new_evidence.items():
    for it in ent.get('items', []):
        if it.get('kind') == 'url':
            u = it.get('ref') or it.get('url') or ''
            assert u.startswith('https://'), (k, it)
    sid, code = k.split(':')
    rnd = next(r for s in new_seasons if s['id'] == sid for r in s['rounds'] if r['code'] == code)
    for mk in ent.get('moves', {}):
        ni, pl = mk.split(':')
        assert 0 <= int(ni) < len(rnd['moves']) and rnd['moves'][int(ni)][0] == pl, (k, mk)
report['evidence_summary'] = {
    "total": len(new_evidence),
    "by_status": dict(collections.Counter(v['status'] for v in new_evidence.values())),
    "s0_with_url": sum(1 for k, v in new_evidence.items() if k.startswith('S0:') and v['items']),
}
# reconciliation：每条仍能在同季找到同玩家、同字段、同 moveTo 值的动作（轮次代码为重组前）
rec_ok, rec_miss = 0, []
for rec in d.get('reconciliation', []):
    sid = rec['season']
    found = any(m[0] == rec['player'] and m[2 if rec['field'] == 'hp' else 3] == rec['moveTo']
                for s in new_seasons if s['id'] == sid for r in s['rounds'] for m in r['moves'])
    if found:
        rec_ok += 1
    else:
        rec_miss.append(rec)
report['reconciliation_check'] = {"total": len(d.get('reconciliation', [])), "matched": rec_ok,
                                  "missed": rec_miss}
assert not rec_miss, rec_miss
# 每名玩家动作数
cnt = collections.Counter()
for s in new_seasons:
    for r in s['rounds']:
        for m in r['moves']:
            cnt[m[0]] += 1
report['per_player_moves'] = dict(cnt)
assert report['moves_total'] == 751, report['moves_total']
assert report['rounds_total'] == 94, report['rounds_total']
assert len(d['players']) == 32
# 写出
out_path = 'ts-spaces/jin-chan-chan-fu-pan-ai-da-ting-2022-2026/assets/data.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
with open('verification/rebuild_monthly_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print('WRITE OK', out_path)
print(json.dumps(report, ensure_ascii=False, indent=2)[:4000])
