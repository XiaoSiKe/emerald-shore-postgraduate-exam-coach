# RD：技术设计

## 架构

`SKILL.md` 负责场景路由和教学纪律；`references/` 只在对应场景加载；`qingan.py` 提供稳定 CLI；`qingan/` 负责状态、计划、材料、渲染和服务编排。运行时无网络依赖，Python 最低版本 3.9。

## 状态所有权

用户工作区中的 `.qingan/` 是唯一状态源：

- `profile.json`：版本、日期、每日时间、目标、缓冲比例。
- `subjects.json`：分数、能力类型、成本和检查点历史。
- `plan.json`：当前阶段、主攻、排序和今日任务。
- `ledger.jsonl` / `mistakes.jsonl`：只追加的训练和错因历史。
- `review_queue.json`：复习状态和到期日。
- `sources.json` / `question_bank.json` / `materials/`：来源、来源题和派生文本。
- `today.md` / `dashboard.md`：由状态重新生成的视图。

JSON 文件使用临时文件、`fsync` 和 `os.replace` 原子更新。当前 schema 为 1；未来迁移必须先复制旧状态到带时间戳的备份，再更新 `schema_version`。损坏状态不自动覆盖，返回 `corrupt_state`。

## 计划算法

阶段由剩余天数决定。科目排序使用：得分缺口比例 × 考试权重 × 重复错误修正 × 前置影响 × 证据可信度；用户提供预计达标小时后，再除以其平方根以避免极端值完全支配排序。缺少成本时标记 `partial-no-time-cost`，对外只称保守估计。

每日容量为 `daily_hours × 60 × 0.85`。存在到期复习时，先分配约 20% 给提取练习；其余以一个主攻和最多两个维持任务分配。任务 ID 由日期、角色和科目确定，重跑保持稳定。

## 复习和掌握

任务成功按 1、3、7、14、30 天递增；失败归零并次日复习。三次成功后状态可变为 `mastered`，但 Skill 仍要求至少有一次限时或迁移证据，脚本状态不能单独作为教学结论。

## 材料

目录输入递归扫描，跳过隐藏目录、符号链接和 `.qingan/`。SHA-256 去重。TXT/MD 支持 UTF-8、UTF-8 BOM、GB18030；HTML 去脚本和标签；DOCX/PPTX 直接读取 OOXML；PDF 使用可选 `pypdf`。提取文本存入 `.qingan/materials/`，原文件只读。

题目只从明确编号行提取并保留来源行号。没有答案时 `answer` 保持 `null`；任何 Agent 都不得把模型补充称为来源答案。

## 错误接口

成功 JSON 固定包含 `ok`、`command`、`workspace`、`updated_files`、`summary`、`next_action`、`warnings`。业务错误返回退出码 2 及 `code`、`message`、`recovery`、`details`；意外错误也包装为稳定 JSON，避免宿主只能解析 traceback。

## 兼容与隐私

路径全部使用 `pathlib`，在 Linux、Windows、macOS 验证。发布 ZIP 只有一个 Skill 根目录。没有遥测、自动登录、浏览器 Cookie、云上传或材料复制到仓库的行为。
