# 018 — 观察状态保真进展

日期：2026-10-18。状态：**候选接入、冻结Notebook和20项人工CPU检查已完成；未push、未启动GPU、没有模型采用或提分结果。** 对应[计划](../plan/018-observation-grounding.md)、[017决策](../../research/017-research-decision.md)。

## 实际完成

- 新增 [observation_grounding.py](../../src/arc3_research/observation_grounding.py)，使用原底座已有 `ARC3_SYSTEM_PROMPT_PREFIX`。前缀130词、873字符，只在候选独立CPU进程设置；baseline原提示保持不变，不新增工具或改观察/动作接口。
- 明确核验当前帧的crop边界及关键编码格子，区分实际颜色掩码与需要交互证据的物理足迹。像素数相同不等于几何正确，提示也不自动纠正错误。
- runner/config/build支持单因素候选，调度冻结remaining/pace0。preflight在启动模型前拒绝非空外部prefix，验证候选prompt恰为prefix+baseline，并恢复环境。
- 冻结四游戏ft09/tr87/ar25/sb26，各臂1000s、10流容量（实际仅4游戏并发）、1pass、warmup0、硬限5400s；诊断、deadline、cache/排空合同两臂相同。[配置](../../experiments/018-observation-grounding.json)。
- 构建 [私有离线研究Notebook](../../notebooks/018-observation-grounding/experiment.ipynb)，jiyujia账号、RTX PRO6000；36 cells，保留原始模型/数据附件和正式009。

## 已通过的验证

[最终CPU报告](../../experiments/018-grounding-cpu/cpu-20261018T054036Z/report.json)为 **20/20 passed**。人工命令脚本为 [check_018_grounding.py](../../scripts/check_018_grounding.py)，复现入口及本地依赖边界见[准备说明](../../experiments/018-grounding-cpu/README.md)。

- 实际导入冻结ToolAgent及solver，加载原Notebook完整setup_env后构造baseline/candidate；candidate系统prompt逐字等于prefix+baseline，已有baseline实例不变。
- 工具schema、ToolAgent行为方法对象、会话play对象、内存/运行控制不变；已有/重复prefix拒绝，卸载及空白原值恢复正确。
- 配置拒绝混入其他候选、改变调度、关闭preflight/deadline及任意prefix注入；实际preflight成功，冲突环境按预期失败。
- Notebook经nbformat校验；29个代码cell经真实IPython转换后编译；19个helper用原生writefile写到临时目录，字节hash与manifest一致；原大patch未改变、保留末尾换行且`git apply --stat`可解析。
- 无网络/HTTP/模型/sandbox执行/引擎动作。检查运行了构造、配置和打包路径，没有实际执行run_arm的游戏循环或KaggleGPU路径。

Notebook SHA256：`731fd4335c20bcec86ea93f3be9449be82175a28ea6835582090b3b3999aefc7`。前缀 SHA256：`7643053cbe36f7cb3d0a6929cc7ddb3de6057ad96ed358068e23b7ebecfd62f7`。独立审查重新核对源码/manifest/Notebook哈希与保存的实际prompt一致。

早期CPU检查失败记录完整保留：本机旧临时SDK/依赖目录不完整，以及检查进程最初未载入完整baseline环境。已用本地官方wheel和独立临时依赖目录恢复，并在完整环境下重跑通过；这些失败不是模型效果实验。最终依赖来源与恢复材料记录在CPU目录，未修改竞赛运行依赖。

## 尚未证明与下一步

框架没有主动插入模型调用或环境动作，但提示可能改变自然请求数、tokens和动作，必须在线记账。当前没有任何“模型会自然校核”“错误减少”“覆盖提升”结论。

下一步在实际GPU额度确认可用后，先执行冻结短筛并逐请求判断至少两游戏自然提取→校核→消费链；具体纠错与原本正确的确认分开。通过后才设计全25与反序。10/18配额接口均报总6h且已用超额，当前按0可规划余额处理，不沿用旧30h。详见[资源证据](../../research/017-competition-update.md#配额出现新约束不能沿用旧余额)。
