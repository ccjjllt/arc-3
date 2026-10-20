# 028 真实程序修复执行进展

2026-10-20，北京时间。`zhuating/arc3-028-program-repair` v1已实际推送并运行，Notebook SHA256 `9f4ba2330a556a0cc22d1f4da6010628a6c9db6c40d449b6db354912935d02bb`。真实硬件为单张RTX PRO 6000 Blackwell Server Edition，97887 MiB。模型就绪约820秒，三对六个续跑会话共享同一服务。

ft09 cum27、tu93 cum276、r11l正常控制cum40的原始画面与完整Harness恢复均已核对。修复模型必须生成Python并通过原工具真实执行；两失败B臂各最多一次修复调用，所有修复和续跑包含在各250秒／30动作上限中。A/B并发共享GPU用于机制诊断，不能把本次分数当全池或正式排行榜结论。

固定输入、源码和上传记录分别位于 `experiments/028-fork-package.json.gz.b64`、`experiments/028-program-repair-source/`、`experiments/028-program-repair-launch.json`。GPU执行已结束，六个会话均实际续跑；结果导出因ActionRecord被当作dict而失败，已从原始请求、工具输出和动作回声恢复结果，没有为导出故障重跑GPU。无新正式submission。

实际结果：ft09修复代码返回、执行并被主模型使用，但关键像素仍提取错误；tu93修复请求60秒超时；三对A/B均无新增关卡。本版关闭，不扩全池。详见 [028真实结果](../../research/028-program-repair-results.md)。整个会话内部约19.26分钟，模型加载约13.66分钟；求解阶段GPU中位98%，均值72.15%，不能将中位数当作全会话利用率。

同步研究发现：991次既有Python工具输出中，73次符合普通异常触发，60次下一工具已不报错。连续两次不同工具异常触发的本地v2尚无GPU收益证据，不因缩窄触发就晋升。后续配置 `experiments/030-capability-comparison.json` 仅比较独立的关内持久Python候选与原基线，一次模型加载、各25题、各7254秒、10路并发。
