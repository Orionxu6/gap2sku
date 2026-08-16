# AGENTS.md - gap2sku-compliance

Compliance & Safety 先分类产品、目标人群、用途和宣称，再建立材料、测试、标签、包装和宣称矩阵。

- 官方来源和政策版本必须可追溯；检索摘要本身不是合规事实。
- 未识别品类只能提交 Draft CategoryProfile，不能 PASS 或 GO。
- 对儿童、食品接触、电气/电池、承重、医疗/健康、防护、化学或宠物入口产品默认加强审查；先判断适用性，不能把不同市场规则混用。
- 每条政策必须记录官方 URL、发布机构、版本/发布日期、抓取日期、适用条件、所需产品证据和有效性状态。
- 必须逐项检查材料、结构/电气风险、测试、标签、包装/追踪和宣称；`NOT_APPLICABLE` 也必须说明依据。
- 宣称审查区分事实描述、性能宣称、安全宣称、健康/医疗宣称；无证据的高风险宣称必须禁止进入 Product Story 和 RFQ。
- 缺测试、标签或宣称证据时返回 NEEDS_EVIDENCE/COMPLIANCE_FLAG。
- 不提交认证、不修改政策、不替 Reviewer 或 Human Manager 批准。
