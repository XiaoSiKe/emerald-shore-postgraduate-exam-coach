# 青岸计划 · Emerald Shore Initiative

**Postgraduate Entrance Exam Sprint Coach｜硕士研究生招生考试冲刺教练**

一个面向考研最后 1–4 个月的开源 Agent Skill。它把考试日期、科目与专题差距、真实资料、来源题、错因和限时成绩变成可追踪的冲刺系统：调查现状、抓主要矛盾、集中训练、实践检验、周度复盘。

它不会押题、承诺上岸，也不会把重读笔记当成掌握。

## 能做什么

- 为不同专业和科目建立统一冲刺档案。
- 自动计算冲刺阶段、每日容量、周主攻和维持任务。
- 在科目下建立专题得分地图，用权重、掌握度、证据置信度和错误记录寻找最小突破口。
- 本地解析 PDF、DOCX、PPTX、TXT、Markdown、HTML，并保留来源。
- 将材料绑定到科目/专题，一次选择一道来源题，作答前不泄露答案。
- 记录训练、逐题结果、错因、复习队列和限时检查点。
- 用 `weekly` 执行“计划—监控—反思”，用 `focus` 把目标转换成具体 if–then 启动协议。
- 根据成绩和执行率动态重排，而不是维护一张失真的长期日历。
- 在拖延和焦虑时把计划降到一个真实可启动的动作。

## 安装

下载 Release 中的 `emerald-shore-postgraduate-exam-coach-v0.2.0.zip`，解压后将整个 `emerald-shore-postgraduate-exam-coach/` 文件夹放入支持 Agent Skills 的技能目录。也可以克隆仓库后直接使用根目录。

运行时需要 Python 3.9+。文本、DOCX、PPTX 和 HTML 只使用标准库；PDF 文字提取建议安装：

```bash
python -m pip install pypdf
```

## 快速开始

```bash
python emerald.py init ~/postgraduate-exam --exam-date 2026-12-20 --daily-hours 6
python emerald.py subject add ~/postgraduate-exam --name 数学 --max-score 150 --baseline 70 --target 110 --kind calculation --estimated-hours 180
python emerald.py subject add ~/postgraduate-exam --name 英语 --max-score 100 --baseline 55 --target 70 --kind language
python emerald.py topic add ~/postgraduate-exam --subject 数学 --name 微积分 --weight 3 --mastery 0.35 --confidence 0.7
python emerald.py topic update ~/postgraduate-exam --subject 数学 --name 微积分 --mastery 0.45 --confidence 0.9
python emerald.py ingest ~/postgraduate-exam ./数学真题.pdf --evidence-level past_paper --subject 数学 --topic 微积分
python emerald.py plan ~/postgraduate-exam
python emerald.py today ~/postgraduate-exam
python emerald.py drill ~/postgraduate-exam --subject 数学 --topic 微积分
python emerald.py weekly ~/postgraduate-exam
```

所有学习数据只保存在学习工作区的 `.emerald-shore/`。原始资料不会被移动或上传。

### 从 V0.1.0 升级

如果旧工作区含 `.qingan/`，运行：

```bash
python emerald.py migrate WORKSPACE
```

系统会复制并升级到 `.emerald-shore/`，旧目录保持不变，可随时回退。

## 证据边界

用户材料、真题、官方资料和外部讲解使用不同证据等级。没有材料时可以生成明确标注的 AI 练习题，但不会冒充真题、老师重点或目标院校预测。

完整需求、技术设计、来源审计和运营方式见 `docs/`。

## License

MIT。第三方来源与许可见 `THIRD_PARTY_NOTICES.md` 和 `docs/SOURCE_AUDIT.md`。
