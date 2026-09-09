<div align="center">

# 🌊 青岸计划

### 面向大学生的考研突击冲刺 Agent Skill

**Emerald Shore Initiative · Postgraduate Entrance Exam Sprint Coach**

[![CI](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/actions/workflows/ci.yml/badge.svg)](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/XiaoSiKe/emerald-shore-postgraduate-exam-coach?color=0F766E)](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/releases)
[![Agent Skill](https://img.shields.io/badge/Agent-Skill-6C47FF)](#-安装)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-black)](LICENSE)

一个主攻 · 最多两个维持 · 15% 缓冲 · 本地证据闭环

[🧭 它解决什么](#-它解决什么) · [🧩 核心能力](#-核心能力) · [⚙️ 工作方式](#️-它怎么工作) · [🚀 安装](#-安装) · [🧪 质量与验证](#-质量与验证)

</div>

---

> [!IMPORTANT]
> 这是一个 **Agent Skill**，不是独立 App、网课平台或题库网站。你直接在支持 Agent Skills 的对话中说出目标、资料和困难；Skill 负责诊断、调用本地证据引擎、推进训练并复盘。`emerald.py` 只是它用来保存学习状态的支撑工具，不是要求学生手动操作的主产品。

考研冲刺最难的，通常不是“没有更多计划”，而是同时面对太多科目、太多资料和太少时间，却不知道哪一处最值得先打穿。

青岸计划把考试日期、科目与专题差距、真实资料、来源题、错因、限时成绩和执行记录连成一个循环：**调查现状 → 找主要矛盾 → 集中训练 → 用结果检验 → 动态重排**。

它不押题，不承诺上岸，也不把“看懂了”当成“掌握了”。

## 🧭 它解决什么

| 你现在的处境 | Skill 会做什么 | 你最终得到什么 |
|---|---|---|
| 不知道从哪科开始 | 比较得分缺口、考试权重、错因和成本 | 一个周主攻，而不是平均用力 |
| 科目太大、无从下手 | 继续定位到高价值专题 | 最小突破口和可判定任务 |
| 计划每天都做不完 | 按现实时间压缩容量并保留 15% 缓冲 | 一个主攻 + 最多两个维持 |
| 看了很多却不会做 | 先闭卷回忆、解题或输出，再补最小解释 | 能被验证的掌握证据 |
| 资料很多、来源混乱 | 本地建库并区分官方、真题、用户材料和外部讲解 | 可追溯的来源题与材料索引 |
| 错题反复出现 | 记录知识、推理、步骤、粗心和时间错因 | 会回流计划的错因账本 |
| 知道该学却启动不了 | 把任务改成具体时间、地点和 5 分钟动作 | 可执行的 if–then 启动协议 |
| 越临近考试越焦虑 | 校准现实、缩小下一步、保护睡眠底线 | 不靠口号的降阶行动 |

## 🗣️ 直接这样开始

安装后，不需要先学习命令。新开一个对话，可以直接说：

```text
我离考研还有 82 天，每天现实能学 6 小时，先帮我判断该主攻哪一科。

这是我的数学真题和最近两次模考，帮我找最限制得分的专题，今天一次只练一题。

我这周计划完成率不到一半，不要安慰我，帮我删掉低价值任务并重排。

我知道今晚该做英语阅读，但一直拖延。把它改成一个我能立刻开始的动作。

用青岸计划做周复盘：哪些判断有证据，哪些只是我的感觉？
```

首次使用时，Skill 只追问会改变计划的关键信息，不会让你一次填写一张长问卷。已有信息不会重复询问。

## 🧩 核心能力

### 1. 科目 → 专题的双层诊断

先找最影响总分的科目，再在这门科目里比较专题权重、当前掌握、证据可信度、重复错误和时间成本。数据不足时只给“暂定主攻”，并安排一个最小诊断，不把启发式小数包装成科学精确值。

### 2. 来源题训练闭环

支持本地读取 PDF、DOCX、PPTX、TXT、Markdown 和 HTML。材料可以绑定科目与专题；训练时一次只显示一道来源题，学生作答后才判定并记录结果。扫描版 PDF 会明确提示视觉/OCR 限制，不会猜测正文。

### 3. 会改变计划的证据账本

限时成绩、逐题结果、实际时长和错因都会进入 `.emerald-shore/`。今日计划、复习队列、专题掌握度和周主攻从这些记录重建，不靠对话中的模糊印象。

### 4. 计划—监控—反思

每周检查“计划是否发生、是否产生闭卷/限时证据、什么错因反复出现、哪个条件失真”，然后决定保留、削减和重排。连续稳定后，Skill 会减少支架，把决策权逐步交还给学生。

### 5. 情绪支持与现实边界

采用“具体共情—现实校准—缩小下一步—归还控制感”，不羞辱、不灌鸡汤、不承诺结果。出现自伤、自杀或无法保障自身安全等危机信号时，立即停止学习施压，优先建议现实中的紧急支持。

## ⚙️ 它怎么工作

```text
对话层：理解目标和困难，只追问一个会改变决策的问题
   ↓
证据层：由 Skill 调用本地引擎，读写科目、专题、资料、训练与复盘状态
   ↓
反馈层：翻译成简洁中文，只给当前依据、下一动作和完成证据
   ↺
结果回流：成绩、错因或执行率变化后，重新判断主要矛盾
```

详细的 Agent 编排规则见 [`references/coach-orchestration.md`](references/coach-orchestration.md)。训练、学习科学与情绪支持只在对应场景按需加载，避免把所有说明一次塞进上下文。

<details>
<summary><strong>开发者与高级用户：本地引擎命令</strong></summary>

Skill 会在需要时调用这些稳定接口：

```bash
python emerald.py init WORKSPACE --exam-date 2026-12-20 --daily-hours 6
python emerald.py subject add WORKSPACE --name 数学 --max-score 150 --baseline 70 --target 110 --kind calculation
python emerald.py topic add WORKSPACE --subject 数学 --name 微积分 --weight 3 --mastery 0.35 --confidence 0.7
python emerald.py ingest WORKSPACE ./数学真题.pdf --evidence-level past_paper --subject 数学 --topic 微积分
python emerald.py plan WORKSPACE
python emerald.py today WORKSPACE
python emerald.py drill WORKSPACE --subject 数学 --topic 微积分
python emerald.py attempt WORKSPACE --question-id ID --result wrong --minutes 12 --error-type reasoning
python emerald.py focus WORKSPACE --task-id ID --when "晚饭后 19:00" --where "图书馆三楼"
python emerald.py weekly WORKSPACE
```

命令名、参数、`KIND` 枚举和 JSON 字段保持英文，是为了兼容不同 Agent 宿主和脚本；面向学生的解释默认使用中文。

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

也可以从 [Releases](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/releases) 下载 `emerald-shore-postgraduate-exam-coach-v0.3.0.zip`。解压后，把完整的 `emerald-shore-postgraduate-exam-coach/` 文件夹放入宿主的 Skill 目录。

运行本地证据引擎需要 Python 3.9+。PDF 文字提取建议安装可选依赖：

```bash
python -m pip install pypdf
```

### 从 V0.1.0 升级

旧工作区若包含 `.qingan/`，Skill 会调用：

```bash
python emerald.py migrate WORKSPACE
```

迁移会复制并升级到 `.emerald-shore/`；旧目录完整保留，可随时回退。V0.2.0 工作区无需迁移。

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

当前门禁覆盖跨平台 Python、原子状态、旧数据迁移、计划容量、专题排序、材料只读、来源题不泄露答案、周复盘、Skill 按需引用、发布包单根目录和重复构建一致性。静态行为契约不冒充真实模型评测，完整说明见 [`eval/REPORT.md`](eval/REPORT.md)。

方法来源、固定 commit、许可证和采用边界见 [`docs/SOURCE_AUDIT.md`](docs/SOURCE_AUDIT.md) 与 [`sources.lock.json`](sources.lock.json)。

## 📚 项目文档

- [`SKILL.md`](SKILL.md)：Skill 入口、路由和不可违背的训练纪律。
- [`docs/PRD.md`](docs/PRD.md)：用户、核心旅程、非目标与验收。
- [`docs/RD.md`](docs/RD.md)：状态、算法、材料、错误与兼容设计。
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md)：版本、质量门禁、反馈和发布。
- [`CONTRIBUTING.md`](CONTRIBUTING.md)：贡献规则与本地验证。
- [`CHANGELOG.md`](CHANGELOG.md)：版本变化。

## 📄 许可证

项目以 [MIT License](LICENSE) 发布。第三方调研来源与许可边界见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
