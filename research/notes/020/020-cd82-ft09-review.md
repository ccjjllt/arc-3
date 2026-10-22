# 020：cd82与ft09退分轨迹复核

2026-10-19。静态读取候选完整请求日志，以`call_id`去重，深审下列关键调用链，并直接切片保存的公开`board_ascii`交叉核对。没有执行模型生成代码、游戏实现、Notebook或GPU。审阅者为Codex AI agent；完整原代码、输出、调用ID、来源行及hash在[复核JSON](../../../experiments/020-analysis/cd82-ft09-review.json)。

结论：**两款游戏的主要失败求解链没有使用新region通道。cd82有一处可确认的“看到了四格、程序却写成三格”，ft09则在两个假设方案未能过关后继续修正规则和坐标变换。** 这些是本次轨迹可见的失败机制，不证明prefix或新API造成了单次退分。

| 游戏 | baseline→候选分数 | 完成关卡 | 候选逐关动作 |
|---|---:|---:|---|
| cd82 | 100→4.902985 | 6→2/6 | 60、26、35、0、0、0 |
| ft09 | 100→47.619048 | 6→4/6 | 6、7、14、22、40、0 |

分数引用现有[comparison](../../../experiments/020-analysis/comparison.json)，本次不重复声明为独立计分复算。两个游戏合计对12游戏均分差贡献约−12.289831分；这不是机制因果贡献。

## 1. region只在cd82最后一次出现，尚无求解消费

