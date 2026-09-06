# codex-learning-os

一个只给自己使用的个人 AI 学习与科研辅助系统。它用 Markdown 保存学习状态，让 Codex
减少无意义摩擦，同时把真正的解释、推导、迁移和研究判断交还给我。

> Maximize future unassisted performance, not current assisted performance.

## 中文快速开始

把这个文件夹作为 Codex 工作区打开，直接用自然语言说。下面六种说法展示常见用法；不
需要记 `mode`、证据类型或任何命令。

1. 快速浏览：`这个符号是什么意思？只解释，不测试。`
2. 核心学习：`我想学会强凸性，先让我试一下。`
3. 正式测试：`测试我到底会不会 Attention。`
4. 暂停保存：`先停，帮我保存现在的进度。`
5. 恢复：`继续上次那篇跨频段 CSI 论文。`（有歧义时 Tutor 会简短确认。）
6. 选择今日一个动作：`今天最值得学什么？`

也可以直接说：

```text
我要学习 KKT。
我想用费曼法解释这个概念。
我论文里这个公式完全看不懂。
EFIM 是什么？
这个经典方法我没有学过。
这个 benchmark 是干什么的？
这个 SOTA 方法我需要读到什么程度？
帮我判断我应该先补什么。
我直接想听完整解释。
```

Tutor 会按 `.agents/skills/ai-tutor/SKILL.md` 和 `SPEC.md` 读取相关状态：浏览时直接
解释，学习时按基础给帮助，完全陌生可以先教定义和例子；正式测试时先出题再收置信度。A5 完整
解释后的核心学习通常会邀请不看答案重新解释、推导或应用；“听懂了”不等于掌握。暂停
可以先保存检查点，不必先完成重建或 reflection。

## 个人自用的最短循环

**选一个小目标 → 读或动手 → 卡住时定向补充 → 留一个能继续的下一步。**

科研入门可以直接说：

> 我想边读 CSI 论文补基础，还没有自己的 idea。先帮我选一个小切口和一篇适合深入的论文，
> 再带我理解一个关键机制；陌生的定义直接讲，值得长期会的部分让我试一下。

也可以说“这个基础反复卡住我，帮我连起来学一点，再回论文”，或者“我想复现一个关键
结果，先弄清输入输出、指标和对照”。不要求先读完一套课程或每篇论文都找出创新点。

查一个符号默认不建档。有值得保留的进度时 Tutor 按模板保存，每栏一句也可以；你不用
手填模式、标签或分数。记录只保留真实输出和恢复需要的信息，不要求填满所有栏目。
恢复优先读最近 Session；论文笔记链接该恢复动作，避免维护多份下一步。

详细实践见 [AI 辅助学习方法论](ai-assisted-research-methodology.md)。日常直接开始即可，
需要选择方向、判断实验或梳理证据时再查相关部分。

## 文件夹

- `Concepts/`：概念当前模型、学习目标、能力维度、证据和下一次练习。
- `Papers/`：论文来源、问题、阅读位置、blocker、主张与验证路径。
- `Mistakes/`：可复用的稳定错误模式，而不是每次小失误。
- `Sessions/`：按 `thread` 保存原始学习证据和可恢复检查点。
- `Templates/`：Concept、Paper、Mistake、Session 的统一格式。
- `SPEC.md`：长期系统规范。
- `AGENTS.md`：进入仓库时的短入口。

文件名使用 lowercase-kebab-case：

```text
Concepts/strong-convexity.md
Papers/cross-band-fm.md
Mistakes/kkt-necessary-vs-sufficient.md
Sessions/2026-09-03-kkt.md
```

## 使用边界

这是个人工具，不包含 Web UI、数据库、RAG、多用户、云同步或自动互联网抓取。如果
Markdown + Skill 已经够用，就不继续加工程。

学习数据可能包含私人弱点、未公开科研思路和论文批评；建议使用 private repository。
如果 remote 是 public，在首次 push `Sessions/`、`Mistakes/` 或真实论文笔记前，先确认
隐私合适。

按已有授权，新对话先拉取当前分支最新版本；每组修改检查后自动提交并推送本次相关文件。
不自动丢弃本地工作或强推；失败会说明。本次不想同步时直接说“这次不要提交或推送”。

## English

`codex-learning-os` is a private, Markdown-first learning and research companion for one
learner. Its purpose is to improve future independent performance. Assisted correctness,
A5 explanations, reconstruction, and recognition are not by themselves mastery evidence.
