# 009 — 首次正式基线提交

日期：2026-10-12（Asia/Shanghai），修订2。用户已授权实施“先提交冻结基线，同时进行008 CPU研究”的路线。v1两次系统错误后已定位补丁缺末尾换行的确定性缺陷，当前方案改为直接Notebook cells及真实GPU保存验证。对应进展见 `docs/progress/009-baseline-submission.md`。

## 目标与选择

取得本项目第一份可追溯的正式比赛提交，验证隐藏评测入口、运行完整性及自身public LB位置。005的49.8997分来自公开开发25游戏，不能作为隐藏榜预期分数。003/006/007均无净收益证据，本次全部关闭；008原型不接入009。

以本地已固定的Franzen Milestone 2 v3完整Notebook为基础，继承原始harness patch、模型、serving、优先级调度、warmup和正式gateway路径。单独构建009，不覆盖已运行研究Notebook。当前研究runner拒绝competition rerun，不能仅删除拒绝语句就直接用于提交。

## 最小实现

1. 独立builder、配置、Notebook与manifest；模型两份v1、两份dataset及competition输入均继承原版。新metadata移除原作者id_no，使用自己的私有Notebook、RTX PRO 6000、断网、32400秒平台上限。
2. 从真实挂载中定位source/wheel/model输入，兼容007实际观察到的嵌套及扁平路径；正式评测不以公开environment_files存在为前提。
3. 普通save运行真实模型启动验证：等待health200后，sb26/cd82两公开游戏、1pass、并发2、300秒；每局有模型生成tokens和非RESET动作才生成明确标记的占位submission.parquet。启动上限1500秒、save总上限2400秒；仅清理本次save的模型进程组。正式rerun预算不受这些限制，运行完整模型并只接受gateway生成的真实产物。
4. 普通save与正式rerun的区分使用平台KAGGLE_IS_COMPETITION_RERUN；不手工伪造该变量去访问隐藏游戏。
5. 保留普通可读cells、原%%writefile与shell magic，不把单元包装为exec/compile字符串。验证实际生成的补丁文件及git apply，不能仅比较写文件之前的源字符串。

轻量save的依据是[ARC Prize官方starter构建器](https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter/blob/main/scripts/build_notebook.py)中明确的non-rerun占位分支；它不是成绩。正式真实产物仍由gateway记录动作并生成。

## 手动验证与发布

- 核对原23个cells的逐项变化、大patch字节/哈希及正式solver/serving配置。
- 使用IPython原生转换和nbformat检查cells；在Kaggle实际执行非正式save的GPU启动与两个公开游戏，核对日志、benchmark、真实动作及tokens，不能仅看parquet。保持手动验证、不创建测试文件、不启动本地模型。
- push前保存账户配额、今日提交次数、源哈希；确认Notebook成功保存的准确版本、GPU/断网设置和输出文件。
- 正式提交准确的own-kernel/version/submission.parquet组合，记录响应和submission ID；响应不确定时先查询历史，不盲目重试。
- 接受、排队、运行、评分成功分别记录。提交已接受不表示模型已成功完成隐藏游戏。

## 资源和研究边界

v1启动前CLI显示GPU余额约8.64h，本赛提交记录为空，今日允许提交1次。v2准备时余额约8.63h，两次v1失败后额度恢复1次；以实际快照为准。v2普通save会使用真实GPU进行最多40分钟的启动及公开游戏验证，不能写成CPU-only或轻量占位保存。正式评测上限9h与个人开发GPU额度是不同口径。

008只使用CPU和已有公开轨迹，独立研究当前帧区域表示，不自动启动新的A/B。模型许可与奖金资格的主办方解释仍未明确；保留许可来源，不将提交成功解释为奖金资格获确认。本次不代表用户向主办方发送消息。
