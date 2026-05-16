# LLM Interview Kit — 数据契约

所有 skill 共享的 schema。修改前先检查：改动会不会破坏 `index.py` 的扫描、`build_mindmap.py` 的聚合、或某个 skill 的写入逻辑。

## 全局约定

- 知识库根目录：`./llm-kb/`（运行 Claude Code 的工作目录下，或通过环境变量 `LLM_KB_ROOT` 覆盖）
- 所有内容文件 = markdown + YAML frontmatter
- ID 命名规则：
  - wiki 条目：`kn_<yyyy>_<short_slug>`，例如 `kn_2026_grpo`
  - frontier 条目：`fr_<yyyy>_<short_slug>`，例如 `fr_2026_dapo`
  - 面试题：`q_<NNNN>`，例如 `q_0042`（自增，脚本分配）
  - 面试场次：`iv_<yyyy>_<mm>_<company-slug>_<n>`
- 日期格式：ISO `YYYY-MM-DD`
- 中文内容写中文，schema 字段名一律英文
- 文件名 = id + `.md`，例如 `wiki/kn_2026_grpo.md`

---

## 1. Wiki 条目（个人知识库）

路径：`llm-kb/wiki/<id>.md`

这是**合成层**：跨来源的概念节点。一个概念（如 GRPO）被多篇论文提到，也可能在多场面试中暴露 gap，只有一个 wiki 条目。

```yaml
---
id: kn_2026_grpo                # 必填，唯一
title: "GRPO"                   # 必填
type: concept                   # concept | method | framework | tool | other
topics: [rl, post-training]     # 必填，至少一个；第一个 topic 是 mindmap 顶层分组键
status: draft                   # stub | draft | reviewed | needs_more
linked_questions: [q_0042]      # 关联到此知识点的题库 id（双向，题卡也要回链）
linked_frontier: [fr_2026_dapo] # 哪些前沿报告讨论了这个概念（双向，frontier 也要回链）
linked_from_interviews: [iv_2026_05_xxx_1]
sources:                        # 可选（type=concept 可空但 status 要是 draft/stub）
  - kind: paper                 # paper | blog | doc | repo | other
    url: "https://arxiv.org/abs/..."
    citation: "Shao et al., DeepSeekMath, 2024"
gaps:                           # 还没搞清的点，来自 interview gap 回流 或 手动标记
  - "group size 对方差的影响还没看实验"
created: 2026-05-16
updated: 2026-05-16
---

# 正文（markdown）

## 一句话总结

## 核心内容

## 与相关概念的对比

## 待补
（结构化的 gaps 在 frontmatter，这里可以放更长的笔记）
```

**写入规则**：
- `wiki` skill 创建或更新此文件（可以从头新建，也可以由 frontier-ingest 触发创建）
- `interview-review` 不直接改这里，通过 `propagate_gaps.py` 写 `gaps` 和 `linked_from_interviews`
- `frontier-ingest` 通过 `link_wiki.py` 写 `linked_frontier`
- 任何 `status=needs_more` 或非空 `gaps` 的条目，下次 frontier-ingest / wiki 操作时主动提示

---

## 2. Frontier 条目（前沿热点）

路径：`llm-kb/frontier/<id>.md`

这是**原始来源层**：每篇论文/技术报告/博客一个文件，自包含，直接供复习用。不合并不聚合。

```yaml
---
id: fr_2026_dapo                # 必填，唯一
title: "DAPO: Decoupled Clip and Dynamic Sampling Policy Optimization"  # 必填
type: paper                     # paper | tech_report | blog | hot_topic_summary
url: "https://arxiv.org/abs/2503.14476"  # 必填（找不到写 "N/A"，不要编）
authors: "Yu et al."            # 可选
date: 2026-03-18                # 论文/报告发布日期（不是 ingest 日期）
topics: [rl, post-training]     # 必填，至少一个；第一个是 mindmap 顶层分组键
status: ingested                # ingested | needs_review | archived
linked_wiki: [kn_2026_grpo]     # 关联的 wiki 条目（双向，wiki 也要回链）
created: 2026-05-16
updated: 2026-05-16
---

# 一句话总结

# 背景与动机

# 核心方法

# 关键实验结论

# 与相关工作的关系

# 待深入
```

