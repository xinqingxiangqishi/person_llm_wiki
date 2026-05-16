# LLM Interview Kit — 设计与交接文档

> 目标读者：未来接手这个项目的 Claude Code（或你自己几个月后回来看）
> 当前版本：v0.2（2026-05）
> 状态：interview-review、frontier-ingest、wiki 均已实现；mock-interview 待建

---

## 1. 这个东西是什么

一套个人化的、本地优先的「LLM 求职知识管理 + 面试复盘 + 模拟面试」工具集。形态是 **3 个 Claude skill + 1 个共享数据目录 + 一组确定性 Python 脚本**。

替代现状：Notion 手动摘抄、Claude 网页对话框临时问、靠记忆关联"上次某公司问过的题"和"前几天读的某篇 paper"。

## 2. 三个 skill 的分工

| skill | 触发语 | 干什么 | 写入 |
|---|---|---|---|
| `interview-review` | "刚面完"、"帮我复盘"、"整理面经" | 把面试文字记录变成结构化复盘 + 问题卡 + gap 回流 | `interviews/`, `questions/`, `wiki/` gaps |
| `frontier-ingest` | "帮我总结这篇论文"、"加到前沿热点"、"搜下最近热点" | 把论文/报告/URL 变成 frontier 条目，与 wiki 建双向链接 | `frontier/`, `wiki/` linked_frontier |
| `wiki` | "搜一下 GRPO"、"知识库缺什么"、"新建 XX 的 wiki 条目" | 个人知识库管理：新建/更新概念节点，查看 gap，搜索 | `wiki/` |

## 3. 两层数据分离（最重要的设计决策）

```
frontier/   原始来源层：每篇论文/报告 = 一个文件，自包含，供复习
wiki/       合成层：每个概念 = 一个节点，整合多个来源，有你自己的理解
```

- `frontier/` 不合并：DAPO 和 GRPO 是两篇论文，就是两个文件
- `wiki/` 不重复：GRPO 这个概念只有一个条目，被 N 篇论文引用
- 两者双向链接：`frontier.linked_wiki` ↔ `wiki.linked_frontier`

这个分离来自 llm_wiki 的 "raw sources → wiki pages" 架构：原始来源是 immutable 的事实记录，wiki 是你理解的合成。

## 4. 设计原则

### 4.1 判断在 Claude，写入在脚本

Claude 负责语义判断（这道题该归哪个 topic、better_answer 该怎么写、这条知识算 concept 还是 method）。脚本负责分配 id、生成 frontmatter、维护双向链接、重建索引、跑校验。

Claude 手动改 YAML 容易把缩进改坏、容易只改一边的反向链接。

### 4.2 数据契约比规则重要

所有 schema 集中在 `skills/shared/CONTRACTS.md`。三个 skill 都引用它。先用一两个月积累真实数据，再考虑 schema v2。

### 4.3 永远不删历史

`my_answer_history` 只 append。进步轨迹比当前快照更有价值。

### 4.4 闭环：gap 必须回流到 wiki

`interview-review` 的 `propagate_gaps.py` 把问题卡的 `gaps_to_fill` 写入对应 wiki 条目的 `gaps`，翻 status 为 `needs_more`。没有这一步，"这道题没答好"会永远停在问题卡上。

### 4.5 本地优先

公司名、面试官姓名、你说过的话可能敏感。一切只在 `llm-kb/` 本地目录处理。`web_search` 只用于明确公开的技术点。

### 4.6 来源可追溯

`frontier` 条目的 `url` 必须真实可追溯。找不到写 `"N/A"`，不要编 URL。

### 4.7 markdown + frontmatter + JSON 索引就够

没用向量库，没用图数据库。现在瓶颈是"东西散、拼不起来"，不是"检索精度不够"。等有几百条，再升级到 sqlite-fts 或 embeddings。

## 5. 目录结构

