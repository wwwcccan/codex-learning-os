---
status: reading
thread: paper:paper-slug
next_action:
---

# Paper Title

有实际阅读且值得追踪时才建立。起步只需来源、当前问题、位置、真实理解和 next_action；
其他栏目按需填写，未用栏目可省略，不保留虚构 blocker 或示例证据。
有同 thread 的 Session 时，next_action 使用带引号的 YAML 字符串，保存指向最新 Session
“下次第一件事”的相对 Markdown 链接；尚无 Session 时直接写一个阅读动作。

## Source

- 标题与已核实的版本信息：
- 本地 PDF：相对链接，或原始来源 URL：
- DOI / arXiv 标识：UNKNOWN（仅在已知时填写）
- 页码约定：PDF 页序 / 印刷页码；如有差异在此说明。

## Core Problem

这篇论文到底解决什么问题？

与我当前的小切口有什么关系？本阶段只需理解什么或判断什么？尚无 idea 也可以开始。

## Main Idea

作者的核心思路是什么？区分作者主张与我的理解。

## Current Position

我目前读到哪一节、哪一页、哪个公式或图表？这里记录阅读位置，不和 Source 混用。

## Current Blockers

每个 blocker 只在此处维护一份，记录优先级、类型、原文位置、需要的最小补充、状态和
验证证据。类型为 `notation`、`math_prerequisite`、`derivation`、`classical_method`、
`benchmark` 或 `related_work`；优先级为 `P0`–`P3`；状态为 `open`、
`resolved-for-reading` 或 `deferred`。checkbox 仅在 `resolved-for-reading` 时勾选。

- [ ] [P0] blocker — type: `notation | math_prerequisite | derivation | classical_method | benchmark | related_work`; location: ; minimum supplement: ; status: `open`; verification evidence:

## Core Formulas

记录公式、目标理解深度（L1–L5）和仍缺少的关键步骤。背景通常到 L1–L2，核心贡献
通常到 L3–L4。

## My Current Understanding

用学习者自己的语言写。Tutor 总结、学习者推断和 UNKNOWN 分开；没有实际 learner output
时写“尚未输出”，不把 AI 解释冒充成学习者判断。

## Claims / Evidence / Verification

仅针对重要主张填写：

- 作者主张及位置：
- 原文证据与适用范围：
- 我的判断：必须来自学习者实际输出；没有则写“尚未输出”。
- Tutor 建议：明确归属；没有则写“无”。
- 下一验证动作：具体的对照、推导检查或来源核验。
- 结论状态：`尚未验证` / `有限支持` / `不支持` / `不确定`，并解释依据。

计划中的验证动作不等于已经下载、运行实验或验证结论。

多次活动需要汇总时，在本栏目链接实际 Session 或实验产物，简列“当前主张 / 支持证据 /
反证或缺口 / 当前判断”，保留范围和修订依据；不每次新建证据表。逐项验证动作是候选
检查，当前要执行哪一项由 next_action 所指的 Session 决定。

## Questions / Critique

区分原文事实、学习者批评、Tutor 建议和待验证的研究疑问。尚无实验时写“尚无实验”，
不得宣称已验证。

值得追踪的疑问可简记：我观察到什么、我如何解释、已有工作是否回答过、什么最小检查能
判断是否值得继续。没有自己的解释就写“尚未输出”，不要求每篇论文都有创新点。

## Method Card（按需）

对陌生经典方法、SOTA 或 benchmark，只记录问题、输入、输出、核心思想和本文为何提到；
不默认阅读原始论文。