**写入规则**：
- 仅 `frontier-ingest` skill 创建此文件
- 一篇论文一个文件，不合并，不拆分（一篇论文的多个 contribution 写在同一文件的不同章节）
- `linked_wiki` 通过 `link_wiki.py` 脚本维护，Claude 不手改 YAML

---

## 3. Question 卡

路径：`llm-kb/questions/<id>.md`

精简 schema，只保留 mock-interview 和复盘所需的字段。

```yaml
---
id: q_0042                     # 必填，自增（脚本分配，不要手填）
question: "讲一下 GRPO 和 PPO 的区别，为什么不要 critic"   # 必填
topics: [rl, post-training]    # 必填
asked_in:                      # 出现过这道题的场次 id
  - iv_2026_05_xxx_1
my_answer_history:             # 每次回答都 append，不删旧的
  - date: 2026-05-10
    context: real_interview    # real_interview | mock_interview
    summary: "讲了 group baseline 替代 value head，没讲清方差问题"
    self_rating: 3             # 1-5
better_answer: |               # 必填，1-3 段，给未来的自己看
  ...
gaps_to_fill:                  # 还没答好的子点，反向写入 wiki.gaps
  - "GRPO group size 与方差的关系"
linked_knowledge: [kn_2026_grpo]   # 关联的 wiki 条目 id（字段名保持以兼容脚本）
mastery: 0.5                   # 0-1，由脚本自动计算，不要手填
---
```

`mastery` 计算：取最近 3 次 `self_rating`，加权平均（最近一次 0.5、前两次各 0.25），归一化到 0-1：`mastery = (weighted_avg - 1) / 4`。无历史时 mastery = 0。

注意：`linked_knowledge` 字段名保留（字段值是 wiki id `kn_xxx`），以兼容现有脚本。

---

## 4. Interview 场次

路径：`llm-kb/interviews/<id>/`（目录）

```
iv_2026_05_xxx_1/
  meta.yaml
  raw.md             # ASR 清洗后的文本，只写一次，不改（原始输入丢弃）
  questions.json     # 这场抽出的 q_id 列表（脚本生成）
  review.md          # 渲染好的复盘（人看的）
  missing_wiki.json  # 引用了但 wiki/ 里还没有的条目（可选）
```

`meta.yaml`：

```yaml
id: iv_2026_05_xxx_1
company: "某司"
role: "LLM Engineer"
round: "技术 1 面"
date: 2026-05-15
duration_min: 60
interviewer_style: "深挖项目，喜欢追问数学细节"
outcome: pending               # pending | passed | failed | ghosted
self_overall_rating: 3
created: 2026-05-15
```

`review.md` 结构参考 `interview-review/SKILL.md`。

---

## 5. 索引

路径：`llm-kb/index/all.json`（脚本生成，不要手改）

顶层字段：`wiki`、`frontier`、`questions`、`interviews`、`topics`、`stats`。

每次任何 skill 写文件后，都要调 `scripts/index.py` 重建索引。

---

## 6. 反向链接强一致性

- `question.linked_knowledge` ↔ `wiki.linked_questions`（双向）
- `frontier.linked_wiki` ↔ `wiki.linked_frontier`（双向）
- `question.asked_in` ↔ `interview/questions.json`（双向）
- `scripts/validate.py` 检查以上所有一致性

---

## 7. 写入的金科玉律

1. **判断在 Claude，写入在脚本**：Claude 决定语义，脚本管 id / frontmatter / 双向链接
2. **永远不删历史**：`my_answer_history` 只 append
3. **gaps 是闭环命脉**：面试暴露的 gap 必须写回 wiki，下次 ingest / wiki 操作时消费
4. **不要假装有数据**：url 必须真实，找不到写 `"N/A"`，不要编
