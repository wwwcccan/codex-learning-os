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
5. 明确 thread 恢复：`继续 thread 为 paper:cross-band-fm 的论文阅读。`
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
解释，学习时先让学习者尝试并给最低有效帮助，正式测试时先出题再收置信度。A5 完整
解释后的核心学习通常会邀请不看答案重新解释、推导或应用；“听懂了”不等于掌握。暂停
可以先保存检查点，不必先完成重建或 reflection。

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

## English

`codex-learning-os` is a private, Markdown-first learning and research companion for one
learner. Its purpose is to improve future independent performance. Assisted correctness,
A5 explanations, reconstruction, and recognition are not by themselves mastery evidence.
