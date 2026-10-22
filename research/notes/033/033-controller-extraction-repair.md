# 033 控制器提取器纠错诊断

2026-10-21。初次`jiyujia/arc3-033-controller-candidate` v1在权重加载阶段退出，没有研究结果；补跑`zhuating/arc3-033-controller-retry` v1已进入真实模型纠错。只运行候选B，不构造新A/B分差。复用028的ft09第27动作切点；600秒runner allowance，真正续跑450秒、最多30动作；其中最多120秒/两次修订请求用于纠错。原两臂配置仍保留供后续研究，尚未启动。

补跑只恢复009原整模型预读并放宽加载余量，冻结纠错代码与实际续跑预算不变。模型在466秒就绪，session第514秒进入候选臂；初次失败不能当作机制负结果。来源见`experiments/033-launch.json`和`experiments/033-retry-launch.json`。

`controller_repair.py`复用028同模型请求及原sandbox。要求模型修订历史bbox填色输入，返回自包含`extract(frame)`，可另定义`rebuild(frame)`保留原pieces/图案/目标计算用途。宿主阻止验证期全部环境动作，逐格比较完整坐标颜色/行段与真实当前画面；候选失败恢复旧函数及历史前缀。验收后宿主再次实际调用保留的extract，将规范化准确行段直接交入下一主请求。可选提案仅在完整合法动作schema和非空可见变化预测下执行最多首步，否则不接管动作。

**`full_frame_pixel_contract_passed_and_delivered`只表示全帧像素合同通过并已交付，不表示旧语义提取器修好。**抄写frame.ascii可轻易通过该合同；必须从真实后续pieces/patterns/target计算及动作判断旧错误是否消失。`rebuild`返回也标为未独立验证的模型输出。没有P4坐标/正确值特例、环境内部答案或未来帧；这是强制切点诊断，在线触发尚未接入。

入口：`controller_repair_forks.run_forks(bm=..., job_dir=..., budget_seconds=600, use_repair=..., dry_run=False)`。A/B arm分别为`controller_repair_A`、`controller_repair_B`；payload需新两模块、`program_repair.py`和028压缩包，无031安装。配置为`experiments/033-controller-repair.json`。

输出：`controller-repair-forks.json`、单题结果、实际请求日志（单会话为arm根目录`requests.jsonl`）、transcript和`artifacts/*_controller-repair.json`。分别记录修订usage、主请求usage、拒收原因、保留函数、准确结果交付hash、下一真实请求是否含该结果、控制器首动作及随后主循环动作；交付不等于采用。

必要CPU核验见`experiments/033-controller-repair-cpu.json`：真实ft09回放匹配；合成响应经原sandbox核对4096像素、实际第二次调用extract、拦截一次动作且真实callback为0、拒收后函数回滚/历史保全。它不是实际模型效果证据。首轮CPU漏设009函数保留开关，补齐同基线环境后通过；后续prompt/状态标签澄清及可选rebuild分支只做编译核对，不增加测试套件。
