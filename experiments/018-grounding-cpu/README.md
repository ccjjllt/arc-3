# 018 CPU 准备结果

2026-10-18，Asia/Shanghai。**准备完成，未上传、未启动 GPU。** 当前有效报告由 [latest.json](latest.json) 指向 `cpu-20261018T054036Z/report.json`；20 项人工 CPU 检查通过，不是 20 个游戏或模型实验。

候选使用既有 `ARC3_SYSTEM_PROMPT_PREFIX`，仅在 observation_grounding 子进程、ToolAgent 构造前设置；baseline 不安装该前缀。130 词 / 873 字符，SHA256 `7643053cbe36f7cb3d0a6929cc7ddb3de6057ad96ed358068e23b7ebecfd62f7`。提醒仅在几何/图案转程序状态时核对局部 ASCII、裁剪范围及关键编码格；明确颜色掩码不必等同物理/碰撞足迹。没有新区域 API、工具、记忆合同或框架自动动作/模型调用；提示仍可能改变自然请求数、tokens 和动作。

实际导入冻结 ToolAgent 和 solver，按原 Notebook 两段 setup_env 字典的静态值配置后构造两组 ToolAgent。仅模型 ID/URL 用无请求的 CPU 占位，warmup0 与研究入口相同。确认候选系统提示严格等于前缀加原提示，工具 schema 相同，Python 执行/dispatch/模型调用等原方法对象未替换，控制参数及记忆状态相同。空前缀恢复、拒绝非空与重复安装、单因素配置拒绝均核对。独立进程执行真实 preflight，确认共享 deadline/timing/scheduler hooks 安装/卸载，并在 serving 前拒绝 ambient 非空前缀。

[Notebook](../../notebooks/018-observation-grounding/experiment.ipynb) 已构建为 36 cells / 29 code cells，SHA256 `731fd4335c20bcec86ea93f3be9449be82175a28ea6835582090b3b3999aefc7`；[manifest](../../notebooks/018-observation-grounding/build-manifest.json) 保留全部来源 hash。真实 IPython 仅执行重定向到临时目录的 writefile cells，全部 helper 字节/hash匹配、源码可编译；继承 patch cell 未改、末尾换行与 git apply --stat 通过，preflight位于模型launcher之前。未执行 Notebook 安装、serving 或求解 cells。

配置为 jiyujia；ft09/tr87/ar25/sb26 四个精确版本，baseline→observation_grounding，各1000秒，单pass、warmup0、10-stream **容量**（四游戏实际至多四路），remaining/pace0，两臂共用016的严格预算/缓存/截止/观察配置，硬限5400秒。是否启动取决于届时实际资源；当前没有消耗研究GPU额度。

## 手动重做

```bash
/Users/zhaohuaxiang/.local/bin/python3.12 -B scripts/check_018_grounding.py \
  --sdk-path /private/tmp/arc3-018-sdk \
  --extra-python-path /private/tmp/arc3-018-check-deps \
  --build
```

临时依赖目录不是仓库运行依赖；清理后应重建这些 CPU 检查依赖，而不是改用虚拟 ToolAgent。原 `/private/tmp/arc3-010-sdk` 已只剩部分缓存，本轮从已下载的官方 arc_agi/arcengine 及其 pure-Python wheel 恢复到独立目录，来源在 [sdk-preparation.json](sdk-preparation.json)。另将 IPython/nbformat/fastapi/flask 的 CPU 检查依赖下载到专用临时目录，版本在 [dependency-preparation.json](dependency-preparation.json)。没有下载模型权重或安装GPU runtime。

历史失败报告保留：053700Z 缺失旧 SDK 源码、053738Z/053752Z 缺 Flask/MarkupSafe，053903Z 检查器未加载原 setup_env 导致调度预检失败。054003Z首次完整通过；054036Z在澄清“框架不主动添加调用，但自然调用可能改变”的元信息后重新构建检查通过。最终实际依赖来源写入报告，使用 CPython3.12，不借 CPython3.13 二进制。

独立子代理只读复核了最终报告、源码/manifest哈希和提示差异，未发现当前工程阻断。边界：未启动游戏、未执行模型日志或sandbox代码、未调用模型/HTTP；网络只用于上述准备依赖下载。没有证明自然采用、像素理解正确、成本降低、关卡收益或远端Kaggle依赖可运行。真实采用需由未来请求中的“读取当前局部证据→忠实编码→实际消费”验证；提示本身不是机械正确性证明。
