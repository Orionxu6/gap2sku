# 1688「牛顿」与 Gap2SKU 的协作边界

## 结论

牛顿适合放在 Gap2SKU 的上游，承担 1688 站内找品、候选货源、店铺经营和询盘辅助；Gap2SKU 继续负责把这些材料变成可追溯、可审查、不能被 LLM 绕过的新品打样决策。两者不是替代关系。

截至 2026-08-15，本项目能检索到的「牛顿智能体」产品说明主要来自二手行业文章，尚未找到可公开核验的 1688 官方开发者 API 或正式产品文档。阿里巴巴集团官方资料只能确认 1688 是其国内批发采购平台，并不能单独证明牛顿的具体能力。因此 v3.0 不把第三方文章中的功能描述写成已验证事实，也不保存 1688 登录态或模拟人工绕过平台限制。

- [阿里巴巴集团对 1688 的官方介绍](https://www.alibabagroup.com/zh-HK/about-alibaba-businesses-1941299332078632960)
- [行业文章中的牛顿能力描述（非官方，仅作待核验线索）](https://www.10100.com/article/147376527)

## 推荐接法

1. 用户在牛顿或 1688 内完成账号授权、搜索和候选筛选。
2. 通过官方导出、用户手动导出或未来经核验的授权 API，把候选供应商保存为脱敏 JSON。
3. `NewtonExportAdapter` 拒绝 Cookie、Token、密码等会话材料，只导入来源 URL、导出时间、文件 hash 和页面可见事实。
4. 导入结果固定为 `PUBLIC_LISTING_SIGNAL / AUTHORIZED_PLATFORM_EXPORT`，只允许进入 Supplier Funnel 和 RFQ 目标池。
5. Prototype Designer 锁定 `SampleSpec` 后，Supply 用完整 RFQPack 在牛顿/1688 内询盘。
6. 用户导出供应商明确回复，由 `rfq.import_response` 校验 `rfq_ref + sample_spec_hash + source_document_hash` 后，才能形成 `SupplierQuoteSet`。
7. Economics 仍需 BOM、包装、物流、平台费、税费和退货假设；展示价或牛顿推荐价不能直接变成“验证利润”。

## 牛顿可以真正帮到的地方

- 扩大供应商候选池，按工艺、地区、MOQ、交期和页面可见能力快速预筛。
- 把跨境爆品或竞品特征映射到 1688 货源，作为机会与可制造性研究的上游输入。
- 在用户授权范围内辅助询盘整理、经营诊断和素材生成，减少重复运营工作。
- 将平台原生的商品、供应商和沟通上下文导出给 Gap2SKU，避免未授权爬取登录态页面。

## 不能交给牛顿或公开页面直接决定的内容

- 不能用站内展示价代替与锁定规格绑定的 RFQ。
- 不能用供应商自述代替工厂身份、工艺能力、样品与量产一致性证明。
- 不能用生成图片代替 CAD、结构、耐久、材料或合规证据。
- 不能由牛顿、Accio、DeepSeek 或任何 Worker 覆盖 Reviewer 的确定性门禁。

## 本地适配器输入

```json
{
  "exported_at": "2026-08-15T00:00:00Z",
  "items": [
    {
      "supplier_name": "示例供应商",
      "source_url": "https://detail.1688.com/example",
      "observed_facts": {
        "displayed_moq": 500,
        "displayed_process": "铝合金加工"
      }
    }
  ]
}
```

该格式禁止包含 API Key、Access Token、Cookie、密码或 Authorization 头。
