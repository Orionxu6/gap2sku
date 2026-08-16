# AgentTeams 午睡枕真实证据协作任务

把下面一整段发送到 `gap2sku-definition` Team Room。网页通过 Matrix Human Observer 发送时会附带真实 `m.mentions`，不是前端伪消息。

```text
@Leader

请组织七名 Worker 对项目 nap-pillow-cn-20260811-001 做一次“真实证据、决策前补证”的协作复核。

本轮唯一运行标识：`{{RUNTIME_RUN_ID}}`
所有委派 Task ID 与 `collaboration.submit_handoff.task_id` 必须包含该运行标识；禁止复用历史 Task 或 Handoff。

边界：
- 389 条评论是 REAL 定向采样证据，只能支持痛点与冲突发现。
- 当前没有真实供应商 RFQ、BOM、耐久测试和材料安全检测。
- 所有概念图都是 SYNTHETIC_CONCEPT，不是 CAD、供应能力或安全证据。
- Agent 消息不是业务状态；不要在聊天里声称任务已 ACCEPTED。

编排要求：
1. Market 与 Supply 并行。Market 读取真实评论与 PainPointSet；Supply 检查 RFQ/SupplierQuoteSet 缺口。
2. Prototype Designer 检查三个概念、锁定的 Demo SampleSpec 与 RenderManifest 是否一致。
3. Economics 必须在 Supply 之后读取当前经济 Artifact；缺真实报价时不得生成验证利润。
4. Compliance 检查儿童产品分类、材料、测试、标签与宣称缺口。
5. Reviewer 独立读取 ReviewResult，不能替 Leader 改结论。
6. 每名 Worker 完成后必须调用 `collaboration.submit_handoff`，提交 summary、artifact_refs、status、data_mode=REAL，且 task_id 包含 `{{RUNTIME_RUN_ID}}`；只发聊天不算结构化交付。
7. Leader 汇总各 Handoff，调用自己的 `collaboration.submit_handoff` 写入 DECISION_RECORD advisory，并在 Team Room 给出 GO / REVISE / NO-GO 建议、推荐方案与下一轮任务。

预期边界：当前真实证据路径应为 REVISE；若任何 Agent 建议 GO，必须指出能解除 RFQ、BOM、耐久与材料证据门禁的具体 Artifact，否则视为越权。
```

合成 GO 与耐久 NO-GO 是独立回归，不得混入本次 REAL Team Room 结论。
