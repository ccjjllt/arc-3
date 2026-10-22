# 未运行的 xz 数据包装方案

此目录保存异步上传结果明确前构建的压缩包装版本，未作为实际 v3 运行。实际远端 v3 是 989878 字节、32 cells、SHA256 `fc0f8d940d96f8e58bb3a044d9d7df956b8c781d1c9c60ecf510a272d4f32840` 的 large 版本，当前 canonical 目录已恢复为该版本。

本方案配置归档于 `experiments/034-plan-diagnostic-v3-xz-packaging.json`，审计归档于 `experiments/034-v3-preparation/build-audit-xz-packaging.json`；仅数据包装改动保存在 `experiments/034-v3-preparation/xz-packaging-only.patch`。当前工作树对应实际在跑版本，尚未应用该 patch。
