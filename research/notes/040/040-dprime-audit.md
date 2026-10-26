# 040 D-prime 独立算法审查

2026-10-26。本轮新代理只读审查已下载的 tantan D-prime v2 cell17、009实际正式Notebook和其匹配runtime，未联网、调用模型、GPU或提交。已知公开卡片33.55仍未绑定具体得分版本，因此以下只评价机制和兼容性。

## 来源与运行时身份

公开源码为`research/snapshots/2026-10-25-strategy/notebook-sources/tantan0327__arc3-franzen-dprime/arc3-franzen-dprime.ipynb`。009正式v2的SHA256为`203da467cb0534fdf50b5683a55a524e647023e0d490524c59f2fda9a73b5dd5`。

本地审查的tool_agent、solver、priority_scheduler源文件Git blob分别为`84a9cdda…`、`e40976c6…`、`14bb787f…`，与009 patch记录的目标blob前缀逐一相同。因此未用到另一轮实验残留的调度代码。

## 真实语义与安装要求

- 公开D-prime的`cost_multiplier`不是基线0.5–2的归一化成本比，而是本游戏已完成关卡的平均生成token数；未完成首关时为0。必须同时替换`ProgressPace`和`priority_value`，只换公式会产生单位错配。
- 每次关卡转换，原harness将`session_generated_tokens - tokens_at_level_start`记入pace，随后重置该关动作/token起点，`_pace_last_completed_level`防止重复记账。公式输入level是当前待完成关号，等于已完成关数+1；最后赢局没有下一次调度需求。
- 009和公开Notebook均启用score normalization及remaining tail lookup，所以`_maybe_handover`会传入公开`total_levels`。公开公式将总关数裁剪至6–10；不应擅自换成隐藏环境或按历史列表推导的值。
- `SCALE=1000`用于统一整数优先级；在同一公式内不会改变排序。它比基线约100的尺度大，但正常输入仍远低于1,000,000的缓存band间隔。
- `session.play`是同步工作线程方法。原函数先配置gate有限时钟，再执行initial acquire；正式31920秒上限满足fade要求。模型分析器在每次游戏play前构造，因此安装须在创建分析器/bm.run之前，不要求改pickle协议。
- fade0.4表示最后40%总时长线性缩小未来关卡B项；它不增加硬停止条件，也不是对生成token的硬上限。

## 具体排序风险

直接从公开cell17提取其原始函数进行CPU计算，没有使用新helper作为oracle。18,000组正常N6–10、合法当前关、非负动作/token/pace组合全部有限非负，最大整数优先级41,428，未跨缓存band。

| 场景 | phi=1 | phi=0.5 | phi=0 |
|---|---:|---:|---:|
| 尚未开始的10关游戏：L1，动作0，tokens0，pace0 | 17,000 | 9,000 | 1,000 |
| 已到第3关的6关游戏：当前关动作0，tokens500,000，前两关平均pace1,000 | 19,879 | 11,879 | 3,879 |

这个普通非负输入反例说明：开启fresh pricing后，一个前两关便宜、当前关长期空想少动作的游戏仍会压过未开始的10关游戏；fade到0也不解除该排序。原因是廉价历史pace提高A，加上C保留下限。策略没有aging或覆盖保底，不能保证110题均开始。这是公开策略本身的取舍，不是分母为零或安装错误。

另一例是phi=1时，10关游戏的最后一关初始值5,500，第一关已花100k tokens/10动作仍为16,544。较大的未来B项可能在前60%时间压过接近终局的题，之后才随fade减弱。其是否有净收益只能真实验证。

## 推荐的隔离范围

建议040采用公开已有的`PRICE_FRESH=0`开关，保留009的未开始题绝对优先；只隔离D-prime公式、平均token pace及fade0.4，继续10streams。关闭fresh pricing时，helper不应包裹`session.play`或`gate.acquire`，原始绝对fresh-first路径应逐字保留。

这项选择消除了上述撤掉覆盖保护所新增的饥饿路径，仍保留公式改变既有题续跑顺序的作用。它不是33.55方案的完整复现，也没有提分证据；不要为此新增aging参数或静默修改公开系数。

027停损的是经验80k未来关卡查表，D-prime则改变A/C、pace单位、B系数与fade。两者不能当作同一机制；027的失败也不足以证明D-prime有效。040仍需CPU确认helper与公开原公式一致、有限时钟/实际gate兼容、开关关闭后原fresh路径保留，再进行必要GPU检查。

[CPU数值与源身份原件](../../../experiments/040-preparation/independent-algorithm-review.json) · [027停损结果](../027/027-tail-confirm-results.md)
