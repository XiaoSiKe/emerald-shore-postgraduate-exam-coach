# 来源审计

调研日期：2026-09-09。所有吸收内容均以原创文字和本项目接口重新实现。

| 来源 | 固定 commit | 许可证 | 吸收点 | 未采用 |
|---|---|---|---|---|
| ZeKaiNie/universal-examprep-skill | `20ed0633bd4923c516fa482bd0a627c190011381` | MIT | 本地资料、来源诚实、进度、CLI、测试与打包 | 完整代码、重型 benchmark、课程样例 |
| zgl610329-wq/learn-anything-fast | `49a6aef010e56da3b873847f872f490d10a483e5` | MIT | 学习契约、核心内容、一次一题、弱项、复述和校准 | “10x”效果表达、原模板文本 |
| cxs885187-create/--skill | `aa0467bd848ce40000e0bdd80667d4f24d946bc3` | README 声称 MIT，但无 `LICENSE` 文件且 GitHub License API 为 404 | 重点概念研究：单科聚焦、材料置信分流、课程骨架、目标院校公开资料匹配、专题卡、必要可视化、短轮自测、连续失败熔断、增量更新 | 全部原文、示例、模板、目录与代码均未复制；实现回到原始研究并针对考研原创重写 |
| Candlest/exam-prep-skill | `a6f6aa759c23c153f110053cc41f1bd12881bdd6` | MIT | 原始材料只读、逐题复习、教师材料优先 | 云 OCR 绑定和目录原文 |
| lhyvshh/exam-prep-agents-skill | `0eb7cdd18ca2be8f5038b0540ce7b9e5c62d8357` | MIT | 来源题、非重复、可恢复和确定性门禁 | 专业资格考试预设、分类器 |
| az9713/learn-anything-skill | `5566f4376b9a976437835a3da3c8dda8e5c2c363` | MIT | 缺口拆解、复述、预测—测试—比较 | 子 Skill 运行依赖和原状态模板 |
| XiaomiMiMo/MiMo-Code | `4f44dab00ac2eeae377a0c4000a1cc0987eb3fb6`（目标文件最近提交） | MIT | 增量教学、跨会话状态、掌握看迁移 | 宿主专用实现 |
| HughYau/qiushi-skill | `3d36c1471081d0cedce248836522c6e845f9b516` | MIT | 调查、主要矛盾、集中、实践、阶段纠错 | 插件、hooks、原著摘录和政治化表达 |
| leezythu/maoxuan-skill | `4376a65020b1fd96af65052ccd30accaddedc3f1` | MIT | 作为策略模型交叉参考 | 人物模拟、表达 DNA、原话 |
| mohitagw15856/pm-claude-skills · exam-study-plan | `5a0326ce34b44c015fc26b5c28f6118092c806e4` | MIT | 逆向排期、权重与弱项共同排序、最后阶段收束 | 原文模板和庞大插件系统 |
| mohitagw15856/pm-claude-skills · explain-simply / feynman-explainer | `648c57dd75ad081bbb6858af836b937d096456a5` / `a9668c72e56ce30214dd4a419939b1ca6e7a4d4c`（目标文件最后提交） | MIT | 一句话本质、分层解释、类比边界、学生先讲、含糊与术语遮挡检查 | 通用领域模板、固定输出措辞与“12 岁标准”原文 |
| LeoYeAI/openclaw-master-skills · study-buddy-ai | `fd6c8c403eba42b1bb765dd79ff2160d2a74eb4f`（目标文件最后提交） | MIT | 本地学习数据、即时反馈、弱项提示、具体庆祝与亲和语气 | 22 功能大菜单、固定 Pomodoro、连胜压力、积分和花哨游戏化 |
| MengTo/Skills · audit-verify-explain-grade-5 | `a3d017f3cf1b9e04695be434593d66b2ed1ae900`（目标文件最后提交） | MIT | 先审计与核验证据，再向聪明新人解释 | 通用审计流程和固定表达模板 |
| open-spaced-repetition/py-fsrs · README | `81765cf8eb6ebb422ce36194372074fb0c8a08b2` | MIT | 复习评分、可提取概率、日志足够后再优化的边界 | 运行依赖、参数和算法代码 |
| 24kchengYe/human-skill-tree · learning-how-to-learn | `50cb585c5186c05ed4b6c5d4df2ca34476379064` | Skill 文件可选 MIT | 方法与任务匹配、反熟悉感、具体进步反馈 | Web 应用与 AGPL 代码 |
| GarethManning/education-agent-skills | `6bbbce418f82e11044009c9f3b7373a354de5bd0` | CC BY-SA 4.0 | 仅作 SRL、周度能动性、动机诊断、错误分析和理解检查的研究线索，回到原始论文独立设计 | 未复制或改编任何 Skill 文字、模板与结构 |

实施时不得从无许可证来源复制可版权化表达；`sources.lock.json` 是上游版本核验的机器可读权威记录。

## 重点蒸馏：cxs885187-create/--skill

该来源面向大学期末突击，本项目没有直接移植，而是做了以下考研化转换：

