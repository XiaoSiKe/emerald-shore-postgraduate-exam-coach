# V0.3.0 评测报告

评测日期：2026-09-09。

## 本地自动化结果

- 完整依赖环境：安装可选 `pypdf` 后，32/32 项单元与集成测试通过。
- 主环境：32 项中 31 项通过；只因未安装可选 `pypdf` 跳过 1 项，与完整依赖环境结果一致。
- Skill 专用校验：通过；覆盖 frontmatter、名称、必需文件、按需 reference、本地链接、中文主文档、公开标识和来源锁定。
- 通用 Agent Skills validator：通过。
- 静态行为契约：24/24，通过率 100%；来源、隐私、安全、不承诺、迁移、不泄露答案、Skill 定位与持久化诚实关键项 12/12。
- Skills CLI：在隔离临时 Git 项目中成功发现并安装 `emerald-shore-postgraduate-exam-coach`，`npx skills list --json` 能返回项目级 Skill。
- 发布包：两次构建 SHA-256 一致，ZIP 只有 `emerald-shore-postgraduate-exam-coach/` 一个根目录，共 29 个文件。
- 安装冒烟：解压后 `--version → init → subject add → topic add → plan → weekly` 全部通过，版本返回 `0.3.0`。

本地发布包 SHA-256：

```text
51b3c0ca15b82135f25ee8987e3afebcb0ae5efa7c9796cf9b60a44b7dec84ff
```

## V0.3.0 新增验证面

- 中文是用户可见主语言，命令、参数、JSON 字段和必要技术标识仍保持兼容。
- 项目被明确呈现为对话驱动的 Agent Skill，本地引擎不会取代对话入口。
- 首次诊断一次只补一个会改变计划的未知，并复用用户已经提供的信息。
- 引擎结果会被翻译为“当前判断—依据—下一动作—完成证据—回流方式”，不默认倾倒原始 JSON。
- CLI 不可用或命令失败时，Skill 必须说明本次结果尚未持久化，不能假装已经建档或重排。
- 中文 CLI 帮助、校验输出和静态评测显式使用 UTF-8，跨进程测试也按 UTF-8 解码，避免 Windows `cp1252` 编码失败。
- Release 包含新编排协议 `references/coach-orchestration.md`。

## 云端验证

- [PR #5](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/pull/5) 的 Windows Python 3.9/3.12、Ubuntu Python 3.9/3.12、macOS Python 3.12 与安装包冒烟全部通过。
- [pull_request CI 34345766878](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/actions/runs/34345766878) 与 [push CI 34345763148](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/actions/runs/34345763148) 共 12 个 checks 全部成功。
- 首轮云端测试发现 Windows `cp1252` 无法输出中文帮助与校验信息；修复为显式 UTF-8 后，同一矩阵全部通过。失败没有被隐藏或降级为英文输出。

## 未自动化范围

固定场景验证的是 Skill 明文行为契约，不冒充真实模型对话评测。V0.3.0 尚未绑定某个模型供应商的可重复实时模型评测；不同模型是否始终遵循“一次一问、一次一题、来源诚实、中文反馈和情绪边界”仍需在后续版本持续采样。确定性本地引擎、跨平台测试和发布包不依赖模型供应商。