- ft09已返回并进入历史快照的35个唯一调用中，没有`.region()`或`.region_from_node()`调用。它继续用segmentation和直接ASCII构造程序输入。
- cd82的74个唯一调用中，唯一region入口是[#74，原149行](../../../runs/020-candidate-logs/grounded_state/cd82-fb555c5d_p0_requests.jsonl:149)：`current_frame.region((2,1,14,15), foreground=None)`成功返回，并打印`raw_rows`。这确实是一次自然读取，随后没有可见的求解器消费或行动链；不能将“打印过”升级为直接数据通道改善计划。
- 两日志全部真实request的system prefix与冻结`GROUND_STATE_PREFIX`一致。没有region报错，也没有发现region getter因陈旧帧而中断这些失败计划。

因此，本次既没有证明region返回坏数据，也没有证明它在这两段主要失败上发挥了作用。接口使用很少仍不排除说明文字改变了模型的自然生成；这一单次配对无法分离这种影响。

## 2. cd82：实际四格宽涂色，被编码成三格宽并推成“不可达”

第3关新交互已被观察到。[#60，121行](../../../runs/020-candidate-logs/grounded_state/cd82-fb555c5d_p0_requests.jsonl:121)点击瓶子后，打印目标块前三行都是`WWWOOOOWWW`，即局部列3、4、5、6四格为橙色。独立读取[events:144，action95](../../../runs/020-focused-events/grounded_state/artifacts/cd82-fb555c5d_p0_events.jsonl:144)的公开ASCII、全局行34–36和列27–36得到完全相同结果；此前action94这三行全白。

但[#68，137行](../../../runs/020-candidate-logs/grounded_state/cd82-fb555c5d_p0_requests.jsonl:137)把瓶子作用区手写为`r<=2 and 3<=c<=5`，漏掉第6列；它的逆向搜索返回`sol NONE states 4`。[#72，145行](../../../runs/020-candidate-logs/grounded_state/cd82-fb555c5d_p0_requests.jsonl:145)继续同样的窄区域定义，仍未找到解。

更直接的复现是[#73，147行](../../../runs/020-candidate-logs/grounded_state/cd82-fb555c5d_p0_requests.jsonl:147)：最后点击后打印`WWWOOOOYYY`。[events:181，action121](../../../runs/020-focused-events/grounded_state/artifacts/cd82-fb555c5d_p0_events.jsonl:181)也确认列3–6为O。紧接着#74推理却声称第6列仍是Y，进而推导目标不可能实现，再首次调用region重看参考图。

这是一处有原始观察反证的编码/解释错误；搜索是在不完整的手写动作效果上运行。它说明精确数据应该进入**动作效果模型**，而不只读取目标图。修正这一个宽度是否足以通关尚未验证，不声称能追回全部95分。

## 3. ft09：两套互补目标各执行一次，均未完成，原约束假设需要修订

进入第5关后，模型直接从当前/历史ASCII按格距提取图案，区分27个可变tile和若干提示图案；[#29，59行](../../../runs/020-candidate-logs/grounded_state/ft09-0d8bbf25_p0_requests.jsonl:59)枚举每个提示图案的两色映射，输出两套互补解。这里的“两解”仅针对它写出的约束，不能证明真实游戏目标只有这两种。

[#30，61行](../../../runs/020-candidate-logs/grounded_state/ft09-0d8bbf25_p0_requests.jsonl:61)先执行10个点击（含撤回探测格），返回`level_completed=False`；随后[#31，63行](../../../runs/020-candidate-logs/grounded_state/ft09-0d8bbf25_p0_requests.jsonl:63)把全部27个tile翻成互补方案，仍未完成。保存事件action62/89均在level5、score4。[#33，67行](../../../runs/020-candidate-logs/grounded_state/ft09-0d8bbf25_p0_requests.jsonl:67)复看初始与当前格子，确认第二套方案的18个紫格变化，提示图案未改变。

这段并非动作没有执行：两个计划的颜色变化已出现，预设条件却没有带来过关。后续模型也明确转向怀疑约束/胜利条件。这是适合研究“目标假设被真实完成反馈否定后如何选择下一次探测”的病例；本复核不读取游戏实现来替它补真规则。

## 4. ft09：变换诊断又混淆坐标系，随后才修正

[#34，69行](../../../runs/020-candidate-logs/grounded_state/ft09-0d8bbf25_p0_requests.jsonl:69)把方向位移`(dr,dc)`∈[-1,1]直接交给按3×3坐标编写的`tr`；其identity分支最终仍减1，因此NW(-1,-1)变成(-2,-2)，找不到方向后被跳过。输出把identity覆盖降成12个tile，而非先前27个。

[#35，71行](../../../runs/020-candidate-logs/grounded_state/ft09-0d8bbf25_p0_requests.jsonl:71)改为先传`(1+dr,1+dc)`，变换后再减1，恢复identity的27个约束覆盖。该修订之后没有可见后续动作，最终停在第5关。这是模型写出的坐标变换错误及修复，不是region实现错误；也不能将这几次计算单独认定为全部退分原因。

## 5. 可见错误来自旧字段假设与既有guard，不能算成region故障

cd82有8个带error的已记录工具结果：3次假设`boundary[2]`存在而触发IndexError，1次sandbox不允许`import sys`，1次将boundary列表与整数比较的TypeError，以及3次已有StaleStateActionError。ft09有3次相同的`boundary[2]`索引错误。原行号、完整错误及调用ID保存在复核JSON；均不来自region。

部分错误发生在真实动作之后，例如cd82#31先点击再打印失败，所以不能把“工具报错”换算成“零动作”。这些具体字段假设可作为后续小修研究素材，但本次没有添加新guard或修改运行代码。

## 日志覆盖与限制

cd82原逐游戏文件为75 request/74 response；默认`grounded_state/requests.jsonl`中的一条响应通过原分析器的**同臂、完整请求身份字段唯一匹配**归属cd82，合并后75/75、106,415 completion tokens，0匹配问题。fallback只补响应账本，不制造新代码调用，因此仍为74个可审历史调用/74个结果。

ft09为36 request/35 response，73,724 completion tokens；可审历史为35个调用/35个结果。最后request未见响应，不能计成执行过的工具代码。新产生的末次调用可能没进入后续快照，本报告没有凭空补它；根任务负责与deadline/执行账本作最终对账。

两份日志都无call_id函数/结果冲突。全部109个去重调用索引及错误已检查，语义深审集中在本文的关键链；没有在本次深审baseline完整轨迹。手工定位的是值得继续处理的行为断点，不是新的采用门槛或单次因果证明。