```
llm-interview-kit/
  skills/
    shared/
      CONTRACTS.md           ← 所有 schema
      common.py              ← 共享工具（MdDoc, kb_root, next_*_id 等）
      scripts/
        index.py             ← 重建 index/all.json（含 wiki + frontier + questions + interviews）
        build_mindmap.py     ← 生成 mermaid 导图（wiki 和 frontier 按第一个 topic 分组）
        validate.py          ← 校验双向链接和必填字段
    interview-review/
      SKILL.md
      scripts/
        new_interview.py
        search_questions.py
        upsert_questions.py
        render_review.py
        propagate_gaps.py
    frontier-ingest/
      SKILL.md
      scripts/
        new_frontier.py      ← 创建 frontier 条目 skeleton
        link_wiki.py         ← 维护 frontier ↔ wiki 双向链接（幂等）
    wiki/
      SKILL.md
      scripts/
        new_wiki.py          ← 创建 wiki 条目 skeleton
        update_wiki.py       ← 更新 status / 清 gap / 加 source（frontmatter only）
        list_pending.py      ← 列出 needs_more / 非空 gaps 的条目，按 topic 聚合
    mock-interview/          ← 待建（§6）

  llm-kb/                    ← 数据目录，通过 $LLM_KB_ROOT 可移到别处
    interviews/
    questions/
    frontier/                ← 前沿热点（每篇一个文件）
    wiki/                    ← 个人知识库概念节点
    index/
    mindmap/
    drafts/
```

## 6. 待建的部分

### 6.1 mock-interview（最后做）

**先决条件**：题库至少 30-50 张问题卡才有意义。

**核心机制**：
1. 选题范围（topic / 公司 / 最近 gap / 低 mastery / 难度区间）
2. 加权抽样：基础权重 = `1 - mastery`；公司 boost ×1.5；最近 gap boost ×2
3. 交互：一道一道问，用户先自评 1-5，再给差距分析 + 追问
4. 沉淀：整个 session 写入 `interviews/`，`round: mock`，`my_answer_history.context: mock_interview`
5. 结束：跑 `propagate_gaps.py`，闭环

**需要写的脚本**：
- `pick_questions.py` — 按 selector 加权抽题
- `start_session.py` — 建 mock interview 目录
- 复用 `propagate_gaps.py`

## 7. 给接手的 Claude Code

按这个顺序工作：

1. **不要重写已有的东西**。所有脚本和 SKILL.md 是端到端设计过的，schema 是稳定的。
2. **任何 skill 写文件之前，先读 `skills/shared/CONTRACTS.md`**。
3. **新 skill 不要直接改 YAML**。Claude 把数据组织成 JSON 或 CLI 参数喂给脚本。
4. **每条 SKILL.md 末尾都要有"最终交付清单"**。强制 Claude 在结束前自检。
5. **新加 skill 时，必须更新 `validate.py`**。
6. `build_mindmap.py` 用第一个 topic 元素作为顶层分组键（不再对 topic 字符串做 split），修 `post-training → post` 这个 v0.1 bug。

## 8. 反模式（不要做）

- ❌ Claude 直接 vim 改 frontmatter YAML
- ❌ 把 schema 改得跟代码不一致（先改 CONTRACTS.md，再改脚本）
- ❌ 一场面试只抽 3 个问题（除非真的就问了 3 个）
- ❌ 把 web_search 用在敏感内容上
- ❌ `better_answer` 里编实验数字
- ❌ 跳过 `propagate_gaps.py`（闭环断了）
- ❌ 让 Claude 凭记忆判断"这道题之前有没有"（必须调 `search_questions.py`）
- ❌ 把 frontier 的原始摘要直接复制粘贴进 wiki（wiki 是合成层，要有自己的理解）
- ❌ 一篇论文创建多个 frontier 文件（多个 contribution 写在同一文件的不同章节）

## 9. 当前文件清单（v0.2）

```
skills/
  shared/
    CONTRACTS.md
    common.py
    scripts/
      index.py
      build_mindmap.py
      validate.py
  interview-review/
    SKILL.md
    scripts/
      new_interview.py
      search_questions.py
      upsert_questions.py
      render_review.py
      propagate_gaps.py
  frontier-ingest/
    SKILL.md
    scripts/
      new_frontier.py
      link_wiki.py
  wiki/
    SKILL.md
    scripts/
      new_wiki.py
      update_wiki.py
      list_pending.py
```

## 10. 第一次使用怎么起步

```bash
# 1. 解压 kit
tar -xzf llm-interview-kit-v0.2.tar.gz
cd llm-interview-kit

# 2. 装依赖
pip install pyyaml --break-system-packages

# 3. 决定 kb 放哪
export LLM_KB_ROOT=~/Documents/llm-kb
mkdir -p $LLM_KB_ROOT/{interviews,questions,frontier,wiki,mindmap,index,drafts}

# 4. 在 Claude Code 里说你想做什么
# "刚面完一场，帮我复盘下" → interview-review
# "帮我总结这篇论文 [URL]" → frontier-ingest
# "新建一个 GRPO 的 wiki 条目" → wiki
```

把 `llm-kb/` 加到 git 单独管，每天 commit。这是你最值钱的东西。
