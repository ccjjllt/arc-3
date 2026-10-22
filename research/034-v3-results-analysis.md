# 034 v3 结果分析

2026年10月22日。`zhuating/arc3-034-plan-diagnostic` **v3已COMPLETE**，两臂完整，实际运行源码与冻结32个cell一致。两题四次续跑全部新增0关；辅助分支返回了Python工具调用，但都是普通观察脚本，没有规划与预测函数，候选实际动作仍为0。**不扩大v3到完整题池，不正式提交；下一版只修辅助交付接口的语义冲突。**

## 真实结果

| 切点 | A新增关 | B新增关 | A／B续跑动作 | A／B实际结束秒数 |
|---|---:|---:|---|---|
| ft09 cut27，L3开始 | 0 | 0 | 25／24 | 450.03／463.48 |
| su15 cut86，L5开始 | 0 | 0 | 31／40 | 457.89／450.13 |

两题最终均分均为18.25397，无配对分数增益。这个分数包含冻结前缀，只是两个人工指定切点的描述，不是完整25题或正式成绩。实际动作均在450秒窗口内，结束存在在途请求和清理尾部，不能称实际耗时精确相等。[配对汇总](../experiments/034-v3-analysis/summary.md) · [平台最终状态](../experiments/034-v3-final-platform-snapshot.json)

四次续跑各有一个最终主请求缺少response事件，日志汇总的已返回usage因此不是完整生成成本。两臂在同一服务中按B→A运行，不能据单次顺序断言稳定因果效应。[独立完整性审阅](../experiments/034-v3-analysis/integrity-independent-review.json)

## 交付问题改变了 但尚未解决

| 游戏 | 实际输入token | 输出token | reasoning token | finish reason | 全分支处理秒数 |
|---|---:|---:|---:|---|---:|
| ft09 | 4435 | 139 | 0 | tool_calls | 8.125 |
| su15 | 6564 | 131 | 0 | tool_calls | 8.174 |

两份请求的`thinking=false`、named tool choice、4096输出上限均有真实payload证据；`/tokenize`计数与返回usage逐项一致。相对v2的61612／89613输入和4096输出耗于推理，本版确实缩短请求并及时获得了工具响应。由于上下文、思考和工具控制一起改变，只能归因于整体交付设计，不能分别宣称每个开关有效。

两份响应均在事件文件第2行保存：

- ft09提交顶层`current_frame.segmentation`遍历、排序和`print`，输出节点概览。
- su15提交顶层shape／level／step打印、颜色统计和`print`。

两者都没有定义`plan_program(frame)`或`predict(frame, action)`，在`extract`阶段以`Return only function definitions and allowed imports`拒收。脚本没有被运行，也没有获得观察输出。这次不是输出截断、预测失配或真实代码被像素验收误拒。

```text
辅助请求2 → 工具响应2 → 普通观察脚本2
→ 合格规划/预测程序0 → 候选动作0 → 预测检查0 → 反例修订0
```

因此可以确认“长推理不交付”的失败形态已改变，但不能称程序执行或修订机制成立。后续普通主循环中，ft09执行24个动作仍停L3，su15执行40个动作仍停L5；这些动作不能算候选程序消费。[独立程序审阅](../experiments/034-v3-analysis/program-independent-review.json) · [ft09原事件](../runs/034-plan-diagnostic-v3/executable_plan_B/artifacts/ft09-0d8bbf25_B_tool_runtime_state_executable-plan.jsonl) · [su15原事件](../runs/034-plan-diagnostic-v3/executable_plan_B/artifacts/su15-1944f8ab_B_tool_runtime_state_executable-plan.jsonl)

## 下一处应修的是辅助工具语义

实际辅助请求沿用了普通Python工具说明，要求执行临时snippet、优先读取segmentation并用print输出。与此同时，分支system／user提示要求只交付函数定义、不进行打印。两次实际响应与普通工具的观察用法一致。

这是可直接核对的请求矛盾，尚未隔离为唯一因果。下一版用专门的`submit_program`工具接收Python源代码，明确只交付定义、由宿主验收后执行；保留原代码合同、紧凑事实、关闭思考、预算、切点和主循环。它不提供观察执行接口，也不增加额外模型观察轮。若仍未交付，就继续归档交付失败，不能跳到“规则理解差”的结论。

另一个边界是上下文内容：v3的未验证假说字段主要是标签和旧代码，没有保留此前自然语言规则／目标判断；ft09无相关规划函数，su15只有click／invaders／state等控制观察函数。这更接近在紧凑证据下构造程序。若后续代码能交付却目标错误，需要审查是否删掉了必要证据，再决定调整上下文还是规则探测。

## 完整性与成本

运行顺序B→A，共享一次模型加载；A/B当前帧、历史、函数、暂停代码和前缀动作数hash全部相同。两臂cache均首次HTTP200并获独立后端确认，没有实际重试。四份请求hash与fork汇总一致；所有游戏覆盖完整，CPU进程组和GPU服务均已确认关闭。

会话4780.17秒，即79.67分钟；模型启动3828.87秒，即63.81分钟。两个并发游戏的分支处理合计16.30秒，不等于会话额外墙钟或计费时长。新读共享GPU余额约2.84小时，足够下一次7200秒上限的切点诊断，不足以再承诺完整25题双臂及启动。

上传API此前返回空响应，早期回读仍是旧版；后续确认实际保存并运行的是唯一新版本3、原989878字节候选。不能把早期空响应当最终失败，也没有证据证明上传大小是根因。实际源码已归档；期间制作的xz包装没有在v3运行。[运行源码](../experiments/034-v3-source/) · [远端逐cell核验](../experiments/034-v3-remote-source-check.json) · [启动记录](../experiments/034-v3-launch.json)

## 执行决策

继续保留009 v2／57101330／31.16。v4只检验辅助专用提交工具能否把观察脚本变成可验收短程序；仍然使用相同切点、每题450秒／60动作、单请求60秒、全分支120秒、累计最多3个受检动作。用于上传的数据可无损合并压缩，但逐fork解码内容必须与v3完全一致。

只有实际交付并消费了相关程序，才重新评估自然入口与完整题池。已有三个基线成功案例会在当前结构触发条件下被暂停，提示完整对照必须保留误停和退步；这是历史轨迹上的反事实机会，尚不是实测退分。[自然触发机会审计](../experiments/034-v3-preparation/natural-trigger-opportunities.json)
