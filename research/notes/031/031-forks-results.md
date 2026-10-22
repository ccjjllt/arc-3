# 031 v1 同状态诊断：未纠正目标像素，不晋升

2026-10-21。实际运行 `zhuating/arc3-031-recorded-state-exact-pixels` v1，平台COMPLETE。这是一次真实GPU诊断，不是正式submission。

| 切点 | A新增关 | B新增关 | A新增动作 | B新增动作 |
|---|---:|---:|---:|---:|
| ft09，原27动作 | 0 | 0 | 2 | 2 |
| tu93，原276动作 | 0 | 0 | 0 | 0 |
| r11l，正常控制 | 0 | 0 | 0 | 0 |

两臂每切点250秒、最多30新增动作；输入帧、消息及保留函数hash相同。每臂独立CPU进程，共用一次RTX PRO 6000模型加载；臂间cache flush确认、退出无残留worker。模型就绪耗时1693.78秒，会话2278.67秒，约0.633小时；不是从CLI余额差额推算的作业账单。远端28个cell源码与冻结本地逐项一致。[汇总](../../../experiments/031-forks-analysis/summary.json) · [源码核验](../../snapshots/2026-10-21-candidates/031-remote-source-cell-comparison.json)

## 关键结果

B的ft09新调用`call_def70a557dd242cf8e0e94c0`实际读取segmentation，但使用`boundary`外接框双重range填充`pieces`，没有读取runs。原帧加真实返回代码CPU复算和该调用stdout一致：P4从真实的`gWg/WOg/WWW`被提取成`gWg/WOW/WWW`；`(row46,col32)`背景g仍被填W。原像素runs明确排除该点。

这是一条真实的新错误调用，不能只把失败归咎于旧历史；也不能由同状态250秒直接推断自然开局无效。B确实收到工具说明中的runs合同，但系统提示的节点字段枚举仍未列runs。该遗漏是可修正的合同不一致，尚未证明它是采用失败的唯一原因。[独立采用审阅](../../../experiments/031-forks-analysis/adoption-review.json)

B两次实际动作都是no-op；另一次尝试被`StaleStateActionError`挡住。末次请求读超时约75.2秒耗尽窗口。两臂均没有新增关卡，所以本轮不能支持全池或正式提交。

## 下一步只允许一次明确变化

保留v1原Notebook、helper与所有负结果。031 v2仅在系统节点字段清单补齐精确runs合同，与原工具说明一致；不增加修复请求、泛化提醒或持久化机制。v2重新冻结helper与正式payload，在独立自然开局的10题、每臂900秒比较中验证采用及收益。v1结果不作为v2效果证据。

若v2有读取机会却仍不消费，或精确像素未带来实际纠错和推进，停止本版，不扩大031、不消耗正式提交名额。只有新的直接增量证据才允许进入全25题比较。

同时完成的限时公开候选刷新没有找到能够绑定准确公开源码版本及高于31.16正式成绩的新方案，不能凭作者队伍分数直接替代当前底座。[公开候选刷新](../../snapshots/2026-10-21-candidates/refresh-summary.json)
