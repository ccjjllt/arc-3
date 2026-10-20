# 028 真实修复结果

No paired case gained a level. ft09 repair executed and was used but retained its key pixel error; tu93 repair timed out. Do not expand this implementation on these results.

| 游戏 | A新增关 | B新增关 | A续跑动作 | B续跑动作 | A总token | B总token |
|---|---:|---:|---:|---:|---:|---:|
| ft09-0d8bbf25 | 0 | 0 | 1 | 1 | 12968 | 16297 |
| tu93-0768757b | 0 | 0 | 0 | 9 | 19973 | 15589 |
| r11l-495a7899 | 0 | 0 | 0 | 2 | 14688 | 17023 |

ft09 B：真实修复调用50.19秒，1116生成token、58470输入token；代码执行并被后续模型采用，但关键WOg→WOW误编码仍存在。

tu93 B：修复调用60.32秒后ReadTimeout，无返回代码；超时调用的实际生成token未知。

六路续跑均实际执行至退出；arm ERROR来自结束后ActionRecord.get导出错误。该工程故障不能抹去已有修复与续跑证据，也不需要重跑GPU恢复结果。

这是六路并发单次诊断，不是正式榜分；token为分析器记录，非计费。动作比较包含ID和完整坐标参数。
