# 003 — 首轮目标证据对照实验

执行：2026-10-10 至 2026-10-11；分析：2026-10-11（Asia/Shanghai）  
对应计划：[003-next-experiment](../plan/003-next-experiment.md)  
状态：**Kaggle COMPLETE，结果已取回并分析。不晋升 goal_evidence v1，保留 baseline。** 本次分析未启动新GPU作业。

## 实际结果与研究判断

两组各为同一批16个公开开发游戏、121关、单遍，均分不是Kaggle隐藏榜单分。

| 指标 | baseline | goal_evidence |
|---|---:|---:|
| 平均分 | **49.2502** | **46.8783** |
| 完成关卡 | **72/121** | **68/121** |
| 完整通关游戏 | 5/16 | 5/16 |
| 固定完成集合的得分上限 | 52.5072 | 49.3028 |
| 动作数 | 3226 | 3169 |
| analyzer自报生成tokens | 2,856,116 | 2,922,797 |
| 预算截止取消的游戏 | 11 | 11 |

改进组低2.3719分、少4关。su15从7关降至3关，对总均分贡献-3.0556分，说明差异集中且单次结果波动大；不能删除该游戏再声称上涨。两组相同的5个游戏全部通关，无崩溃或截止后继续计分。完整逐游戏结果见[分析报告](../../research/003-results-analysis.md)、[派生汇总](../../experiments/003-analysis/summary.md)。

更关键的是：改进组16次初始指导、1次目标marker、**0次有效反证提示**。唯一marker回顾的是r11l已经成功的第1关，真实帧已在第2关，拒绝正确，不是hook故障。本轮实际检验了额外指导文字及其报告约定，尚未实际检验到计划中的反证反馈机制。详见[原始轨迹复盘](../../research/003-intervention-postmortem.md)。

因此：保留基线；不原样重跑此版本；不从一次下降推断“目标推断方向无效”。下一轮先用现有失败轨迹研究无需特殊自报marker的观察证据表达，见[004计划](../plan/004-observation-evidence.md)。

## 实际GPU效率与配额

- 本程序实测 **9875.01秒=2.7431h**；加载/初始化526.54秒（8.78分钟，5.33%），两组解题窗口9284秒（94.02%），其他启停/收尾约64.47秒。
- GPU逐分钟采样均值为 **91.22% / 92.17%**；它是解题阶段的稀疏采样，不是整段会话连续测量。解码请求平均约9路、上限10路；没有长时空转证据。
- 服务端两次明确记录cache flush成功；输入token加权缓存命中94.07% / 93.60%。整session约589.08个服务端输出token/秒。
- 模型只加载一次，结束后正常停止，两组无残留worker线程，无父进程硬杀。11个cancelled均与预算截止对应，不是崩溃。
- 10/11精确账户快照：已用19226.113756秒，**剩余24.6594h**，预留0；10/17北京时间08:00刷新。
- 账户相对运行前增加2.9954h，比本程序计时多约908秒。快照涵盖全账户，无法把差额完全归因于此实验或框架空转。

详见[效率报告](../../research/003-efficiency-analysis.md)、[效率JSON](../../experiments/003-efficiency.json)、[配额快照](../../experiments/003-quota-after.json)。当前没有证据支持先重写serving或增加并发；GPU时间应优先用于更有效的研究干预。

## 分析后已完成的本地修补（尚未重新上GPU）

1. 汇总工具保留历史计数，并新增analyzer自报/未归属tokens口径。原history+final分别漏掉45,501和108,880个analyzer自报tokens，不能再当总生成量；服务端输入非零，旧uncached_input=0表示字段未记录。
2. 目标事件增加完整runtime路径、dispatch ID、真实帧和拒绝原因；触发策略、指导文字与拒绝条件均未改变。
3. OFFLINE研究入口关闭多余的warmup RESET。原版A额外RESET落在bp35，B落在sk48；父进程已等待模型ready，下一轮无需这个非确定性额外动作。正式比赛入口未改。
4. 从实际v1 Notebook的嵌入payload保存当时源码至`experiments/003-source/`；原Notebook与下载输出未重写。当前本地代码修补不冒充已经实跑。

修补以人工CPU重放/数据重算核对，没有新增测试文件或GPU运行。

## 实验启动记录

