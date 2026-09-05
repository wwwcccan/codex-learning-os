# codex-learning-os 修改验收报告

## 1. 执行日期与基线

- 执行日期：2026-09-05（Asia/Shanghai）
- 依据：工作区中的 `modification-plan.md`，不是 Git HEAD。
- 开始前状态：工作树已有大量用户未提交修改、删除和 14 份未跟踪论文 PDF；`SPEC.md`
  与 `modification-plan.md` 也是开始前已存在的未跟踪文件。已有修改涉及 `.gitignore`、
  `AGENTS.md`、`README.md`、四个模板、`.gitkeep` 文件，以及旧 CLI、源码、测试、架构
  文档等删除。
- 开始前实际盘点：`Concepts/`、`Mistakes/`、`Sessions/` 中只有 `.gitkeep`，没有真实
  学习笔记；`Papers/` 中有 14 份 PDF，没有 Markdown 论文笔记。
- 保护措施：修改前将本轮 8 个目标文档保存到工作区外的
  `/private/tmp/clos-modification-baseline.rSVjT2`，验收后已清理该临时副本；使用逐文件补丁，
  没有 reset、checkout、clean、commit 或 push。

## 2. 实际修改文件

| 文件 | 实际用途 |
|---|---|
| `SPEC.md` | 固定 browse/learn/assess、四类证据、正式 A0、掌握门槛、暂停恢复、论文来源与 blocker、复习、兼容和回退规则。 |
| `.agents/skills/ai-tutor/SKILL.md` | 将上述语义落成 Tutor 的读取、帮助、测评、写入、复用错误和恢复顺序；保留 SPEC 作为定义来源。 |
| `Templates/concept.md` | 使用未评估 `null` 默认值，增加 Learning Target、Evidence 和 Next Practice。 |
| `Templates/session.md` | 增加 `mode`、暂停检查点和可选关键学习证据，保留原始五个摘要栏目。 |
| `Templates/paper.md` | 增加 Source 与 Claims / Evidence / Verification，合并 blocker 栏目，保留唯一 `next_action`。 |
| `Templates/mistake.md` | 增加证据来源和最近复测，明确复用文件及计数规则。 |
| `README.md` | 增加六个自然语言使用例子、暂停说明和证据边界。 |
| `AGENTS.md` | 只补入口层必要规则：模式由自然语言推断、暂停可先保存、A5 重建不对 browse/暂停强制。 |
| `acceptance-report.md` | 本轮实际验收记录；不是学习记录。 |

`modification-plan.md` 未修改。既有旧代码删除、`.gitignore`、`.gitkeep` 变更和 14 份
PDF 未被本轮恢复、删除、重命名或搬移。

## 3. T01–T22 固定场景

结果严格区分为 `PASS`、`FAIL`、`NOT RUN`。本轮没有可启动的 Tutor runtime，也没有
真实学习者的多轮输入，因此下表的行为场景没有用规则文本或预期响应冒充执行结果。

| 编号 | 结果 | 实际观察、文件证据或未执行原因 |
|---|---|---|
| T01 | NOT RUN | 未对 Tutor 发送新概念输入；当前无 `bin/learning-os`、`src/`、`tests/` 或 `pyproject.toml`。静态解析 `Templates/concept.md` 观察到四维和 `ai_level` 为真正的 YAML null。 |
| T02 | NOT RUN | 未发送“只解释，不测试”输入；未观察运行时响应。`SKILL.md` 的 `browse` 分支明确写有不催重建、不改分数。 |
| T03 | NOT RUN | 未执行 A5 后的多轮对话；`SPEC.md` 与 `SKILL.md` 仅提供了邀请重建且不提前改分的规则证据。 |
| T04 | NOT RUN | 未执行原题复述；`SPEC.md` 要求即时复述标 `reconstruction`，但本轮没有产生 Session 证据文件。 |
| T05 | NOT RUN | 未展示正式测试题，也未收集 confidence；静态规则要求先展示题目再收作答前 confidence。 |
| T06 | NOT RUN | 未执行中途求助；没有可保存的用户原始输出或模拟 Session，未伪造证据。 |
| T07 | NOT RUN | 未产生独立答对记录；当前没有 Concept/Session 学习数据可验证 `mastered` 行为。 |
| T08 | NOT RUN | 未使用 synthetic 临时夹具运行跨日证据演练；没有把虚构历史写入工作区。掌握门槛已写入 `SPEC.md`，但不是运行结果。 |
| T09 | NOT RUN | 未执行“先停，帮我保存”对话；模板包含 `paused` 兼容说明和恢复检查点，但没有实际暂停 Session。 |
| T10 | NOT RUN | 未执行明确 thread 恢复；没有最近 Session 可供运行时读取。 |
| T11 | NOT RUN | 未执行多 thread 消歧；没有并行真实线程，未按文件时间猜测。 |
| T12 | NOT RUN | 未执行论文补课后的原文重建；没有论文 Markdown 笔记或 learner output，未标 blocker resolved。 |
| T13 | NOT RUN | 未执行未输出/跳过场景；`SPEC.md` 对应规则保持 `open`/`deferred`，但无运行时状态可观察。 |
| T14 | NOT RUN | `Mistakes/` 中没有真实记录，未演练复用和重复整理；模板与规则已保留 `reoccurrences` 计数语义。 |
| T15 | NOT RUN | 没有旧学习笔记可做兼容读取；静态规则要求缺少新可选栏目不阻断使用，未伪造历史字段。 |
| T16 | NOT RUN | 未创建不可解析 frontmatter 或 thread 冲突夹具；规则文本要求不猜、不覆盖相关状态。 |
| T17 | NOT RUN | 未执行无法判定的推导演练；模板和规则包含 `uncertain`，但无实际判断可记录。 |
| T18 | NOT RUN | 未执行“今天最值得学什么”；规则文本要求只推荐一个动作并优先当前 P0，未产生推荐响应。 |
| T19 | NOT RUN | 未执行不同意评分或缺 confidence 场景；规则文本允许重新核验和 `unknown`，但无实际对话。 |
| T20 | NOT RUN | 未创建 Paper 笔记；模板含 `UNKNOWN`、来源和待验证动作，不能据此宣称论文事实已核验。 |
| T21 | NOT RUN | 未做受控 Concept 写入故障注入；`SKILL.md` 明确先保存 Session、再更新引用方，但没有部分保存实例。 |
| T22 | NOT RUN | 没有带 `next_review` 的 Concept，也未执行到期未参加复习；规则要求只保持待复习、不降分。 |

