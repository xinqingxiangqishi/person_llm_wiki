# LLM Interview Kit

个人化的 LLM 求职知识管理 + 面试复盘工具集。跑在 Claude Code 上。

## 是什么

3 个 Claude skill 共享一个本地数据目录：

- **interview-review** — 把面试文字记录变成结构化复盘 + 问题卡，gap 自动回流到 wiki ✅ v0.1 已实现
- **frontier-ingest** — 把论文/博客/技术报告沉淀成前沿热点条目（每篇一个文件），与 wiki 建立双向链接 ✅ v0.2 已实现
- **wiki** — 个人知识库管理：新建/更新概念节点，查看待补 gap，搜索已有知识 ✅ v0.2 已实现

## 数据目录结构

```
llm-kb/
  interviews/      # 面试复盘（每场一个子目录）
  questions/       # 题库（q_xxxx.md，自增）
  frontier/        # 前沿热点（每篇论文/报告一个文件，fr_yyyy_slug.md）
  wiki/            # 个人知识库（概念节点，kn_yyyy_slug.md）
  index/           # all.json（脚本生成，不要手改）
  mindmap/         # mindmap.mmd + mindmap.md
  drafts/          # 草稿、临时文件
```

## 文档

- 📄 [`DESIGN.md`](DESIGN.md) — 完整设计文档，给后续接手的 Claude Code 看
- 📄 [`skills/shared/CONTRACTS.md`](skills/shared/CONTRACTS.md) — 数据契约（schema），改动前必读
- 📄 [`skills/interview-review/SKILL.md`](skills/interview-review/SKILL.md) — 面试复盘工作流
- 📄 [`skills/frontier-ingest/SKILL.md`](skills/frontier-ingest/SKILL.md) — 前沿热点摄入工作流
- 📄 [`skills/wiki/SKILL.md`](skills/wiki/SKILL.md) — 知识库管理工作流

## 第一次用

```bash
pip install pyyaml --break-system-packages
export LLM_KB_ROOT=~/Documents/llm-kb
mkdir -p $LLM_KB_ROOT/{knowledge,questions,interviews,mindmap,index,drafts,frontier,wiki}
```

然后在 Claude Code 里直接说你想做什么，Claude 会读对应的 SKILL.md 跑流程：

- "刚面完一场，帮我复盘下" → interview-review
- "帮我总结这篇论文 [URL]" → frontier-ingest
- "新建一个 GRPO 的 wiki 条目" → wiki
- "知识库缺什么，帮我看看" → wiki（场景 C）

## 设计原则速览

1. **判断在 Claude，写入在脚本** — Claude 决定语义，脚本管 YAML 和双向链接
2. **两层分离** — `frontier/`（原始来源摘要）vs `wiki/`（跨来源合成节点）
3. **永远不删历史** — `my_answer_history` 只 append，看得见进步轨迹
4. **闭环：gap 必须回流** — 面试暴露的 gap 自动写回 wiki，frontier-ingest 和 wiki 时主动消费
5. **本地优先** — 公司名、原话不出本地；web_search 只用于明确公开的技术点
6. **markdown + frontmatter + JSON 索引** — 不上向量库不上图数据库

## 下一步（给接手的 Claude Code）

读 `DESIGN.md` §6，建 `mock-interview`。
