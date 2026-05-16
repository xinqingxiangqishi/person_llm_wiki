---
name: wiki
description: 个人知识库管理。创建/更新 wiki 概念条目，查看待补的 gap，搜索已有知识，标记 gap 为已解决。适用场景：用户说"搜一下 GRPO"、"知识库缺什么"、"我想补一下 RL 这块"、"新建一个 DAPO 的 wiki 条目"、"帮我总结一下 post-training 的知识"、"这个 gap 我搞清了"。
---

# Wiki Skill

个人知识库的管理入口。wiki/ 是**合成层**——整合来自面试复盘（interview-review 暴露的 gap）和前沿热点（frontier-ingest 引入的论文）的知识，形成你自己的概念节点网络。

## 数据契约

读 `skills/shared/CONTRACTS.md`（wiki 条目 schema 在 §1）。这个 skill 写入：
- `llm-kb/wiki/<kn_id>.md`（新建或更新）
- `llm-kb/index/all.json`（流程末尾重建）

不写入 frontier/ 或 questions/（那是各自 skill 的活）。

## 四种使用场景

### 场景 A：新建 wiki 条目（从头建，不依赖 frontier 或 interview）

触发语："新建一个 XX 的 wiki 条目"、"我要给 DAPO 建个知识卡"

**流程**：

1. 问用户（一次问完）：
   - 标题（概念名称）
   - type（concept / method / framework / tool，给建议）
   - topics（从已有 topics 里挑，新增要告知用户）
   - 来源（可选：URL、paper 名、"暂无来源"）

2. Claude 生成正文草稿（按 CONTRACTS.md §1 的正文结构）：
   - 一句话总结
   - 核心内容
   - 与相关概念的对比
   - 如果用户给了来源，从中提炼；没有来源就写 stub 骨架留待填充

3. 调脚本创建文件：
   ```bash
   python skills/wiki/scripts/new_wiki.py \
     --slug "<slug>" \
     --title "<title>" \
     --type <type> \
     --topics "<comma,separated>" \
     --source-url "<url_or_empty>" \
     --source-kind "<paper|blog|doc|other>" \
     --source-citation "<citation>"
   ```

4. Claude 把草稿正文写入脚本生成的文件（替换 placeholder body）

5. 重建索引：
   ```bash
   python skills/shared/scripts/index.py
   python skills/shared/scripts/build_mindmap.py
   python skills/shared/scripts/validate.py
   ```

6. 交付：条目路径 + 提示"有没有相关的 frontier 条目需要链接？用 `frontier-ingest` 里的 `link_wiki.py` 可以建立双向链接"

---

### 场景 B：更新已有 wiki 条目

触发语："更新一下 GRPO 的条目"、"给这个 wiki 加点内容"、"我搞清了 GRPO 的 group size 问题"

**流程**：

1. 读 `llm-kb/index/all.json`，找到对应条目（或让用户确认 kn_id）
2. 读当前条目内容，展示给用户看当前状态（包括 gaps 列表）
3. 和用户确认要做什么：
   - 更新正文某个章节
   - 清除某个 gap（`--clear-gap`）
   - 修改 status
   - 添加 source

4. 调脚本：
   ```bash
   python skills/wiki/scripts/update_wiki.py \
     --id <kn_id> \
     [--status <new_status>] \
     [--clear-gap "<gap_text>"] \
     [--add-source-url "<url>" --add-source-kind <kind> --add-source-citation "<citation>"]
   ```

5. Claude 手动编辑正文部分（如果用户要更新内容，Claude 直接改 body，不改 frontmatter）

6. 重建索引（同上）

7. 如果清除了 gap 且 gaps 变空 + status=needs_more，脚本自动提示"gaps 已清空，是否把 status 翻回 reviewed？"

---

### 场景 C：查看待补的 gap（知识库缺什么）

触发语："知识库缺什么"、"我要刷哪些知识点"、"有什么 gap 还没填"

**流程**：

```bash
python skills/wiki/scripts/list_pending.py [--topic <topic>] [--status needs_more]
```

脚本输出所有 `status=needs_more` 或非空 `gaps` 的条目，按 topic 聚合。Claude 读取后：
- 按优先级排序（gap 数量多的先显示）
- 对每个条目，列出未解决的 gap 列表
- 建议："这几个 gap 可以用 frontier-ingest 搜论文补，这几个可以直接写"

---

### 场景 D：搜索 wiki

触发语："搜一下 GRPO"、"wiki 里有没有关于 RL 的"、"列出所有 post-training 相关的条目"

**流程**：

读 `llm-kb/index/all.json`，按关键词或 topic 过滤，展示匹配条目的摘要（id、title、status、gap 数、关联 frontier 数）。Claude 展示结果，用户可以继续问"给我看 kn_xxx 的详情"。

---

## 写作风格规则

- 中文
- wiki 条目正文是给**自己未来复习**用的，写成"你下次看还能快速理解"的密度
- 一句话总结要真的是一句话，不要废话
- "与相关概念的对比"章节是最有价值的部分，要写清楚区别在哪，不要写"两者都很好"
- status 规则：
  - `stub` = 只有骨架，正文基本为空
  - `draft` = 有内容但来源不确定或有明显缺失
  - `reviewed` = 自己满意，来源可追溯，gap 为空
  - `needs_more` = 有 gap 需要填（一般由 propagate_gaps 自动翻）

## 反模式（不要做）

- ❌ 在 wiki 条目里编实验数字或编 URL
- ❌ 手改 frontmatter YAML（用脚本）
- ❌ 把 frontier 的原始摘要直接复制粘贴进 wiki（wiki 是合成层，要有自己的理解）
- ❌ 跳过 validate（双向链接不一致很难手动发现）
- ❌ 新建 wiki 条目时不告知用户新增了哪些 topic

## 最终交付清单

完成后确认：
- [ ] 写入/更新的条目 frontmatter 必填字段齐全
- [ ] 正文非空（至少一句话总结 + 核心内容）
- [ ] 如果清除了 gap，gaps 字段已更新
- [ ] `validate.py` 通过
- [ ] index 和 mindmap 重建完成
