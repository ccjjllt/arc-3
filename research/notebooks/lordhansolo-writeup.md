## Overview

The solution for [ARC-AGI-3](https://arcprize.org/arc-agi/3) Milestone 2 is built on the [Tufa Labs duck harness](https://github.com/Tufalabs/duck-harness). Each game is played by a single agent, backed by the same open-weight model for all games. The agent inspects the board and executes actions by writing code for one Python tool. The model is [Qwen3.8-Flash-Next](https://huggingface.co/primitive-ai/Qwen3.8-Flash-Next-mixed-NVFP4-FP8), served by a [patched vLLM](https://www.kaggle.com/datasets/lordhansolo/arc3-vllm-e975732-gdn-recoverssm) that runs many games at once on one GPU. The submission notebook is public: [built-on-tufa-labs-duck-harness-milestone-2](https://www.kaggle.com/code/lordhansolo/built-on-tufa-labs-duck-harness-milestone-2/notebook?scriptVersionId=353922905).

The key observation was that the score follows the number of turns each game gets. Most of my work therefore went into serving more tokens per game within the fixed time budget.

## Model and serving

Everything runs offline on the Kaggle machine, a Google Cloud g4-standard-48 with 48 vCPUs, 180 GB of RAM and one NVIDIA RTX PRO 6000 Blackwell GPU with 96 GB of memory.

The submission mounts three public Kaggle inputs:

- **Model:** [qwen3-8-flash-next-mixed-nvfp4-fp8](https://www.kaggle.com/models/lordhansolo/qwen3-8-flash-next-mixed-nvfp4-fp8/PyTorch/hf-mixed-mtp-nvfp4/1), a mirror of [primitive-ai/Qwen3.8-Flash-Next-mixed-NVFP4-FP8](https://huggingface.co/primitive-ai/Qwen3.8-Flash-Next-mixed-NVFP4-FP8).
- **Runtime:** [arc3-vllm-e975732-gdn-recoverssm](https://www.kaggle.com/datasets/lordhansolo/arc3-vllm-e975732-gdn-recoverssm), a [vLLM](https://github.com/vllm-project/vllm) main build at commit e975732 packed from Docker image layers, plus extra patches. Details in the throughput section.
- **Source bundle:** [taaf-kaggle-source](https://www.kaggle.com/datasets/lordhansolo/taaf-kaggle-source), the harness code.

## Agent harness

The core of the Tufa Labs duck harness stays as it was: one `python` tool, a segmented board and the game history available in code. My main changes on top of it:

- **Saved modules with regression tests.** `save_module` keeps tested code across turns, levels and context truncation. Tests replay against the observations captured when they were added, so an update that breaks an earlier test is rejected.
- **Richer action feedback.** After each action the model gets the changed regions and the per-step changes in a batch.
- **Animation frames.** The engine can answer one action with several frames. The original harness passed on only the last one, the board the action settled on. Here the frames before it are kept too, in `current_frame.animation_frames`, and the model reads them in code like any other board. Repeated frames are collapsed and long animations are thinned to 16 frames. The first frame and the settled board are always kept. The action result adds a short reading of those same frames: `blink` when a region alternates between two looks, `tween` when one sprite slides in a straight line, `path` when it takes any other route, and `other` for everything else. Every reading carries the frame count and the bounding box of the animated region. A moving sprite is named by the same hash as its segmentation node. An action that changed no pixels but did animate tells the model the game reacted even though the board ended unchanged. The newest 16 history entries keep their frames.
- **A game record the model can query.** `game_overs` lists the failed attempts on the current level, and every action stores the one-line `plan` it was issued with. The model can recall what it tested after those turns leave the context.
- **Strategy audit.** When a level stalls, the turn prompt asks the model to separate observed facts from assumptions and run one discriminating experiment.
- **History bounded by tokens, not by turns.** The original kept a fixed number of recent model replies. Now the whole history stays until a request nears the context limit, and only then are the oldest turns dropped. Until then new turns are only appended, so each prompt begins with the previous one and vLLM can serve that part from the prefix cache.

I cannot confirm that any of these changes improved the score. That would take A/B tests over many runs, and I did not have the compute for them.


## Throughput engineering

Every turn costs tokens, mostly thinking, so the number of turns a game gets depends on how many tokens it can generate in its time. The score closely followed the number of turns per game, so the goal was to generate more tokens per game.

In the final setup many games run at once in waves, with no preemptions and most of each prompt served from the prefix cache.

The main steps on the way there:

1. **More KV room per game.** A compact checkpoint, an FP8 KV cache and memory moved off the GPU let more games run at once.
2. **Prefix caching that survives the tool gap.** Patches keep the model's recurrent state between turns, so most of each prompt is served from cache.
3. **Longer context.** History is truncated less often, and each truncation makes the next prompt miss the cache and prefill again from the start. Fewer truncations left more GPU time for generation.
4. **Higher concurrency.** More games in flight raised total throughput. Each game generates tokens more slowly, but there are fewer waves and each game gets more time, which makes up for it. The time limit for a single turn (yield seconds) should grow along with it, so a turn still gets about as many tokens as before.
5. **No idle engine between turns.** Keeping game state in memory instead of on disk removed most of the tool latency and kept the engine fed.
6. **SM 120 kernels.** Custom GEMM kernels for the small batches seen during decode. The gain is small.

The vLLM patches ship in the public [arc3-vllm-e975732-gdn-recoverssm](https://www.kaggle.com/datasets/lordhansolo/arc3-vllm-e975732-gdn-recoverssm) runtime dataset.

## Lessons and acknowledgements

The main lesson is to measure what the agent achieved per unit of spend, not the single-run score.

- **Read low-variance metrics first.** Turns per game and generated tokens per turn show whether a change moved the machine. The score alone mostly shows the dice.
- **Look for idle time, not only faster kernels.** Gaps between turns are easy to miss in a kernel benchmark. Keeping game state in memory instead of on disk kept the engine busy between turns.
- **Measure on the target hardware.** Benchmarks on a different GPU did not always carry over to the competition machine, so every serving change had to be checked there.

Thanks to:

- [ARC Prize](https://arcprize.org/arc-agi/3) and Kaggle for ARC-AGI-3 and the competition.
- [Tufa Labs](https://tufalabs.ai/research/duck-harness/) for the [duck harness](https://github.com/Tufalabs/duck-harness) and the TAAF framework this solution is built on.
- [primitive-ai](https://huggingface.co/primitive-ai/Qwen3.8-Flash-Next-mixed-NVFP4-FP8) for the checkpoint and the Qwen team for the model.
- The [vLLM](https://github.com/vllm-project/vllm) contributors.

