# 来源审计

调研日期：2026-09-09。所有吸收内容均以原创文字和本项目接口重新实现。

| 来源 | 固定 commit | 许可证 | 吸收点 | 未采用 |
|---|---|---|---|---|
| ZeKaiNie/universal-examprep-skill | `20ed0633bd4923c516fa482bd0a627c190011381` | MIT | 本地资料、来源诚实、进度、CLI、测试与打包 | 完整代码、重型 benchmark、课程样例 |
| zgl610329-wq/learn-anything-fast | `49a6aef010e56da3b873847f872f490d10a483e5` | MIT | 学习契约、核心内容、一次一题、弱项、复述和校准 | “10x”效果表达、原模板文本 |
| cxs885187-create/--skill | `aa0467bd848ce40000e0bdd80667d4f24d946bc3` | 无许可证 | 仅抽象概念：课程骨架、证据分级、紧迫模式 | 全部原文、模板和代码均未复制 |
| Candlest/exam-prep-skill | `a6f6aa759c23c153f110053cc41f1bd12881bdd6` | MIT | 原始材料只读、逐题复习、教师材料优先 | 云 OCR 绑定和目录原文 |
| lhyvshh/exam-prep-agents-skill | `0eb7cdd18ca2be8f5038b0540ce7b9e5c62d8357` | MIT | 来源题、非重复、可恢复和确定性门禁 | 专业资格考试预设、分类器 |
| az9713/learn-anything-skill | `5566f4376b9a976437835a3da3c8dda8e5c2c363` | MIT | 缺口拆解、复述、预测—测试—比较 | 子 Skill 运行依赖和原状态模板 |
| XiaomiMiMo/MiMo-Code | `4f44dab00ac2eeae377a0c4000a1cc0987eb3fb6`（目标文件最近提交） | MIT | 增量教学、跨会话状态、掌握看迁移 | 宿主专用实现 |
| HughYau/qiushi-skill | `3d36c1471081d0cedce248836522c6e845f9b516` | MIT | 调查、主要矛盾、集中、实践、阶段纠错 | 插件、hooks、原著摘录和政治化表达 |
| leezythu/maoxuan-skill | `4376a65020b1fd96af65052ccd30accaddedc3f1` | MIT | 作为策略模型交叉参考 | 人物模拟、表达 DNA、原话 |
| mohitagw15856/pm-claude-skills · exam-study-plan | `5a0326ce34b44c015fc26b5c28f6118092c806e4` | MIT | 逆向排期、权重与弱项共同排序、最后阶段收束 | 原文模板和庞大插件系统 |
| open-spaced-repetition/py-fsrs · README | `81765cf8eb6ebb422ce36194372074fb0c8a08b2` | MIT | 复习评分、可提取概率、日志足够后再优化的边界 | 运行依赖、参数和算法代码 |
| 24kchengYe/human-skill-tree · learning-how-to-learn | `50cb585c5186c05ed4b6c5d4df2ca34476379064` | Skill 文件可选 MIT | 方法与任务匹配、反熟悉感、具体进步反馈 | Web 应用与 AGPL 代码 |
| GarethManning/education-agent-skills | `6bbbce418f82e11044009c9f3b7373a354de5bd0` | CC BY-SA 4.0 | 仅作 SRL/if–then 研究线索，回到原始论文独立设计 | 未复制或改编任何 Skill 文字、模板与结构 |

实施时不得从无许可证来源复制可版权化表达；`sources.lock.json` 是上游版本核验的机器可读权威记录。

## 学习科学

- Dunlosky et al. (2013), DOI `10.1177/1529100612453266`。
- Carpenter, Pan & Butler (2022), DOI `10.1038/s44159-022-00089-1`。
- Weinstein, Sumeracki & Caviglioli (2018), DOI `10.1186/s41235-017-0087-y`。
- Zimmerman (2002), DOI `10.1207/S15430421TIP4102_2`：计划、执行监控、自我反思的循环。
- Panadero (2017), DOI `10.3389/fpsyg.2017.00422`：自我调节学习模型综述及认知、动机、情绪维度。
- Gollwitzer (1999), DOI `10.1037/0003-066X.54.7.493`：把具体情境与目标行为连接成 implementation intention。

研究结论被转译成行为规则，不复制论文图表或长段文字。效果为群体层面证据，不构成个人提分保证。

## 经典方法来源

使用《实践论》《矛盾论》《反对本本主义》《论持久战》等公开著作中的一般方法概念。项目不收录原著全文、长篇摘录或人物角色扮演；方法同时写入失效条件和历史纠错边界。
