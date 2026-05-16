---
name: interview-review
description: 把一场面试的原始记录（手打文字或口述转文字）整理成结构化复盘。抽取每个问题、记录你的真实回答、生成更好的回答、识别需要补的知识 gap，并把 gap 反向写回知识库形成闭环。使用场景：用户说"刚面完"、"帮我复盘下这场面试"、"整理面经"、"我把面试笔记给你"。不处理音视频文件（用户已表示输入是文字）。
---

# Interview Review

把一场面试的文字记录变成：
1. 一份 `review.md`，给你下次面试前 5 分钟扫一眼用
2. 一批 `q_xxxx.md` 问题卡，沉淀到题库供模拟面试和重复出现时聚合
3. 写回 `wiki/` 的 gap 列表，让"这道题没答好"变成"下次 ingest 时要重点搞清的事"

输入纯文字，不做 ASR。

## Local-First Rule

公司名、面试官姓名、你说过的话可能敏感。一切只在本地 `llm-kb/` 目录下处理，不要 web_search 真实公司名，不要在生成的内容里塞绝对路径。用户主动要求 web_search 某个技术点的标准答案除外。

## 数据契约

读 `skills/shared/CONTRACTS.md`（wiki 条目的 schema 在 §1，question 卡在 §3）。这个 skill 写入：
- `llm-kb/interviews/<iv_id>/`（新建一整个目录）
- `llm-kb/questions/q_xxxx.md`（新建或更新已有的）
- `llm-kb/wiki/*.md` 的 `gaps` 和 `linked_from_interviews` 字段（通过脚本，不要手改 YAML）
- `llm-kb/index/all.json`（流程末尾重建）

## 工作流

Claude 走判断，脚本走确定性。**严格按顺序**：

### 步骤 1：收集元数据（Claude）

问用户（一次性问完，不要逐条问）：
- 公司（可以模糊化，比如 "C-large-AI"）
- 岗位 + 轮次
- 日期（不说就用今天）
- 时长
- 这场的整体感觉 1-5 分

如果用户在第一条消息里已经说了，就不再问。

### 步骤 2：创建场次目录（脚本）

```bash
python skills/interview-review/scripts/new_interview.py \
  --company "<company>" --role "<role>" --round "<round>" \
  --date <YYYY-MM-DD> --duration <min> --rating <1-5>
```

脚本输出新创建的 `iv_id` 和目录路径。把用户给的原始文字直接写到 `<iv_dir>/raw.md`。

### 步骤 3：抽取问题（Claude）

读 `raw.md`，识别每一个独立的"面试官提问 → 候选人回答"对。原则：

- **覆盖度优先**：一场 60 分钟面试通常 8-15 个实质性问题（不算寒暄）。少于 5 个一般是你漏抽了，回去再扫一遍
- **追问算独立问题**：A 问题里的深挖追问单独成卡，不要塞进 A 的"我的回答"里
- **不抽**：寒暄、自我介绍流水账、薪资问答、反问环节
- **问题清洗**：写成正常的中文问句，不要保留口语 "嗯那个那个" 这种，但保留技术术语原貌
- **回答忠实**：`my_answer.summary` 必须反映你**当时真的说了什么**，不要替你润色成"你应该这样答"。润色那是 `better_answer` 的事

对每个问题，先**搜一下题库里是不是已经有这道题**：

```bash
python skills/interview-review/scripts/search_questions.py --query "<question text>" --topics "<comma,separated>"
```

返回 top-3 相似度结果。Claude 判断：
- 相似度高 + 技术内核相同 → 复用旧 id，把这次回答 append 到 `my_answer_history`，更新 `asked_in`
- 看起来像但其实问的不一样 → 新建 q_id，但在 `linked_knowledge` 里互相挂上

### 步骤 4：批量写入问题卡（脚本）

Claude 整理成一个 JSON 数组喂给脚本，脚本负责分配 id、双向挂链、写文件：

```bash
python skills/interview-review/scripts/upsert_questions.py \
  --interview <iv_id> --questions-json /tmp/questions_draft.json
```

`questions_draft.json` schema：

```json
[
  {
    "reuse_id": "q_0042",          // 复用时填，新建时留空
    "question": "...",
    "topics": ["rl", "post-training"],
    "my_answer_summary": "...",
    "self_rating": 3,
    "better_answer": "1-3 段",
    "gaps_to_fill": ["..."],
    "linked_knowledge_titles": ["GRPO", "DAPO"],   // 用标题或 slug，脚本帮你解析到 id
    "difficulty": 3
  }
]
```

`linked_knowledge_titles` 里如果某个标题在 wiki/ 里找不到对应条目，脚本会：
1. 把它记录到 `<iv_dir>/missing_wiki.json`
2. 在场次复盘的末尾提示 "以下知识点还不在库里，建议跑 kb-ingest 补上：..."

不要让 Claude 自动创建知识条目——那是 `kb-ingest` 的活，分工明确。

### 步骤 5：生成 review.md（脚本 + Claude）

```bash
python skills/interview-review/scripts/render_review.py --interview <iv_id>
```

脚本拼出骨架（按 CONTRACTS.md §3 的格式），Claude 在脚本输出基础上补"一句话总评"和"下次同公司应该准备"两节——这两节需要判断，脚本写不出。

### 步骤 6：写回 gaps（脚本）

```bash
python skills/interview-review/scripts/propagate_gaps.py --interview <iv_id>
```

这一步把每个问题卡的 `gaps_to_fill` append 到对应的 `linked_knowledge` 条目的 `gaps` 字段（去重），同时把场次 id 加到这些条目的 `linked_from_interviews`。这是闭环的关键，**不能省**。

### 步骤 7：重建索引

```bash
python skills/shared/scripts/index.py
python skills/shared/scripts/build_mindmap.py
python skills/shared/scripts/validate.py
```

validate 报错就停下来修，不要把不一致的状态留给下次。

### 步骤 8：交付（Claude）

给用户：
- 复盘 md 的路径
- 这场新建/复用了多少题
- 暴露的 top-3 gap（从 propagate 的 stdout 拿）
- 一句建议：下次模拟面试要不要重点刷这场的某几道题

## 写作风格规则

- 中文
- `better_answer` 不要写成教科书，写成"你下次嘴里能蹦出来的那种长度和节奏"——1-3 段，每段 2-4 句
- 数学公式只在不写就答不清的时候写
- 不要在 `my_answer_summary` 里美化候选人，复盘的价值就在于看到真实差距
- 不要在 `better_answer` 里编实验数字。如果原 paper 有具体数字且你能引用，引用并在 `linked_knowledge` 里挂上

## 反模式（不要做）

- ❌ 一场面试只抽 3 个问题然后说"主要就这些"
- ❌ 把追问合并到主问题的回答里
- ❌ Claude 直接 vim 改 frontmatter YAML（让脚本干）
- ❌ 给一个虚构的 url 当 source
- ❌ 跳过 propagate_gaps（gap 没回流 = 闭环断了）
- ❌ 在 review.md 里出现绝对路径
- ❌ 自动创建 knowledge 条目（那是 kb-ingest 的活）

## 最终交付清单

完成后必须确认：
- [ ] `interviews/<iv_id>/meta.yaml`, `raw.md`, `questions.json`, `review.md` 都存在
- [ ] 每个问题卡都有 `better_answer` 且非空
- [ ] `validate.py` 通过
- [ ] 至少一个 gap 写回了 knowledge（如果一场面试啥 gap 都没暴露，要么你太强，要么你抽得太浅——多半是后者）
- [ ] index 重建完成
- [ ] mindmap 重建完成
