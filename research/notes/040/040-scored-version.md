# 040 来源与分数绑定边界

2026-10-26。官方SDK重新读取 `tantan0327/arc3-franzen-dprime`，currentVersionNumber仍为2，Notebook源码SHA256 `2d21f788f48c842a1c50785c6e1efa84ed1962385ab4b87c7fbfef214f9ba79e`，与10月25日已审快照逐字节一致。模型、两个数据集和Docker均与009使用的公开Franzen栈一致。下载源码仅供静态检查和公式提取，没有执行整本Notebook。

10月25日公开列表卡片显示33.55，但该观察未绑定具体得分version/scriptVersionId。当前API只提供current version与源码，不返回该分数的对应版本。本轮浏览器导航读取超时，官方页面HTTP读取404，搜索没有补足绑定证据。不能把33.55当作已确认属于v2的可复制成绩。

这个边界不阻止把已审公开算法当作新候选验证：040明确是**009固定环境＋D-prime公式／mean-token pace／0.4 fade，保留原fresh-first**，不是33.55全本复现。PRICE_FRESH=False是公开源码已有选项；本轮独立数值审查发现True可令正常停滞题压过未开始题，因此选择False。

准确信息见[官方API源码与manifest](../../snapshots/2026-10-26-dprime/manifest.json)、[历史卡片原件](../../snapshots/2026-10-25-strategy/notebook-public-scores-ui.json)、[策略风险审查](040-dprime-audit.md)。正式是否提高分数以本队后续提交结果为准。