结论：T01–T22 行为演练均为 `NOT RUN`，没有 `FAIL`，但也不能称为行为验收通过。

## 4. 静态检查

以下是本轮实际执行的检查，不等同于 Tutor 行为演练：

- `git diff --check`：`PASS`。
- Ruby `YAML.safe_load` 解析四份模板：`PASS`。检查确认必需字段存在；Concept 的
  `recall`、`explanation`、`derivation`、`transfer`、`ai_level`、`next_review` 均为
  真正的 null，不是字符串 `"null"`。
- 旧冲突扫描：`PASS`。未发现“所有 A5 必须重建”“重建等于 A0”“必须先 reflection
  才能保存”“格式问题停止全部教学”等残留文本。
- Paper 单一下一步/ blocker 栏目：`PASS`。`next_action:` 恰有一处，`## Next Step`
  和独立 `## P0`–`## P3` 均不存在。
- 语义锚点检查：`PASS`。已在文档中找到 `browse`、`learn`、`assess`、
  `delayed-independent`、`novel_transfer`、`resolved-for-reading`、`deferred`、
  `UNKNOWN`、`reoccurrences`、`next_review`、2–3 天复习起点和先保存 Session 的规则。
- 学习记录污染检查：`PASS`。`Concepts/`、`Mistakes/`、`Sessions/` 仍只有 `.gitkeep`，
  没有 synthetic 学习数据。
- PDF 保护检查：`PASS`。`Papers/` 仍有 14 份原有 PDF；本轮没有修改其文件名或内容。
- 依赖/基础设施检查：`PASS`。本轮未新增依赖、CLI、数据库、scheduler、插件、Web UI、
  测试框架或自动推送。

## 5. 行为演练工具、隔离方式与限制

实际只使用了本地文本读取、Ruby YAML 解析、`git diff --check`、`rg`、`find` 和 Git
状态检查。行为演练未启动：基线中的可执行 CLI、源码、测试和 `pyproject.toml` 已处于
用户既有删除状态；剩余 Tutor 是由 Codex 读取的 skill 规则，没有独立可调用的运行时。
为遵守方案“不把预期行为当实际验收”和“不把模拟回答写成用户表现”，没有新增运行时，
也没有把 synthetic 夹具或虚构 learner output 写入仓库。

## 6. 兼容处理

实际发现没有旧 Concept、Paper、Mistake 或 Session 记录，因此不需要批量迁移、补字段、
改 thread、改历史分数或核验历史 `mastered`。只有模板和 14 份 PDF；按方案只更新模板，
没有为 PDF 批量创建空笔记。由于没有真实记录，也不存在断链或旧 frontmatter 需要修复的
兼容动作。

## 7. 未解决项与偏离

- T01–T22 全部尚未完成运行时行为演练；原因是可执行实现不在当前工作区，且本轮范围不
  授权恢复已删除旧代码或建设新应用。
- 真实学习效果、跨日独立表现、恢复摩擦和记录负担尚未验证，必须在后续真实使用中观察。
- 未偏离文档改造范围；未执行 commit、push、插件安装、全局配置修改或 PDF 操作。

## 8. 最终结论

方案要求的文档修改已完成，静态检查通过；真实记录兼容处理无工作可做。行为验收未完成
（T01–T22 均 `NOT RUN`），因此本报告不声称“全部验收通过”。学习效果仍待真实使用和
后续跨日证据验证。
