# V0.2.0 评测报告

评测日期：2026-09-09。

## 自动化结果

- 本地：30 项测试中 29 项通过；仅因主环境未安装可选 `pypdf` 跳过 1 项。该 PDF 文本分支在隔离环境安装 `pypdf` 后单独通过。
- GitHub Actions：Windows 3.9/3.12、Ubuntu 3.9/3.12、macOS 3.12 全部通过；每个环境安装 `pypdf` 后执行 30 项测试。
- 发布包：两次构建 SHA-256 一致，ZIP 只有 `emerald-shore-postgraduate-exam-coach/` 一个根目录。
- 安装冒烟：解压后 `--version`、`init`、`subject add`、`topic add`、`plan`、`weekly` 全部通过。
- 静态行为契约：19/19，通过率 100%；来源、隐私、安全、不承诺、迁移与不泄露答案关键项 10/10。
- 上游锁定：13 个来源均能按仓库或目标文件 commit 复核，无未解释漂移。
- 端到端：专题建档、材料绑定、来源题、答题回流、启动协议和周复盘通过；真实 V0.1.0 fixture 迁移后旧目录保留、schema 2 可继续运行。

证据：[PR #4](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/pull/4)、[PR CI 34331857669](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/actions/runs/34331857669)、[分支 CI 34331813675](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/actions/runs/34331813675)。GitHub 仓库改名后，旧链接由 GitHub 自动重定向。

## 修复记录

V0.2.0 将公开标识、CLI、Python 包和发布包统一为 Emerald Shore 英文命名；新增非破坏迁移、专题排序、来源题闭环、周复盘和 if–then 启动。重复材料重新绑定会返回明确摘要，专题权重与证据可通过正式接口更新。

## 未自动化范围

固定场景验证的是 Skill 明文行为契约，不冒充真实模型对话评测。V0.2.0 尚未绑定某个模型供应商的可重复 live-eval；不同模型是否始终遵循“一次一题、来源诚实和情绪边界”仍需在后续版本持续采样。确定性 CLI、跨平台行为和发布包不依赖模型。
