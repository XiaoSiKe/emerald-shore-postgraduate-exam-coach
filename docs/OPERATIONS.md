# 运营与迭代

## 版本

使用语义化版本。行为兼容修复增加 patch；新增可选命令增加 minor；状态或 CLI 不兼容变更增加 major，并提供迁移说明。每次发布更新 `CHANGELOG.md`。

## 发布门禁

1. `python -m unittest discover -s tests -v`
2. `python scripts/validate_skill.py .`
3. `python scripts/run_static_eval.py`
4. `python scripts/build_release.py --check`
5. 解压 ZIP 后在临时目录运行 `--version`、`init`、`subject add`、`plan`、`today` 冒烟流程。

关键行为、安全、隐私、来源诚实必须全部通过；静态行为评测总分至少 90%。未运行真实模型评测时必须在报告中写明，不能把静态检查冒充真实对话结果。

## 反馈

Issue 分为 Bug、功能建议、方法来源更新。Bug 要求提供命令、脱敏后的 JSON 错误、Python/系统版本和预期；禁止上传课程版权材料或个人信息。

## 上游更新

`sources.lock.json` 固定调研 commit。每月 GitHub Action 运行 `scripts/check_upstreams.py` 并上传 JSON 报告，不自动修改仓库、不自动复制上游变化。维护者审查许可证、行为价值和回归风险后再创建 PR。

## 运营指标

只使用 GitHub Stars、Release 下载、Issues 和用户自愿提交的脱敏评测。禁止在 Skill 内加入遥测。优先修复来源错误、状态损坏、计划超量和泄露答案；不以功能数量为迭代目标。
