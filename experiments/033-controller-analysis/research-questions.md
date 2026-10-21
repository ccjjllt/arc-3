# 033结果回来后的三个研究问题

这是结果前的局部研究预判，不是验收门槛或已取得的收益；不改冻结helper、不产生环境动作。依据为028原ft09切点与031 B实际执行的`pieces/target_for`代码。下面的具体坐标和正确像素仅用于离线审阅，不能补进本次或后续在线修复提示。

## 1. 准确像素是否进入了真正的pieces/图案提取？

原切点P4的3×3采样为`[gWg, WOg, WWW]`；旧bbox填色代码得到`[gWg, WOW, WWW]`。唯一差异是当前图中`(row46,col32)`：真实`g`，旧`pieces`为`W`。将中心颜色记为`C`时，中行应是`W C g`，不是`W C W`。

最有价值的证据是**新rebuild或随后主循环实际执行得到的P4/pieces输出**变对，并用同一画面逐格确认。`extract`复制4096个正确像素、日志含正确坐标、函数存在，均不能单独回答这个问题。若新代码仍使用bbox双层range，要看实际得到的任务数据，不能只因它读过extract就判为纠错。

若未返回/打印P4，可离线重放已返回的纯计算代码，在同一切点原帧检查输出；不要擅自执行含`action()`的新代码，也不要用已换关的最终帧替代原帧。

## 2. 这个修正是否改变target/mismatch计算，而非只添一份数据？

已将031 B的原`target_for`代码在原帧做纯CPU差分：仅把错误`pieces`换为实际像素，其余算法不动，目标变化**只落在逻辑tile(5,3)**，对应可点击色块中心`MOUSE(row46,col38)`。

| 原算法保留的假设 | 旧错误输入的target(5,3) | 精确输入的target(5,3) | 切点该色块实际颜色 |
|---|---|---|---|
| mode A | O | R | O |
| mode B | R | O | O |

因此，在**沿用旧mode A的条件下**，完整mismatch应为`((0,1), R→O)`和`((5,3), O→R)`；对应中心为`(row6,col22)`、`(row46,col38)`。旧代码漏掉第二项。沿用mode B时，这个修正反而应从原mismatch中移除tile(5,3)，避免多点一次。

这些是原规则假设下的可复现推论，**不是宣称mode A/B中哪一个已经被环境证实**。新模型可以改规则、换表示；重点读出“准确观测→具体目标改变”的链条，而不是要求它复述某个列表。只返回全帧抄写、随后仍用手写`W C W`或旧target，是没有解决已知任务输入错误的直接证据。

## 3. 随后动作是否产生有意义的真实变化或关卡推进？

031两臂曾把预算花在P2内部/调色板探测，实际均为no-op，最终停在完成2/6关。033应区分：

- 控制器有没有真的执行首步，还是只有计划；随后主循环到底执行了哪些完整ACTION6坐标。
- 若动作落在上述色块，是否真实改变对应O/R颜色，而不是只动边缘计时条；若采用不同规则，也需有清楚的观测依据和真实效果。
- 是否完成第3关或更深；若未过关，是否已经纠正输入却受规则解释、超时或新错误阻断。单候选多/少动作都不直接称提分。

若有控制器动作，后续证据须使用其**动作后**帧；交回的准确行段属于动作前帧。不要跨level/reset继续对照旧P4，也不要把最后未返回的模型请求视为零成本或没有计算。

## 最短读取方法

先运行现成分析器，查看`summary.md`和`review.md`，无需额外测试：

```bash
python3.12 -B scripts/analyze_033_results.py
rg -n -C 2 'P4|pieces|target_for|rebuild|\[action\]|NO-OP|level_completed|gameplay_changed' \
  runs/033-controller-candidate/controller_repair_B/transcripts/ft09-0d8bbf25_B.txt
```

也可直接抽出实际返回与执行动作；下面只读JSON，不执行任何模型程序：

```python
import json
from pathlib import Path
p = Path('experiments/033-controller-analysis/summary.json')
d = json.loads(p.read_text())
print('rebuild output:', (d['repair'] or {}).get('task_rebuild_output'))
for call in d['main_requests']['new_python_calls']:
    if any(word in call['code'] for word in ('extract', 'rebuild', 'pieces', 'target_for', 'P4')):
        print(call['call_id'], 'request line', call['first_snapshot_line'])
        print(call['code'])
        print((call.get('tool_result') or {}).get('payload'))
print('controller action:', d['observed_stages']['controller_first_action'])
print('actual main actions:', d['observed_stages']['actual_subsequent_main_actions'])
print('added levels:', d['observed_stages']['added_levels_after_checkpoint'])
```

需要核对落盘帧时，读取`artifacts/*_tool_runtime_state.json`中的`current_frame.level/step/grid`，先确认仍是同一关、同一动作阶段。当前文件是末帧，不保证就是修复时帧；原修复帧在028冻结包，后续帧优先取实际events/viewer记录。颜色字母表来自runtime的`inference.utils.grid_utils.ARC_COLOR_CHARS`，不要手猜数字颜色映射。

最终按实际结果分别陈述：全帧合同、P4/pieces纠错、目标计算变化、真实动作效果、关卡推进和成本。单臂033不借旧028/031轨迹构造新的配对分差。
