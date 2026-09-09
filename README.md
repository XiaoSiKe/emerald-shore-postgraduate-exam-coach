<div align="center">

# 🌊 青岸计划·考研冲刺教练

### 一万年太久，只争朝夕！

#### 面向大学生日常、适配所有学校与专业的通用型考研冲刺 Agent Skill

**Emerald Shore Initiative · Postgraduate Entrance Exam Sprint Coach**

[![CI](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/actions/workflows/ci.yml/badge.svg)](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/XiaoSiKe/emerald-shore-postgraduate-exam-coach?color=0F766E)](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/releases)
[![Agent Skill](https://img.shields.io/badge/Agent-Skill-6C47FF)](#-安装)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-black)](LICENSE)

一个主攻 · 最多两个维持 · 校园节律 · 15% 缓冲 · 本地证据闭环

[🧭 它解决什么](#-它解决什么) · [🧩 八大系统](#-八大系统) · [📚 理论与方法](#-理论支持与经典方法) · [🚀 安装](#-安装) · [🧪 质量与验证](#-质量与验证)

</div>

---

> [!IMPORTANT]
> 这是一个 **Agent Skill**，不是独立 App、网课平台或题库网站。你直接在支持 Agent Skills 的对话中说出目标、资料和困难；Skill 负责诊断、调用本地证据引擎、推进训练并复盘。`emerald.py` 只是它用来保存学习状态的支撑工具，不是要求学生手动操作的主产品。

考研冲刺最难的，通常不是“没有更多计划”，而是同时面对太多科目、太多资料和太少时间，却不知道哪一处最值得先打穿。

青岸计划把考试日期、目标院校、课表与实习、工作日/周末时间、科目—章节—专题差距、真实资料、来源题、错因和限时成绩连成一个循环：**调查现状 → 找主要矛盾 → 集中训练 → 用结果检验 → 动态重排**。

它不押题，不承诺上岸，也不把“看懂了”当成“掌握了”。

“通用型”不是让所有人套同一张表，而是让不同学校、专业、科目、基础、备考身份和时间条件的人，都能用同一套证据闭环生成自己的计划。应届、跨考、二战、边实习边备考都能使用；公共课、统考专业课和自命题专业课都可自定义。

## 🧭 它解决什么

| 你现在的处境 | Skill 会做什么 | 你最终得到什么 |
|---|---|---|
| 不知道从哪科开始 | 比较得分缺口、考试权重、错因和成本 | 一个周主攻，而不是平均用力 |
| 科目太大、无从下手 | 建立科目—章节—专题骨架 | 最小突破口和可判定任务 |
| 上课、实验、实习把计划打乱 | 区分工作日/周末容量，扣除固定安排 | 能落进真实校园生活的今日单 |
| 宿舍学不动、图书馆才进入状态 | 保存地点锚点与启动触发 | 到点、到地、先做 5 分钟 |
| 看了很多却不会做 | 先闭卷回忆、解题或输出，再补最小解释 | 能被验证的掌握证据 |
| 资料很多、来源混乱 | 按归类置信度分流，区分官方、真题、目标院校公开资料和讲解源 | 可追溯的课程骨架与来源题 |
| 专业课是目标院校自命题 | 记录院校、专业、科目代码与材料匹配理由 | 不把同名课程误当目标范围 |
| 错题反复出现 | 记录知识、推理、步骤、粗心和时间错因 | 会回流计划的错因账本 |
| 知道该学却启动不了 | 把任务改成具体时间、地点和 5 分钟动作 | 可执行的 if–then 启动协议 |
| 越临近考试越焦虑 | 校准现实、缩小下一步、保护睡眠底线 | 不靠口号的降阶行动 |

## 🗣️ 直接这样开始

安装后，不需要先学习命令。新开一个对话，可以直接说：

```text
我离考研还有 82 天，每天现实能学 6 小时，先帮我判断该主攻哪一科。

我周一到周五要上课，只有 4 小时；周末能学 8 小时，常去图书馆三楼。请按这个节律排计划。

我是跨考生，专业课是目标院校自命题。这是招生目录、参考书和网上找到的往年资料，请先判断哪些真的匹配。

这是我的数学真题和最近两次模考，帮我找最限制得分的专题，今天一次只练一题。

我这周计划完成率不到一半，不要安慰我，帮我删掉低价值任务并重排。

我知道今晚该做英语阅读，但一直拖延。把它改成一个我能立刻开始的动作。

用青岸计划做周复盘：哪些判断有证据，哪些只是我的感觉？
```

首次使用时，Skill 只追问会改变计划的关键信息，不会让你一次填写一张长问卷。已有信息不会重复询问。

## 🧩 八大系统

| 系统 | 解决的问题 | 核心产出 |
|---|---|---|
| ① 学生画像与校园节律 | 每个人的课表、实习、通勤、睡眠和周末时间不同 | 工作日/周末容量、固定安排、地点锚点 |
| ② 目标院校与证据 | 自命题专业课资料多，但真假和匹配程度不同 | 院校/专业/科目代码、证据等级、匹配依据 |
| ③ 材料分流与课程骨架 | PPT、PDF、题库和笔记混在一起，直接总结容易失真 | 高/中/低归类置信度、科目—章节—专题地图 |
| ④ 主要矛盾与得分地图 | 科目和专题很多，不知道哪里最值得投入 | 一个周主攻、最小突破口、最多两个维持 |
| ⑤ 阶段计划与今日执行 | 长期日历很快失真，今日任务又经常超量 | 冲刺阶段、现实容量、15% 缓冲、触发式重排 |
| ⑥ 专题卡与理解增强 | 笔记只有目录，拿起来仍然不会背、不会做 | 背什么、怎么做、易错点、自测题、必要可视化 |
| ⑦ 逐题训练与掌握校准 | 看答案产生熟悉感，连续做错又只会继续刷题 | 一次一题、错因定位、复习队列、自测熔断 |
| ⑧ 周复盘与情绪韧性 | 失约后计划报废，焦虑被误当成意志问题 | 计划—监控—反思、降阶动作、支架递减 |

### ① 学生画像与校园节律系统

首次建档区分工作日和周末，记录上课、实验、实习、社团、通勤、睡眠底线与常用学习地点。整块时间留给数学、专业课推导或主观题；课间和通勤只安排短回忆。当天被临时课程打断时删减或顺延，不把欠账滚成第二天的惩罚。

### ② 目标院校与证据系统

档案可以记录目标院校、专业和科目代码。公开网络资料只有在院校、科目/代码、材料类型与年份可追溯时，才标为 `target_school_open`；它可以帮助判断题型风格，但不能替代官方招生目录、大纲和用户确认的参考书。

### ③ 材料分流与课程骨架系统

支持本地读取 PDF、DOCX、PPTX、TXT、Markdown 和 HTML。材料先分成 `high`、`medium`、`low` 置信度：低置信保持待确认，中等置信只暂归科目，高置信且范围明确才绑定专题。随后建立“科目 → 章节 → 专题 → 来源题”骨架，扫描版 PDF 无文字时明确提示视觉/OCR 限制。

### ④ 主要矛盾与得分地图系统

先比较科目得分缺口、考试权重、重复错因、前置影响和成本，再在主攻科目内比较专题权重、掌握度与证据质量。每周只有一个主攻，每天最多两个维持；数据不足时只说“暂定”，先安排小测，不伪装精确。

### ⑤ 阶段计划与今日执行系统

依据剩余时间进入基础重建、专题强化、真题限时或考前稳定阶段。当天容量来自校园节律，并预留 15% 缓冲；`focus` 把任务落成具体时间、地点和 5 分钟启动动作。睡眠不能作为被无限挤压的“备用时间”。

### ⑥ 专题卡与理解增强系统

每张专题卡必须能让学生直接开始：闭卷要写什么、遇题如何识别、最短步骤是什么、哪里容易错、怎样自测。关系、区域、方向、坐标变换或论证层级难以理解时，才使用表格、ASCII、Mermaid 或示意图；纯装饰不算学习产出。

### ⑦ 逐题训练与掌握校准系统

训练一次只显示一道来源题，学生作答后才给最小反馈并记录 `attempt`。连续失败先定位定义、公式、题型识别、步骤、表达还是时间压力；三次 `wrong`/`partial` 触发熔断，回专题卡重建并完成一次成功闭卷提取后再测。掌握至少需要重复提取，并包含一次限时或迁移证据。

### ⑧ 周复盘与情绪韧性系统

每周从真实账本检查执行率、计划/实际分钟、闭卷或限时证据与重复错因，再决定保留、削减和重排。执行率低于 60% 时先缩小任务，不归因人格。情绪支持采用“具体共情—现实校准—缩小下一步—归还控制感”，连续稳定后逐步减少教练支架。

## 📚 理论支持与经典方法

下面这些方法不是装饰性术语，而是各系统的设计依据；最终是否有效，仍由个人的限时成绩、提取表现和执行记录校准。

| 功能设计 | 理论或经典方法 | 在考研冲刺中的转译 |
|---|---|---|
| 一次稳定一个主攻 | 认知负荷理论、目标屏蔽、抓主要矛盾 | 减少多科同时切换；保留少量维持，防止单科沉没 |
| 先看考试日期与校园容量 | 倒排计划、时间盒、约束规划 | 从考试日倒推阶段，用工作日/周末真实时间决定任务体积 |
| 材料分流与来源记录 | 信息分块、来源追踪、证据层级、三角互证 | 不把低置信文件静默并入科目，不用随机网页定义考试范围 |
| 先建课程骨架 | 先行组织者、图式理论、概念图、建构性对齐 | 先画科目—章节—专题—题目，再压缩高价值内容 |
| 目标院校定向证据 | 情境匹配、近迁移、生态效度、来源批判 | 同校同科资料只增强题型线索，必须记录代码、类型和年份 |
| 专题卡 | Cornell 提问、主动回忆、生成效应、worked example | 每张卡都包含闭卷提示、方法步骤、易错点与自测入口 |
| 必要才可视化 | 双编码、多媒体学习、空间推理外化 | 图必须帮助理解区域、关系、方向或论证，不做装饰 |
| 短轮自测与错因定位 | 检索练习、形成性评价、掌握学习、错误分析 | 先答再讲；根据第一个关键错因决定补概念、识别还是步骤 |
| 连续失败熔断 | 认知负荷管理、教学支架、挫败控制 | 三次失败停止加题，回专题卡完成最小重建后再测 |
| 周复盘与启动协议 | 自我调节学习、implementation intention | 用“计划—监控—反思”和 if–then 把目标变成可执行行为 |
| 新材料增量更新 | 学习日志、间隔提取、阶段性认识 | 只更新受影响的范围、专题卡和自测，不全量推倒重来 |

本轮重点研究了 [`cxs885187-create/--skill`](https://github.com/cxs885187-create/--skill) 中“一门课一门课处理、材料置信分流、课程骨架、学校定向资料、专题卡、可视化、自测熔断与增量更新”等机制，再改造成面向考研多科统筹、目标院校证据和长期冲刺的原创系统。该仓库 README 声称 MIT，但没有 `LICENSE` 文件，GitHub License API 也无法识别，因此本项目只采用抽象机制与研究线索，不复制其文字、模板、目录或代码。

学习科学论文、经典方法来源、固定 commit 和采用边界见 [`docs/SOURCE_AUDIT.md`](docs/SOURCE_AUDIT.md)。

## ⚙️ 它怎么工作

```text
对话层：理解目标、校园日常和困难，只追问一个会改变决策的问题
   ↓
证据层：读写院校、节律、科目、章节、专题、资料、训练与复盘状态
   ↓
反馈层：翻译成简洁中文，只给当前依据、下一动作和完成证据
   ↺
结果回流：成绩、错因或执行率变化后，重新判断主要矛盾
```

详细规则按场景加载：[`教练编排`](references/coach-orchestration.md)、[`校园生活与通用适配`](references/campus-life-system.md)、[`课程骨架与证据`](references/course-evidence-system.md)、[`训练闭环`](references/training-loop.md)、[`学习科学`](references/learning-science.md) 和 [`情绪支持`](references/emotional-support.md)。Skill 不会把全部资料一次塞进上下文。

<details>
<summary><strong>开发者与高级用户：本地引擎命令</strong></summary>

Skill 会在需要时调用这些稳定接口：

```bash
python emerald.py init WORKSPACE --exam-date 2026-12-20 --daily-hours 6 --target-school 目标大学 --target-major 目标专业
python emerald.py routine set WORKSPACE --weekday-hours 4 --weekend-hours 8 --sleep-floor-hours 7 --preferred-place "图书馆三楼" --fixed-commitment "周三实验课"
python emerald.py subject add WORKSPACE --name 数学 --max-score 150 --baseline 70 --target 110 --kind calculation --code 301
python emerald.py topic add WORKSPACE --subject 数学 --name 微积分 --chapter 高等数学 --weight 3 --mastery 0.35 --confidence 0.7
python emerald.py ingest WORKSPACE ./数学真题.pdf --evidence-level past_paper --classification-confidence high --subject 数学 --topic 微积分
python emerald.py ingest WORKSPACE ./目标院校公开题.pdf --evidence-level target_school_open --subject 数学 --match-note "院校、科目代码、资料类型与年份匹配"
python emerald.py plan WORKSPACE
python emerald.py today WORKSPACE
python emerald.py drill WORKSPACE --subject 数学 --topic 微积分
python emerald.py attempt WORKSPACE --question-id ID --result wrong --minutes 12 --error-type reasoning
python emerald.py focus WORKSPACE --task-id ID --when "晚饭后 19:00" --where "图书馆三楼"
python emerald.py weekly WORKSPACE
```

命令名、参数、`KIND` 枚举和 JSON 字段保持英文，是为了兼容不同 Agent 宿主和脚本；面向学生的解释默认使用中文。

重复材料默认保留已有证据等级；只有材料身份经过重新核验时才使用 `--replace-metadata`，避免默认参数把官方或真题来源静默降级。

</details>

## 🚀 安装

### 使用 Skills CLI

在当前项目安装：

```bash
npx skills add XiaoSiKe/emerald-shore-postgraduate-exam-coach --skill emerald-shore-postgraduate-exam-coach -y
```

希望所有项目都能使用，可全局安装：

```bash
npx skills add XiaoSiKe/emerald-shore-postgraduate-exam-coach --skill emerald-shore-postgraduate-exam-coach -g -y
```

检查安装结果：

```bash
npx skills list
```

### 下载 Release

也可以从 [Releases](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/releases) 下载 `emerald-shore-postgraduate-exam-coach-v0.4.0.zip`。解压后，把完整的 `emerald-shore-postgraduate-exam-coach/` 文件夹放入宿主的 Skill 目录。

运行本地证据引擎需要 Python 3.9+。PDF 文字提取建议安装可选依赖：

```bash
python -m pip install pypdf
```

### 从 V0.1.0 升级

旧工作区若包含 `.qingan/`，Skill 会调用：

```bash
python emerald.py migrate WORKSPACE
```

迁移会复制并升级到 `.emerald-shore/`；旧目录完整保留，可随时回退。V0.2.0 与 V0.3.0 工作区无需 schema 迁移，运行 `profile set` 和 `routine set` 即可按需补充新信息。

## 🔒 隐私与证据边界

- 学习状态只保存在用户选择的学习目录内，不含遥测。
- 原始资料只读，不移动、不自动上传，也不会被打进仓库或 Release。
- 当年大纲、招生政策和考试日期等易变信息只采用官方来源，并标注核验日期。
- 没有材料时可以生成明确标注的 AI 练习题，但绝不冒充真题、老师重点或目标院校预测。
- 这是冲刺决策与训练 Skill，不替代教师、官方招生信息或心理治疗。

## 🧪 质量与验证

项目同时验证 Skill 契约、确定性引擎和可安装发布包：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_skill.py .
python3 scripts/run_static_eval.py
python3 scripts/build_release.py --check
```

当前门禁覆盖跨平台 Python、原子状态、旧数据迁移、校园节律容量、目标院校证据门、章节/专题排序、材料置信分流、来源题不泄露答案、周复盘、Skill 按需引用、发布包单根目录和重复构建一致性。静态行为契约不冒充真实模型评测，完整说明见 [`eval/REPORT.md`](eval/REPORT.md)。

方法来源、固定 commit、许可证和采用边界见 [`docs/SOURCE_AUDIT.md`](docs/SOURCE_AUDIT.md) 与 [`sources.lock.json`](sources.lock.json)。

## 📚 项目文档

- [`SKILL.md`](SKILL.md)：Skill 入口、路由和不可违背的训练纪律。
- [`references/campus-life-system.md`](references/campus-life-system.md)：大学生日常节律与跨人群通用适配。
- [`references/course-evidence-system.md`](references/course-evidence-system.md)：材料分流、课程骨架、目标院校证据、专题卡与自测熔断。
- [`docs/PRD.md`](docs/PRD.md)：用户、核心旅程、非目标与验收。
- [`docs/RD.md`](docs/RD.md)：状态、算法、材料、错误与兼容设计。
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md)：版本、质量门禁、反馈和发布。
- [`CONTRIBUTING.md`](CONTRIBUTING.md)：贡献规则与本地验证。
- [`CHANGELOG.md`](CHANGELOG.md)：版本变化。

## 📄 许可证

项目以 [MIT License](LICENSE) 发布。第三方调研来源与许可边界见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
