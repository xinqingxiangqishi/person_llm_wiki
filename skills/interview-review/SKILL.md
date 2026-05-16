---
name: interview-review
description: 把一场面试的原始记录（语音转文字或手打文字）整理成结构化复盘文档。支持 ASR 文本预处理（纠错别字、合并断句）。使用场景：用户说"帮我复盘"、"刚面完"、"整理面经"、"面试录音文本在这"。
---

# Interview Review

把一场面试变成：
1. `raw.md` — ASR 清洗后的文本（原始输入丢弃）
2. `review.md` — 逐题复盘：问题 / 我的回答 / 评分 / 亮点不足 / 改进方向 / 参考要点
3. `q_xxxx.md` — 题目卡（供 mock-interview 使用，schema 精简）

## Local-First Rule

公司名、面试原话可能敏感。一切只在本地 `llm-kb/` 处理。`web_search` 只用于明确公开的技术点（用户主动要求时）。

## 数据契约

读 `skills/shared/CONTRACTS.md`。写入：
- `llm-kb/interviews/<iv_id>/`（meta.yaml、raw.md、review.md、questions.json）
- `llm-kb/questions/q_xxxx.md`（新建或追加历史）
- `llm-kb/wiki/*.md` 的 gaps 字段（通过脚本）

---

## 工作流（3 步）

### 步骤 1：收集信息 + ASR 预处理（Claude）

**先问用户**（一次性问完，已说过的就不问）：
- 公司（可模糊，如"某大厂"）
- 岗位 + 轮次
- 日期（没说就用今天）
- 时长、自评 1-5 分

**然后对用户提供的文本做 ASR 清洗**：
- 纠正明显错别字（语境推断，如"在训练"→"再训练"，"这个这个"删掉一个）
- 合并语音断句（"嗯...那个...就是说 PPO 它..."→"PPO..."）
- 保留技术术语原貌（GRPO、KL divergence 等不要改）
- 听不清 / 无法判断的片段标记 `[unclear]`，**不要猜**
- **不要美化回答内容**，清洗只是去噪，不是润色

清洗完的文本即为 `raw.md` 内容，原始输入丢弃。

### 步骤 2：完整分析，生成 JSON（Claude）

**先查重**：对每道题调一次 search_questions.py，判断是否复用已有 id：

```bash
python3 skills/interview-review/scripts/search_questions.py \
  --query "<题目文本>" --topics "<topic1,topic2>"
```

返回 top-3 相似题。相似度 > 0.4 且技术内核相同 → 填 `reuse_id`；否则留空。

**然后一次性输出完整分析 JSON**，写到 `/tmp/interview_draft.json`：

```json
{
  "meta": {
    "company": "某司",
    "role": "LLM算法工程师",
    "round": "技术二面",
    "date": "2026-05-16",
    "duration_min": 60,
    "self_overall_rating": 3,
    "interviewer_style": "深挖底层原理，追问数学细节"
  },
  "cleaned_transcript": "（清洗后的完整文本）",
  "overall_rating": 3.5,
  "overall_comment": "RL 方向基础扎实，但代码题临场发挥偏弱，系统设计题缺乏结构化表达。",
  "next_prep": [
    "重刷 GRPO 原论文 §3 方差分析",
    "练习 LLM serving 系统设计的 STAR 结构表达"
  ],
  "questions": [
    {
      "reuse_id": "",
      "question": "讲一下 GRPO 和 PPO 的区别，为什么 GRPO 不需要 critic",
      "topics": ["rl", "post-training"],
      "my_answer_summary": "讲了 group baseline 替代 value head，提到省显存，但没讲清方差问题",
      "self_rating": 3,
      "highlights": "方向正确，提到了 group relative baseline 的核心思想",
      "weaknesses": "没讲清 group size 和方差的关系，面试官追问时没答上来",
      "improvement": "补 DeepSeekMath 原论文 §3.2，重点看 Var(A) = Var(r)(1-1/G) 这个推导",
      "better_answer": "PPO 用 critic 网络估 V(s) 计算 advantage...\nGRPO 对同一 prompt 采样 G 个输出，用 group 内 reward 均值做 baseline...\n好处是省 critic 显存；代价是 G 不够大时方差偏高...",
      "gaps_to_fill": ["GRPO group size 与方差关系的数学推导"],
      "linked_wiki_titles": ["GRPO"]
    }
  ]
}
```

**覆盖度要求**：一场 60 分钟面试通常 8-15 个实质问题。少于 5 个一定是漏了，回去重扫清洗后的文本。追问算独立问题，不要塞进主问题的回答里。

### 步骤 3：一键写入所有文件（脚本）

```bash
python3 skills/interview-review/scripts/process_interview.py \
  --json /tmp/interview_draft.json
```

脚本一次完成：建目录 → 写 meta.yaml → 写 raw.md → 创建/更新问题卡 → 渲染 review.md → 传播 gaps → 输出 iv_id 和统计。

### 步骤 4：重建索引

```bash
python3 skills/shared/scripts/index.py
python3 skills/shared/scripts/build_mindmap.py
python3 skills/shared/scripts/validate.py
```

validate 报错就停下来修。

### 步骤 5：交付（Claude）

给用户：
- review.md 路径
- 新建/复用题数
- top-3 gap（从脚本 stdout 拿）
- 一句建议

---

## review.md 格式

```markdown
# <公司> <轮次> 复盘 — <日期>
_岗位_: ...  •  _时长_: ... 分钟  •  _自评_: .../5

## 总体评价
**评分**：3.5/5
<一句话总评>

**下次重点准备**：
- ...

---

## Q1. <问题>  [[q_0001]]
_topics_: ...  •  _自评_: .../5

**我的回答**
<my_answer_summary>

**评分**：3/5  ✅ 亮点：<highlights>  ❌ 不足：<weaknesses>

**改进方向**
<improvement>

**参考回答要点**
<better_answer>

---

## 这场暴露的 Gap
| 知识点 | Gap | 优先级 |
|---|---|---|
| GRPO | group size 与方差推导 | 高 |
```

---

## 反模式（不要做）

- ❌ ASR 清洗时美化用户的回答内容
- ❌ 一场面试只抽 3-5 道题（除非真的就问了这么多）
- ❌ `better_answer` 里编数字或编 URL
- ❌ 跳过脚本直接用文字回答（数据不落地 = 白做）
- ❌ 在 review.md 里出现绝对路径

## 最终交付清单

- [ ] `interviews/<iv_id>/` 下有 meta.yaml、raw.md、questions.json、review.md
- [ ] 每道题有 better_answer 且非空
- [ ] `validate.py` 通过
- [ ] index 和 mindmap 重建完成
