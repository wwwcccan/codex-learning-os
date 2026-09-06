# codex-learning-os

这是只供本人使用的 Markdown-first 学习与科研辅助系统。目标是提高未来的独立
学习能力，不是让当前的 AI 辅助答案看起来完整。

开始任何任务前：

1. 先读 `SPEC.md`；
2. 按需读取相关 `Concepts/`、`Papers/`、`Mistakes/` 和同 `thread` 的最近
   `Sessions/`；
3. Tutor 行为遵循 `.agents/skills/ai-tutor/SKILL.md`；
4. 使用 `Templates/` 的固定格式，保留学习者自己的原始思考。

关键约束：

- Markdown + YAML frontmatter 是状态来源；不主动加入复杂基础设施。
- assistance 不等于 mastery；核心学习在 A5 后邀请 learner reconstruction，浏览、明确暂停或只想听解释时不强制。
- 从自然语言推断 browse、learn、assess；正式 assess 先出题再收 confidence，缺少输出不推定不会。
- 重要 Mistake 先复用已有模式；不为小计算错误建档。
- `Sessions/` 用 `thread` 区分并行任务；resume 有歧义时只简短询问，不猜。
- 暂停可先保存真实检查点，不要求先 reflection；跨文件更新先保存 Session，再更新引用方。
- 固定使用 lowercase-kebab-case 和约定的文件路径。
- 私人学习与科研内容默认按 private repository 处理；用户已于 2026-09-06 授权每次完成修改并检查后自动 commit、push 到本仓库 GitHub remote，具体规则见 `SPEC.md`。

完整长期规则见 `SPEC.md`；不要把 SPEC 复制到本文件，也不要重新设计整个系统。
