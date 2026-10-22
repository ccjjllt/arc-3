# 018 — 观察状态保真进展

日期：2026-10-18。状态：**jiyujia v1 已COMPLETE，67.0106→63.7827，22→22关，全通2→1；两游戏有真实纠错，ar25仍转抄误用，不晋升/不扩跑。** 对应[完整分析](../../research/notes/018/018-results-analysis.md)、[冻结计划](../plan/018-observation-grounding.md)。

## 10/18 实际启动

用户明确授权使用Kaggle CLI和jiyujia GPU，并要求尽量提高利用率。北京时间14:57:42成功push v1；之后状态RUNNING，拉回36 cells与冻结源码逐字一致。远端preflight 1.539秒通过、无网络/模型/游戏动作，日志确认NVIDIA RTX PRO6000 Blackwell、SM120。[私有Notebook](https://www.kaggle.com/code/jiyujia/arc3-018-observation-grounding)、[启动记录](../../experiments/018-launch.json)、[远端源码核对](../../experiments/018-launch-checks/remote-check.json)。

通用配额API仍报总6h/已用超额，但平台实际已接受并运行此RTX作业，不能由该API推断RTX无法启动。保留原始返回，不猜原因。4游戏筛选保持不变：015相同规模求解GPU时间加权94.01%/93.48%，扩大短池会减少核心游戏暴露；两臂复用一次加载，每10s采样，完成后报告实际利用率。利用率不是有效吞吐或最优效率保证。[依据](../../experiments/018-launch-checks/utilization-rationale.md)。

## 在线结果与核验

- 已取回两臂全部输出，八局逐关评分与保存结果一致；冻结源码、实际prefix、工具schema、同预算、cache flush、排空和截止检查通过。修复离线分析器对两条默认requests.jsonl响应的归属后，八局请求/响应/usage全部对账；运行Notebook未改。
- 432个去重调用经Codex代理静态审阅；ft09/tr87候选有具体纠错链，baseline也有自然纠错；ar25仍将正确(8,18)转抄为(8,17)后投入搜索。不是无采用，但完整采用门与净收益均未过。
- 会话内部2587.887秒（0.71886h），启动559.847秒；求解GPU采样均值91.75%/90.40%、中位数均98%。这不是精确Kaggle计费；账户配额增量2.65832h无法全部归属本次。服务已关闭，没有新正式提交。
- [派生报告](../../experiments/018-analysis/report.json)、[采用审阅](../../experiments/018-adoption-review.json)、[独立像素复算](../../experiments/018-cell-proof.json)、[GPU阶段](../../experiments/018-analysis/gpu-phases.json)。初始日志归属误报保留在launch-checks，未改写原件。

## 已完成实现

- 新增 [observation_grounding.py](../../src/arc3_research/observation_grounding.py)，使用原底座已有 `ARC3_SYSTEM_PROMPT_PREFIX`。前缀130词、873字符，只在候选独立CPU进程设置；baseline原提示保持不变，不新增工具或改观察/动作接口。
- 明确核验当前帧的crop边界及关键编码格子，区分实际颜色掩码与需要交互证据的物理足迹。像素数相同不等于几何正确，提示也不自动纠正错误。
- runner/config/build支持单因素候选，调度冻结remaining/pace0。preflight在启动模型前拒绝非空外部prefix，验证候选prompt恰为prefix+baseline，并恢复环境。
- 冻结四游戏ft09/tr87/ar25/sb26，各臂1000s、10流容量（实际仅4游戏并发）、1pass、warmup0、硬限5400s；诊断、deadline、cache/排空合同两臂相同。[配置](../../experiments/018-observation-grounding.json)。
- 构建 [私有离线研究Notebook](../../notebooks/018-observation-grounding/experiment.ipynb)，jiyujia账号、RTX PRO6000；36 cells，保留原始模型/数据附件和正式009。

## 已通过的验证

[最终CPU报告](../../experiments/018-grounding-cpu/cpu-20261018T054036Z/report.json)为 **20/20 passed**。人工命令脚本为 [check_018_grounding.py](../../scripts/checks/check_018_grounding.py)，复现入口及本地依赖边界见[准备说明](../../experiments/018-grounding-cpu/README.md)。

- 实际导入冻结ToolAgent及solver，加载原Notebook完整setup_env后构造baseline/candidate；candidate系统prompt逐字等于prefix+baseline，已有baseline实例不变。
- 工具schema、ToolAgent行为方法对象、会话play对象、内存/运行控制不变；已有/重复prefix拒绝，卸载及空白原值恢复正确。
- 配置拒绝混入其他候选、改变调度、关闭preflight/deadline及任意prefix注入；实际preflight成功，冲突环境按预期失败。
- Notebook经nbformat校验；29个代码cell经真实IPython转换后编译；19个helper用原生writefile写到临时目录，字节hash与manifest一致；原大patch未改变、保留末尾换行且`git apply --stat`可解析。
- 无网络/HTTP/模型/sandbox执行/引擎动作。检查运行了构造、配置和打包路径，没有实际执行run_arm的游戏循环或KaggleGPU路径。

Notebook SHA256：`731fd4335c20bcec86ea93f3be9449be82175a28ea6835582090b3b3999aefc7`。前缀 SHA256：`7643053cbe36f7cb3d0a6929cc7ddb3de6057ad96ed358068e23b7ebecfd62f7`。独立审查重新核对源码/manifest/Notebook哈希与保存的实际prompt一致。

早期CPU检查失败记录完整保留：本机旧临时SDK/依赖目录不完整，以及检查进程最初未载入完整baseline环境。已用本地官方wheel和独立临时依赖目录恢复，并在完整环境下重跑通过；这些失败不是模型效果实验。最终依赖来源与恢复材料记录在CPU目录，未修改竞赛运行依赖。

## 下一步

018当前版停止，不进入全25或倒序。本轮两游戏的真实纠错不能证明提示的因果收益；四游戏单次均分回退也不证明所有表示干预无效。后续若研究表示，要针对正确提取结果到下游输入之间的失真，而非继续加长全局提醒。

下一优先级回到017独立FP8 PLE吞吐/数值可行性路线，先CPU核验权重、loader、scale/dequant与固定请求方案，再决定GPU投入；不叠加018、也没有直接启动下一GPU会话。正式009保留。
