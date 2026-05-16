# LLM Interview Kit — Claude Code 工作手册

这是一个个人 LLM 求职知识管理工具集。**读完这个文件再开始干活**。

## 环境初始化（只需做一次）

```bash
pip3 install pyyaml
```

数据默认存在项目内的 `llm-kb/` 目录，无需额外配置。

---

## 三个 Skill 和触发条件

### 1. interview-review（面试复盘）

**触发关键词**：「复盘」「面试」「面经」「刚面完」「整理一下面试」

**必须做的事**：在回答之前，先读 `skills/interview-review/SKILL.md`，完整按照里面的 **3 步流程**走（ASR 预处理 → 完整分析生成 JSON → 一键写入），**不要跳过任何一步，不要只用文字回答**。核心脚本是 `process_interview.py`，一次调用完成所有文件写入。

### 2. frontier-ingest（前沿热点）

**触发关键词**：「总结这篇论文」「加到前沿热点」「解读这个报告」「搜一下最近热点」「找开源项目」

**必须做的事**：在回答之前，先读 `skills/frontier-ingest/SKILL.md`，按照流程走，调用脚本写文件。

### 3. wiki（知识库管理）

**触发关键词**：「知识库」「wiki」「新建条目」「搜一下 XX」「知识库缺什么」「这个 gap 我搞清了」

**必须做的事**：在回答之前，先读 `skills/wiki/SKILL.md`，按对应场景（A/B/C/D）走流程。

---

## 数据契约

改任何 schema 之前先读 `skills/shared/CONTRACTS.md`。

---

## 铁律（违反了就是坏掉了）

1. **判断在 Claude，写入在脚本** — 所有 YAML 写入走脚本，Claude 不手改 frontmatter
2. **每次写文件后必须跑三个脚本**：
   ```bash
   python3 skills/shared/scripts/index.py
   python3 skills/shared/scripts/build_mindmap.py
   python3 skills/shared/scripts/validate.py
   ```
   validate 报错就停下来修，不要把不一致的状态留给下次
3. **不删历史** — `my_answer_history` 只 append
4. **gap 必须回流** — 面试结束前必须跑 `propagate_gaps.py`
5. **不要只用文字回答** — 用户说"帮我复盘"的目的是把内容存到本地文件里，不是听你讲一遍
