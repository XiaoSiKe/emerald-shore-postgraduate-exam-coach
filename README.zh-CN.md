# 青岸计划·考研冲刺教练

一个面向考研最后 1–4 个月的开源 Agent Skill。它把考试日期、各科差距、真实资料、错题和限时成绩变成可追踪的冲刺系统：调查现状、抓主要矛盾、集中训练、实践检验、动态复盘。

它不会押题、承诺上岸，也不会把重读笔记当成掌握。

## 能做什么

- 为不同专业和科目建立统一冲刺档案。
- 自动计算冲刺阶段、每日容量、周主攻和维持任务。
- 本地解析 PDF、DOCX、PPTX、TXT、Markdown、HTML，并保留来源。
- 记录训练、错因、复习队列和限时检查点。
- 根据成绩和执行率动态重排，而不是维护一张失真的长期日历。
- 在拖延和焦虑时把计划降到一个真实可启动的动作。

## 安装

下载 Release 中的 `qingan-kaoyan-coach-v0.1.0.zip`，解压后将整个 `qingan-kaoyan-coach/` 文件夹放入支持 Agent Skills 的技能目录。也可以克隆仓库后直接使用根目录。

运行时需要 Python 3.9+。文本、DOCX、PPTX 和 HTML 只使用标准库；PDF 文字提取建议安装：

```bash
python -m pip install pypdf
```

## 快速开始

```bash
python qingan.py init ~/kaoyan-2027 --exam-date 2026-12-20 --daily-hours 6
python qingan.py subject add ~/kaoyan-2027 --name 数学 --max-score 150 --baseline 70 --target 110 --kind calculation --estimated-hours 180
python qingan.py subject add ~/kaoyan-2027 --name 英语 --max-score 100 --baseline 55 --target 70 --kind language
python qingan.py plan ~/kaoyan-2027
python qingan.py today ~/kaoyan-2027
```

所有学习数据只保存在学习工作区的 `.qingan/`。原始资料不会被移动或上传。

## 证据边界

用户材料、真题、官方资料和外部讲解使用不同证据等级。没有材料时可以生成明确标注的 AI 练习题，但不会冒充真题、老师重点或目标院校预测。

完整需求、技术设计、来源审计和运营方式见 `docs/`。

## License

MIT。第三方来源与许可见 `THIRD_PARTY_NOTICES.md` 和 `docs/SOURCE_AUDIT.md`。