Notebook：[ccjjllt/arc3-003-goal-evidence-ab](https://www.kaggle.com/code/ccjjllt/arc3-003-goal-evidence-ab)，版本1，私有、断网、RTX PRO 6000，CLI hard timeout10800秒。构建Notebook SHA256：`61fb18ca348e47b4f00bb546de80965870da6ab85680f86c5431c3b946761af8`。未正式提交比赛。

实际执行命令：

```bash
kaggle kernels push -p notebooks/003-goal-evidence-ab -t 10800 --accelerator NvidiaRtxPro6000
```

CLI返回`Kernel version 1 successfully pushed`，随后MCP状态RUNNING，metadata确认私有/断网/RTX及原版Docker。普通`kernels logs`读取持久化日志，运行时可能为空；改用`kernels logs -f`成功获得实时输出。

启动日志确认：原版harness patch成功、Python3.12、离线Pennyroyal安装完成、CUDA可用、GPU确为RTX PRO6000 Blackwell。随后SGLang返回`READY after 475s`；从Notebook研究计时起约527秒进入baseline组，16游戏、4642秒预算。

启动前预期总时长约527+2×4642=9811秒（2.73h），另加两组取消清理/汇总，受10800秒硬限；最终实测9875.01秒。

## 配额与实验范围

运行前MCP返回：总GPU配额30h，已用8442.630秒（2.345h），预留0，剩余约27.655h；下次刷新北京时间10/17 08:00。原始记录在 `experiments/003-quota-before.json`。

首轮限定一次Notebook、最多3h，预计2.8h。16游戏各跑baseline与goal_evidence一遍；组间仅重启CPU harness、共享SGLang模型权重。每组4642秒，10路活跃推理；启动慢时两组预算等量缩短。不是两个独立模型启动，也不是两个9小时Notebook。

## 实际代码修改

- `src/arc3_research/goal_evidence.py`：原ToolAgent的两个方法外增加可关闭的目标证据反馈，记录marker采用、帧匹配、动作反馈和短提示触发。只做目标干预，动画留下一轮。
- `src/arc3_research/run_arm.py`：每组fresh加载bundle、独立OFFLINE游戏session与全局调度器，保存arm metadata/目标证据；不启动GPU模型。
- `src/arc3_research/session_runner.py`：复用已加载SGLang，等预算顺序运行两组、采集GPU利用率、收尾终止自己创建的进程组。第一组基础运行失败时停止继续花配额。
- `scripts/build_experiment.py`：从固定原版生成私有研究Notebook，保留其harness patch、安装与serving配置，把自有源码嵌入Notebook；不会上传凭证或整份本地研究缓存。
- `scripts/summarize_experiment.py`：人工调用的结果汇总工具，按真实benchmark schema输出JSON/Markdown和逐game对照。
- `experiments/003-goal-evidence.json`：游戏集合、预算与比较限制。
- `notebooks/003-goal-evidence-ab/`：构建出的Notebook、CLI metadata及source hashes。

所有自有验证由人工启动，没有测试文件或测试套件。

## 已完成的手动检查

1. 对真实patched ToolAgent/Python sandbox人工检查干预开关、一次提示、事件去重、过时帧/终局情况及原dispatch flags。使用合成反馈，不是模型效果实验。
2. 结果汇总脚本读取作者原始100条轨迹，得到46.4930、ceiling49.1227、417关、17,504,777 tokens，与前轮重算一致。这仍是作者历史结果。
3. 检查精确源码中的Benchmark teardown、global scheduler生命周期与超时，选择独立CPU子进程避免跨组状态污染。
4. 自有模块已人工语法编译检查；本轮Kaggle运行已确认模型加载与真实推理。
5. 实际bundle的CPU核查通过pickle恢复、solver deepcopy/setup/teardown、真实ToolAgent构造、干预开关和16游戏prefix解析；未请求模型，未作效果结论。

## 结果与限制

已得到本项目首轮强模型公开开发结果，未正式提交比赛。仅一次A/B且固定顺序、无共同请求seed、共享模型服务，结果用于筛选，不作统计显著性结论，不外推隐藏榜单。零次反证触发限制了对原研究机制的解释。

原件位于`runs/003-goal-evidence-ab/`，派生结果位于`experiments/003-analysis/`；下轮设计继承本轮负结果、配额和已定位的测量问题。
