# 020 正式路径本地准备

已经生成[正式候选Notebook](020-submission-source/submission.ipynb)，**未执行、未push、未正式submit**。它不是12游戏研究Notebook，也没有可报告的新榜分。

- 构建入口：[build_020_submission.py](../scripts/build_020_submission.py)，配置：[020-grounded-submission.json](020-grounded-submission.json)。默认kernel身份为`ccjjllt/arc3-020-grounded-submission`，继承009账号，仅是本地metadata。
- 原009 builder/config和冻版未修改。新builder调用原builder写入临时目录，再插入独立源码及安装cell；重建的009底稿SHA256与已存v2完全相同：`203da467cb0534fdf50b5683a55a524e647023e0d490524c59f2fda9a73b5dd5`。
- 唯一求解变化为`grounded_state`精确region接口和其prefix；附带`observation_representation.py`与package init。安装在bundle路径可用之后、模型服务及benchmark unpickle之前。没有加入018提示、checked execution、probe策略或FP8 PLE。
- 正式rerun逐字保留原gateway动态游戏枚举、一次pass、120任务/10 active streams、31,920秒solver预算及32,400秒Notebook时限。它没有研究池过滤。
- Save逐字保留sb26/cd82两个公开游戏、300秒、2并发、1,500秒启动上限和2,400秒总watchdog。只有真实GPU smoke通过后才写官方不计分placeholder；正式submission文件仍由gateway负责。

本地构建命令：

```bash
python3 -B scripts/build_020_submission.py --output-dir experiments/020-submission-source
```

生成物30cells、701,629 bytes，SHA256为`3fa59145d6d632af1d931fc727edf99bfafa0202ab6c8d4658ee4086c73c7215`。完整小型源码快照、输入hash和cell映射在[build-manifest](020-submission-source/build-manifest.json)；[本地准备记录](020-submission-preparation.json)确认新Python源码可编译、未执行状态以及原gateway/服务/预算cells逐字保留。grounded_state冻结hash为`65c91f2be5b9e27c763be8c94fa1241cef819a625663f8238df9002f6b3dee05`，与020研究候选一致。

本地默认与bundled Python未安装nbformat/IPython，因此采用JSON结构检查与新cell编译；未声称Notebook全程执行或视觉预览通过。下一次选中此正式候选后，应运行它原有的真实GPU save smoke。当前短筛结果尚不由这个构建产物给出，也没有增加人工审批步骤或新的晋升门槛。
