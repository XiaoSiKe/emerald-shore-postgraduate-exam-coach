# V0.4.0 评测报告

评测日期：2026-09-09。

## 本地自动化结果

- 完整依赖环境：安装可选 `pypdf` 后，38/38 项单元与集成测试通过。
- Skill 专用校验：通过；覆盖 frontmatter、名称、必需文件、按需 reference、本地链接、中文主文档、公开标识和来源锁定。
- 通用 Agent Skills validator：通过。
- 静态行为契约：34/34，通过率 100%；来源、隐私、安全、不承诺、迁移、不泄露答案、通用适配、材料分流、目标院校证据、自测熔断与战略放弃边界关键项 17/17。
- Skills CLI：在隔离临时 Git 项目中成功发现并安装 `emerald-shore-postgraduate-exam-coach`。
- README：通过 GitHub GFM 接口渲染，标题、口号、3 个表格、折叠说明与本地链接结构正常。
- 发布包：两次构建 SHA-256 一致，ZIP 只有 `emerald-shore-postgraduate-exam-coach/` 一个根目录，共 31 个文件。
- 安装冒烟：解压后 `--version → init → routine set → subject add → topic add → target_school_open ingest → plan → drill → focus → weekly` 全部通过，版本返回 `0.4.0`。

本地发布包 SHA-256：

```text
a1b4764259e3a0dfc43baa13829da2116204de948f2f6fc203d721ad6a9376a8
```

## V0.4.0 新增验证面

- 工作日和周末容量分别计算，固定课程/实习、睡眠底线和地点锚点进入计划上下文。
- V0.2/V0.3 工作区缺少新可选字段时退回原 `daily_hours`，无需 schema 迁移。
- 目标院校公开资料必须已有目标院校、绑定科目并记录 `--match-note`；低置信材料不能直接绑定科目/专题。
- 默认重复建库不会静默改写证据等级；只有显式 `--replace-metadata` 才更新来源元数据与派生 Markdown 头部。
- 科目代码、章节层级、目标院校证据和归类置信度能从 CLI 进入持久状态并在 `drill` 中回显。
- Skill 明文约束覆盖课程骨架、专题卡、必要可视化、连续三次失败熔断、增量更新和战略放弃边界。

## 重点来源复核

`cxs885187-create/--skill` 固定在 commit `aa0467bd848ce40000e0bdd80667d4f24d946bc3`。仓库 README 声称 MIT，但根目录没有 `LICENSE` 文件，GitHub License API 返回 404。因此本轮只蒸馏抽象功能机制与理论问题，未复制其文字、示例、模板、目录或代码。

## 云端验证

- [PR #6](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/pull/6) 的 Windows Python 3.9/3.12、Ubuntu Python 3.9/3.12、macOS Python 3.12 与增强安装包冒烟全部通过。
- [pull_request CI 34357908577](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/actions/runs/34357908577) 与 [push CI 34357900466](https://github.com/XiaoSiKe/emerald-shore-postgraduate-exam-coach/actions/runs/34357900466) 共 12 个 checks 全部成功。

## 未自动化范围

固定场景验证的是 Skill 明文行为契约，不冒充真实模型对话评测。V0.4.0 尚未绑定某个模型供应商的可重复实时模型评测；不同模型是否始终遵守一次一问、一次一题、来源诚实、校园约束、自测熔断和情绪边界，仍需后续持续采样。确定性本地引擎、跨平台测试和发布包不依赖模型供应商。