| 来源机制线索 | 考研场景中的深化 | 本项目落点 |
|---|---|---|
| 一次处理一门课 | 多科考研不能永久单科化，因此改为“一周一个主攻 + 最多两个维持” | `planner.py`、`strategy-methods.md` |
| 先问考试时间 | 由 7 天/3 天/24 小时短模式扩展为 1–4 个月四阶段，并结合工作日/周末校园容量 | `planner.py`、`campus-life-system.md` |
| 材料归档 | 不移动原文件，改为高/中/低置信状态分流；低置信不得绑定科目 | `materials.py`、`course-evidence-system.md` |
| 课程骨架 | 从课程—章节—主题扩展为科目—章节—专题—来源题，并接入得分地图 | `topic add --chapter`、`topics.json` |
| 学校定向资料 | 从期末课程匹配改为目标院校、专业、科目代码、材料类型和年份的可追溯匹配 | `target_school_open`、`--match-note` |
| 专题卡与图示 | 卡片必须支持闭卷、方法选择、错因和自测；图示只解决空间/关系障碍 | `output-templates.md`、`learning-science.md` |
| 自测与自评 | 保留一次一题，并将结果写入掌握度、错因和复习队列 | `drill`、`attempt` |
| 连续不会停止加题 | 改为连续三次失败熔断：先最小重建，再用替代题复测 | `course-evidence-system.md`、静态行为契约 |
| 增量更新 | SHA-256 去重；新证据只更新绑定、置信度和受影响的专题 | `materials.py`、`sources.json` |

许可证边界：2026-09-09 复核 commit `aa0467bd848ce40000e0bdd80667d4f24d946bc3` 时，根目录只有 README 与 Skill 子目录，没有 MIT 许可证全文。最后一次 commit 仅把 README 中的“建议 MIT”改成“仓库使用 MIT”。这不足以让本项目复制可版权化内容，因此机器策略继续保持 `concept-only-no-copy`。

## V0.5 讲解、效率与情绪机制蒸馏

| 来源机制 | 考研化改写 | 主动拒绝 |
|---|---|---|
| explain-simply 的分层解释与类比边界 | 一句话本质—生活类比—失真点—考试落点 | 固定通用模板、与考题无关的展开 |
| feynman-explainer 的学生复述与含糊检查 | 学生先讲，定位含糊/循环/术语遮挡，再重讲和迁移 | 用“能讲给孩子”作为唯一掌握标准 |
| study-buddy 的本地记录、即时反馈与轻松语气 | 具体庆祝真实进步、轻量幽默、数据仍留本地 | 连胜压力、积分刺激、固定 Pomodoro 与 22 功能菜单 |
| weekly-agency-review 的数据解释顺序 | 效率面板先给学生，学生先发现模式，再共同定策略目标 | 让 AI 直接替学生完成全部反思 |
| motivation diagnostic 的自主、胜任与关系检查 | 拖延时调整选择、挑战和合作关系，不贴“懒”标签 | 为了有趣降低考试训练标准 |
| audit-verify-explain-grade-5 的证据优先 | 先读账本和检查点，再用新人能听懂的语言解释 | 没核验就先给漂亮结论 |

以上 Skill 提供行为线索；最终规则由本项目按考研证据接口重新设计。GarethManning/education-agent-skills 为 CC BY-SA 4.0，本项目未复制或改写其文字与结构，只依据其研究线索回到原始论文。

## 学习科学

- Dunlosky et al. (2013), DOI `10.1177/1529100612453266`。
- Carpenter, Pan & Butler (2022), DOI `10.1038/s44159-022-00089-1`。
- Weinstein, Sumeracki & Caviglioli (2018), DOI `10.1186/s41235-017-0087-y`。
- Zimmerman (2002), DOI `10.1207/S15430421TIP4102_2`：计划、执行监控、自我反思的循环。
- Panadero (2017), DOI `10.3389/fpsyg.2017.00422`：自我调节学习模型综述及认知、动机、情绪维度。
- Gollwitzer (1999), DOI `10.1037/0003-066X.54.7.493`：把具体情境与目标行为连接成 implementation intention。
- Sweller (1988), DOI `10.1207/s15516709cog1202_4`：问题解决中的认知负荷；用于控制同时处理量和连续失败后的题量。
- Shah, Friedman & Kruglanski (2002), DOI `10.1037/0022-3514.83.6.1261`：目标屏蔽；仅支持减少竞争目标干扰，不等于长期放弃其他科目。
- Biggs (1996), DOI `10.1007/BF00138871`：建构性对齐；用于让范围、训练活动和验收证据一致。
- Black & Wiliam (1998), DOI `10.1080/0969595980050102`：形成性评价；用于根据自测证据调整下一步。
- Mayer (2003), DOI `10.1016/S0959-4752(02)00016-6`：多媒体学习；用于约束图示必须服务理解而非装饰。
- Ryan & Deci (2000), DOI `10.1037/0003-066X.55.1.68`：自主、胜任和关系需要；用于检查任务与反馈条件，不诊断人格。
- Bandura (1977), DOI `10.1037/0033-295X.84.2.191`：自我效能；用于强调真实成功经验，而不是空泛劝说。
- Ericsson, Krampe & Tesch-Römer (1993), DOI `10.1037/0033-295X.100.3.363`：有目标、带反馈的刻意练习；不把单纯时长当效率。
- Banas et al. (2011), DOI `10.1080/03634523.2010.496867`：教学幽默研究综述；用于约束幽默与学习目标、关系安全和场景适配，不承诺幽默必然提分。

研究结论被转译成行为规则，不复制论文图表或长段文字。效果为群体层面证据，不构成个人提分保证。

## 经典方法来源

使用《实践论》《矛盾论》《反对本本主义》《论持久战》等公开著作中的一般方法概念，并参考实用主义的结果检验、斯多葛传统中的控制边界与波普尔式可证伪假设。项目不收录原著全文、长篇摘录或人物角色扮演；这些思想只用来形成可检验的决策工具，并同时写入失效条件和防误用边界。
