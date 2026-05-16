---
name: frontier-ingest
description: 把论文/技术报告/博客沉淀为前沿热点条目，存入 llm-kb/frontier/，并与 wiki/ 建立双向链接。适用场景：用户说"帮我总结这篇论文"、"加到前沿热点"、"解读这个技术报告"、"搜一下最近 XX 方向的热点"、"找几个不错的 agent 开源项目"。
---

# Frontier Ingest

把一篇论文/技术报告/博客从 URL 或文本变成：
1. 一份 `fr_<yyyy>_<slug>.md`，存入 `llm-kb/frontier/`，自包含，供你后续复习
2. 与 `llm-kb/wiki/` 里相关概念节点的双向链接
3. 如果 wiki/ 里还没有对应概念，提示用户是否要新建 wiki 条目

每篇报告一个文件，不合并，不拆分。

## Local-First Rule

`web_fetch` 和 `web_search` 只用于明确公开的技术内容（论文、官方博客）。
**永远不要**把公司名（非公开）、个人信息发出去。

## 数据契约

读 `skills/shared/CONTRACTS.md`（frontier 条目 schema 在 §2，wiki 条目在 §1）。这个 skill 写入：
- `llm-kb/frontier/<fr_id>.md`（新建）
- `llm-kb/wiki/<kn_id>.md` 的 `linked_frontier` 字段（通过 `link_wiki.py`，不要手改 YAML）
- `llm-kb/index/all.json`（流程末尾重建）

## 工作流

严格按顺序。

### 步骤 1：判断输入类型（Claude）

根据用户的输入判断入口：

| 输入形态 | 处理方式 |
|---|---|
| 一个 URL（arxiv/blog/官方文档） | `web_fetch` 抓正文，进入步骤 2 |
| 一段文本（用户直接粘贴摘要/正文） | 直接进入步骤 2，url 写 `"N/A"` |
| "搜一下最近 XX 方向" | `web_search` 拉候选列表，**让用户挑选**后再走步骤 2；不要自动全部沉淀 |
| "找几个 XX 开源项目" | `web_search` 拉候选，让用户确认；type 写 `hot_topic_summary` |

### 步骤 2：两步提取（Claude）

**第一步：提取事实**（输出给自己看，不展示给用户）

从原文提取：
- 标题、作者、发布日期、URL
- 论文/报告要解决的核心问题（1 句话）
- 方法的关键组件（列点，尽量从原文提取，不要过度概括）
- 关键实验数字（如果有）
- 这篇和哪些已有方法/概念相关（这决定 linked_wiki 的候选）

**第二步：生成结构化条目**

按 CONTRACTS.md §2 的 frontmatter schema 填写，正文按以下结构：

```markdown
## 一句话总结
一句话说清楚这篇的贡献是什么、和已有工作的核心区别在哪。

## 背景与动机
这篇为什么要做，解决了什么问题。2-4 句。

## 核心方法
主要技术创新。每个关键点一段。有公式写公式，但只在不写清楚不了的时候写。

## 关键实验结论
数字要真实，来自原文。不要写"在多个 benchmark 上表现更好"这种废话，写具体是哪个 benchmark，提升了多少。如果原文没有数字，如实说。

## 与相关工作的关系
和哪几篇关联最紧密，区别在哪里。这部分决定 linked_wiki 填什么。

## 待深入
你读完还没搞清楚的点，或者值得 deep-dive 的子问题。
```

### 步骤 3：确定 linked_wiki（Claude）

读 `llm-kb/index/all.json`（如果存在），查看现有 wiki 条目。判断：
- 这篇报告涉及的核心概念，wiki/ 里有没有对应条目？
- 有 → `linked_wiki` 里填对应 kn_id
- 没有 → 把这些"缺失的概念"记录下来，在步骤 5 后提示用户

**注意**：不要在这个 skill 里自动创建 wiki 条目，那是 `wiki` skill 的活。

### 步骤 4：写入 frontier 条目（脚本）

```bash
python skills/frontier-ingest/scripts/new_frontier.py \
  --slug "<short_slug>" \
  --title "<full title>" \
  --type paper \
  --url "<url_or_N/A>" \
  --authors "<authors>" \
  --pub-date <YYYY-MM-DD> \
  --topics "<comma,separated>" \
  --linked-wiki "<kn_id1,kn_id2>"
```

脚本输出创建的 `fr_id` 和文件路径。Claude 把步骤 2 生成的正文写入该文件（替换 placeholder）。

### 步骤 5：维护双向链接（脚本）

```bash
python skills/frontier-ingest/scripts/link_wiki.py \
  --frontier <fr_id> \
  --wiki "<kn_id1,kn_id2>"
```

脚本在每个 wiki 条目的 `linked_frontier` 里追加 fr_id，同时确保 frontier 条目的 `linked_wiki` 也是最新的（幂等）。

### 步骤 6：重建索引

```bash
python skills/shared/scripts/index.py
python skills/shared/scripts/build_mindmap.py
python skills/shared/scripts/validate.py
```

validate 报错就停下来修。

### 步骤 7：交付（Claude）

给用户：
- frontier 条目路径
- `linked_wiki` 的条目列表（点击可查看）
- 如果有"缺失的 wiki 概念"，列出来并说："这些概念在 wiki/ 里还没有条目，要用 wiki skill 补上吗？"
- 如果这篇暴露了对已有 wiki 条目的补充信息（比如 wiki 条目里对某概念的描述和这篇的描述有出入），指出来

## 写作风格规则

- 中文（除非用户明确要求英文）
- 正文里的数字和实验结论必须来自原文，不要编
- `linked_wiki` 里只填实际在 wiki/ 存在的 kn_id，不要填幻想的 id
- `url` 找不到写 `"N/A"`，不要编 URL
- 一篇论文的多个 contribution 写在同一文件的不同章节，不要拆成多个 frontier 条目

## 反模式（不要做）

- ❌ `web_search` 用在敏感内容上
- ❌ 直接全部沉淀 web_search 的结果（先让用户挑选）
- ❌ 在 frontier 文件里编实验数字
- ❌ 自动创建 wiki 条目（那是 wiki skill 的活）
- ❌ 把一篇论文拆成多个 frontier 文件
- ❌ 手改 wiki 的 YAML frontmatter（让 link_wiki.py 干）
- ❌ 跳过步骤 5（双向链接没维护 = validate 报错）

## 最终交付清单

完成后确认：
- [ ] `frontier/<fr_id>.md` 存在，frontmatter 必填字段齐全
- [ ] 正文 6 个章节都非空（或明确标注"原文无此信息"）
- [ ] `linked_wiki` 里的每个 kn_id 在 wiki/ 里真实存在
- [ ] `validate.py` 通过
- [ ] index 重建完成
