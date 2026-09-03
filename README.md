# Codex Learning OS

一个以 Markdown 为第一公民的个人 AI 学习与科研训练系统。它不把“在 AI 帮助下做对”误认为掌握，而是持续记录：你哪里不会、需要多少帮助、能否在 A0 条件下独立输出，以及什么时候应该让 AI 退出。

## 中文快速开始

核心运行时只依赖 Python 3.12+ 标准库：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
learning-os init
```

创建一个概念并开始学习：

```bash
learning-os concept create strong-convexity \
  --name "Strong Convexity" \
  --domain convex-optimization \
  --prerequisite convex-functions \
  --prerequisite gradient

learning-os session start 2026-09-03-strong-convexity \
  --mode learning \
  --concept strong-convexity \
  --goal "从记忆解释强凸性的定义并重建关键推导"

learning-os session attempt 2026-09-03-strong-convexity \
  --text "我的初始解释……"
learning-os session hint 2026-09-03-strong-convexity --level A2 \
  --text "考虑 Hessian 的下界"
learning-os a0 record strong-convexity \
  --dimension derivation --correct --confidence 65 --novel \
  --session 2026-09-03-strong-convexity
learning-os session finish 2026-09-03-strong-convexity \
  --reflection "我仍然混淆了定义和充分条件" \
  --next-action "T+1 day 做 A0 recall"
learning-os dashboard
```

查看所有命令：

```bash
learning-os --help
learning-os concept --help
```

如果不想安装 editable package，也可以在仓库根目录使用：

```bash
PYTHONPATH=src python3 -m learning_os init
./bin/learning-os init
```

editable 安装只用于把 `learning-os` 放进环境；核心运行时没有第三方依赖。如果本机的 Python 受 PEP 668 或离线构建工具限制，直接使用上面的 source-tree launcher 即可。

## MVP 覆盖范围

- Learning Mode：Concept、五维能力、Feynman 会话记录、A0 evidence、延迟 review。
- Research Mode：Paper、blocker diagnosis、P0–P3 dependency map、证据标签和 prerequisite repair 线索。
- Mistakes：保存认知 bug，而不只是正确答案。
- Dashboard：due reviews、weak concepts、unresolved mistakes、repeated blockers、AI dependency、A0 success rate、foundation-track candidates。
- 可替换 scheduler 接口；MVP 使用透明的固定间隔 fallback，不自研 FSRS。

## 设计边界

当前不包含 Web UI、数据库、向量检索、RAG、多用户、云同步、自动互联网抓取和自动自然语言评分。LLM 通过 `.agents/skills/ai-tutor/SKILL.md` 负责教学判断；Python 代码负责可验证的状态更新。

详细设计见：

- `docs/architecture.md`
- `docs/implementation-plan.md`
- `docs/data-model.md`
- `docs/mastery-rubric.md`
- `docs/pedagogy.md`
- `docs/hint-policy.md`
- `docs/assessment-policy.md`
- `docs/research-mode.md`

## English

Codex Learning OS is a Markdown-first personal learning and research training system. Its objective is future independent performance. Assisted correctness is tracked as assistance evidence, not mastery. The MVP uses a standard-library Python CLI, versioned frontmatter schemas, explicit A0 evidence, deterministic mastery gates, blocker diagnosis, mistake tracking, and a replaceable review scheduler.
