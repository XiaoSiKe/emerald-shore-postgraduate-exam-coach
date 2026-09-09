# RD：技术设计

## 架构

`SKILL.md` 是产品入口，负责场景路由、对话协议和教学纪律；`references/` 按哲学策略、效率评估、通俗讲解、情绪价值等场景加载；`emerald.py` 提供稳定的内部 CLI；`emerald_shore/` 负责状态、计划、专题、材料、逐题训练、效率快照、渲染和服务编排。运行时无网络依赖，Python 最低版本 3.9。

交互按三层组织：对话层识别当前任务并补齐一个关键未知；证据状态层通过公开命令读取或写入 `.emerald-shore/`；反馈层把 JSON 翻译为“当前判断—证据依据—下一动作—完成证据—回流方式”。CLI 失败时不伪造写入成功，允许给出明确标注为未持久化的临时建议。

## 状态所有权

用户工作区中的 `.emerald-shore/` 是唯一状态源：

- `profile.json`：版本、日期、目标院校/专业、工作日/周末时间、固定安排、睡眠底线、地点与缓冲比例。
- `subjects.json`：分数、科目代码、能力类型、成本和检查点历史。
- `topics.json`：章节、科目内专题权重、掌握度、证据置信度、成本和证据次数。
- `plan.json`：当前阶段、主攻科目/专题、排序和今日任务。
- `focus.json`：当前任务的时间、地点、if–then 启动句和障碍应对。
- `ledger.jsonl` / `mistakes.jsonl`：只追加的训练和错因历史。
- `review_queue.json`：复习状态和到期日。
- `sources.json` / `question_bank.json` / `materials/`：来源、来源题和派生文本。
- `today.md` / `dashboard.md` / `weekly.md`：由状态重新生成的视图。
- `efficiency.md`：由账本生成的多维效率视图，不保存或制造综合分。

JSON 文件使用临时文件、`fsync` 和 `os.replace` 原子更新。当前 schema 为 2。`migrate` 将 V0.1 `.qingan/` 复制到临时目录，升级 profile、计划和派生路径后原子提交为 `.emerald-shore/`；旧目录不删除。损坏状态不自动覆盖，返回 `corrupt_state`。

V0.4 新字段全部为 schema 2 的可选扩展。V0.2/V0.3 工作区没有 `routine`、目标院校、科目代码、章节或材料置信度时仍可读取；计划回退到原 `daily_hours`，新信息通过 `profile set`、`routine set`、`subject add`、`topic add` 和重新 `ingest` 补齐。

专题初次建档使用 `topic add`，大纲权重或新诊断证据变化后使用 `topic update`，随后显式 `replan`。不要求维护者或 Agent 直接修改 JSON。

## 计划算法

阶段由剩余天数决定。先按“得分缺口比例 × 考试权重 × 重复错误 × 前置影响 × 证据可信度”排序科目，再在主攻科目内按“专题权重 × 未掌握比例 × 证据可信度 × 重复错误”寻找最小突破口。只有同层全部提供成本时才除以成本平方根；否则标记保守估计，避免把未知成本误当成低成本。

每日容量优先使用 `routine.weekday_hours` 或 `routine.weekend_hours`，再乘 `60 × 0.85`；旧工作区没有 `routine` 时退回 `daily_hours`。存在到期复习时，先分配约 20% 给提取练习；其余以一个主攻和最多两个维持任务分配。任务 ID 由日期、角色和科目确定，重跑保持稳定。

## 复习和掌握

任务成功按 1、3、7、14、30 天递增；失败归零并次日复习。来源题使用独立 `question:<id>` 队列；专题任务使用 `topic:<id>`。三次成功后状态可变为 `mastered`，但 Skill 仍要求至少有一次限时或迁移证据。

## 材料

目录输入递归扫描，跳过隐藏目录、符号链接和 `.emerald-shore/`。SHA-256 去重。TXT/MD 支持 UTF-8、UTF-8 BOM、GB18030；HTML 去脚本和标签；DOCX/PPTX 直接读取 OOXML；PDF 使用可选 `pypdf`。提取文本存入 `.emerald-shore/materials/`，原文件只读。

每个来源记录 `evidence_level`、`classification_confidence` 与可选 `match_note`。低置信材料不能绑定科目/专题，中等置信材料不能绑定专题；`target_school_open` 必须已有目标院校、绑定科目并记录匹配依据。重复材料可以更新绑定；只有显式 `--replace-metadata` 才替换证据等级、置信度和匹配说明，并同步刷新派生 Markdown 头部，避免默认参数静默降级来源。

题目只从明确编号行提取并保留来源行号、科目与专题绑定。`drill` 优先到期题、历史错题、未做题，再选择已正确题；返回值主动移除 `answer`，但保留证据等级、归类置信度和匹配说明。`attempt` 更新题目历史、错因、复习队列，并以 0/0.5/1 观察值对专题掌握度做保守增量更新。

## 自我调节与周复盘

`focus` 要求可观察的时间/事件和地点，生成 5 分钟启动动作与可选 2 分钟障碍应对。`weekly` 只使用最近 7 天账本计算执行率、计划/实际分钟、闭卷或限时证据次数和错因分布，并据此重排。执行率低于 60% 时缩小任务，不补旧计划；没有证据事件时把下周第一目标改为可判定检查点。

## 效率评估

`efficiency --days N` 接受 1–90 天窗口。它从 `ledger.jsonl` 和 `mistakes.jsonl` 分别计算任务完成率、计划/实际任务分钟、来源题与检查点数量、答题结果分布、重复错因和同科检查点变化。

诊断按上游顺序选择一个：`insufficient_evidence`、`load_mismatch`、`input_heavy`、`accuracy_gap`、`recurring_error`、`checkpoint_missing`、`evidence_loop_stable`。返回 `principle=multi-dimensional-no-composite-score`，故意不提供 `overall_score`。不同维度量纲不同，强行加权会制造不可解释的精确感。

`weekly` 同时生成 `weekly.md` 与 `efficiency.md`，但保留原有周复盘字段，现有调用方无需迁移。

## 讲解与表达

通俗讲解和幽默属于 Skill 行为，不进入确定性引擎。`communication-style.md` 规定“一句话本质—生活类比—类比边界—考试落点—学生复述”，并限制普通回复最多一处轻量幽默。危机、安全和官方核验场景禁用幽默；表达变化不能降低来源、评分和掌握证据标准。

## 错误接口

成功 JSON 固定包含 `ok`、`command`、`workspace`、`updated_files`、`summary`、`next_action`、`warnings`。业务错误返回退出码 2 及 `code`、`message`、`recovery`、`details`；意外错误也包装为稳定 JSON，避免宿主只能解析 traceback。

JSON 是 Agent 与引擎之间的接口，不是默认面向学生的呈现格式。除非用户要求调试或导出，Skill 只呈现与当前决策有关的少量字段。

## 兼容与隐私

路径全部使用 `pathlib`，在 Linux、Windows、macOS 验证。发布 ZIP 只有一个 Skill 根目录。没有遥测、自动登录、浏览器 Cookie、云上传或材料复制到仓库的行为。
