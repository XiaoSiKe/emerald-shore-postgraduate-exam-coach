# 运营与迭代

## 版本

使用语义化版本。行为兼容修复增加 patch；新增能力增加 minor。1.0 之前的不兼容标识或状态变更增加 minor 并必须提供迁移说明；1.0 之后此类变更增加 major。每次发布更新 `CHANGELOG.md`。

## 发布门禁

1. `python -m unittest discover -s tests -v`
2. `python scripts/validate_skill.py .`
3. `python scripts/run_static_eval.py`
4. `python scripts/build_release.py --check`
5. 使用通用 Agent Skills validator 校验 `SKILL.md` frontmatter、命名和目录结构。
6. 解压 ZIP 后运行 `--version`、`init --target-school`、`routine set`、`subject add --code`、`topic add --chapter`、目标院校证据 `ingest`、`drill`、`plan`、`weekly` 冒烟流程。
7. 用一份真实 V0.1 fixture 运行 `migrate`，确认旧目录保留、schema 2 可继续计划。
8. 在临时目录验证 Skills CLI 能发现并安装 `emerald-shore-postgraduate-exam-coach`，不得污染维护者的全局 Skill 目录。

关键行为、安全、隐私、来源诚实必须全部通过；静态行为评测总分至少 90%。未运行真实模型评测时必须在报告中写明，不能把静态检查冒充真实对话结果。

## 反馈

Issue 分为 Bug、功能建议、方法来源更新。Bug 要求提供命令、脱敏后的 JSON 错误、Python/系统版本和预期；禁止上传课程版权材料或个人信息。

用户可见说明、Issue 表单和 Actions 步骤默认使用中文；Skill 名、仓库名、命令、参数、JSON 字段、许可证、论文与项目专名保留英文。README 必须优先说明这是 Agent Skill，再介绍本地证据引擎，避免被误解为独立 App。

## 上游更新

`sources.lock.json` 固定调研 commit。每月 GitHub Action 运行 `scripts/check_upstreams.py` 并上传 JSON 报告，不自动修改仓库、不自动复制上游变化。维护者审查许可证、行为价值和回归风险后再创建 PR。

来源 README 自称某许可证但仓库缺少许可证全文时，仍按未确认许可证处理：只研究抽象机制，禁止复制文字、模板、目录和代码。许可证声明、GitHub License API 与实际文件三者不一致时，在来源审计中保留证据。

## 运营指标

只使用 GitHub Stars、Release 下载、Issues 和用户自愿提交的脱敏评测。禁止在 Skill 内加入遥测。优先修复来源错误、迁移失败、状态损坏、计划超量、专题误排和泄露答案；不以功能数量为迭代目标。
