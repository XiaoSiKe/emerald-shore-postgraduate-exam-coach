# V0.5.0 评测报告

评测日期：2026-09-09。

## 本地自动化结果

- 完整依赖环境：安装可选 `pypdf` 后，46/46 项单元与集成测试通过。
- 主环境：46 项中 45 项通过，1 项因未安装可选 `pypdf` 跳过；完整依赖环境已覆盖该分支。
- Skill 专用校验与通用 Agent Skills validator：通过。
- 静态行为契约：42/42，通过率 100%；关键项 21/21。
- README：通过 GitHub GFM 接口渲染；四层十一系统、哲学/效率/情绪模块、3 个表格、折叠说明和链接均正常。
- 发布包：两次构建 SHA-256 一致，ZIP 只有一个 Skill 根目录，共 33 个文件。
- Skills CLI：已在隔离 Git 目录成功发现并安装；发布后按用户要求进行本机全局安装。
- 上游锁定：使用认证后的 GitHub API 复核 17 条仓库/目标文件记录，全部与固定 commit 一致，无漂移或请求错误。

本地发布包 SHA-256：

```text
398413602bcd70d970b0745a10be919f1f15b5489fbd8eb329a657cb8d0279d7
```

## V0.5.0 新增验证面

- `efficiency` 对 1–90 天窗口生成执行、有效证据、答题结果、错因复发和检查点变化，不包含 `overall_score`。
- 覆盖证据不足、容量错配、输入偏重、正确率缺口、错因复发、缺少检查点和证据闭环稳定七类诊断。
- `weekly` 同时生成效率快照与 `efficiency.md`；`status` 返回七日效率诊断，同时保留原字段。
- 哲学策略约束调查、主要矛盾、集中力量、实践检验、阶段调整、控制边界与可证伪计划。
- 通俗讲解约束一句话本质、生活类比、类比边界、考试落点、学生复述和迁移。
- 情绪价值覆盖自主感、胜任感、关系感、具体表扬和危机边界；幽默限制为普通场景最多一处，禁止嘲笑学生。

## 新来源复核

- `mohitagw15856/pm-claude-skills` 的 explain-simply 与 feynman-explainer：MIT。
- `LeoYeAI/openclaw-master-skills` 的 study-buddy-ai：MIT。
- `MengTo/Skills` 的 audit-verify-explain-grade-5：MIT。
- `GarethManning/education-agent-skills`：CC BY-SA 4.0，仅作研究线索，未复制或改编文字与结构。

## 云端与本地安装验证

PR 创建前不预写尚未发生的 GitHub Actions、Release 或全局安装结果。合并与发布前补充实际证据；Release 回下载通过 SHA-256 后再更新本机全局 Skill。

## 未自动化范围

固定场景验证的是 Skill 明文行为契约，不冒充真实模型对话评测。V0.5.0 尚未绑定某个模型供应商的可重复实时模型评测；幽默是否恰当、类比是否真正帮助某位学生理解，仍需真实会话采样。确定性引擎、跨平台测试和发布包不依赖模型供应商。
