# Failed model registry

_Generated (UTC): `2026-04-03T14:54:33.548767+00:00`_

**Source:** `/mnt/models/d3/run_state.json`

## Summary

| Metric | Count |
|--------|------:|
| Total failed (run_state) | 26 |
| Skipped (included) | 5 |
| Total rows (merged) | 47 |

| Category | Models |
|----------|-------:|
| `failed_shards` | 30 |
| `unavailable` | 6 |
| `disk_space` | 5 |
| `skipped_gated` | 5 |
| `auth` | 1 |

### Historical run reports (`run-report-*.md`)

| Metric | Value |
|--------|-------|
| Report files scanned | 25 |
| Distinct models in reports | 35 |
| Rows historical-only (not failed in run_state now) | 16 |
| Directories | `/mnt/models/d3/logs` |

## Disk space (ENOSPC) (`disk_space`)

| Model id | Drive | Tier | Reason kind | Primary | Hist-only | #inc | Updated (UTC) |
|----------|-------|------|-------------|---------|-----------|-----|---------------|
| `deepseek-ai/deepseek-vl2` | d1 | F | no space left on device | run_report | yes | 5 | 2026-04-02T22:24:01 |
| `meta-llama/Llama-3.2-90B-Vision-Instruct` | d5 | F | no space left on device | run_report | yes | 1 | 2026-03-30T01:45:34 |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` | d1 | D | disk space / abandoned | run_state | — | 1 | 2026-04-03T00:48:34 |
| `Undi95/dbrx-base` | d2 | A | disk space / abandoned | run_state | — | 1 | 2026-04-03T04:01:42 |
| `unsloth/DeepSeek-R1-GGUF` | d5 | — | disk space / abandoned | run_state | — | 4 | 2026-04-02T20:06:51 |

<details><summary>Error text + run-report history</summary>

### `deepseek-ai/deepseek-vl2`

**Primary error:**

```
[Errno 28] No space left on device
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-01_03-22-55.md`

```
[Errno 28] No space left on device
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-30_14-40-54.md`

```
Access denied for model-00001-of-000008.safetensors: aria2c error for model-00001-of-000008.safetensors: The response status is not successful. status=403
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-30_14-40-54.md`

```
Failed to download DeepSeek-V3-Q4_K_M/DeepSeek-V3-Q4_K_M-00006-of-00009.gguf after 5 attempts: aria2c error for DeepSeek-V3-Q4_K_M/DeepSeek-V3-Q4_K_M-00006-of-00009.gguf: Download aborted.
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-29_21-45-34.md`

```
[Errno 28] No space left on device: '/mnt/models/d5/raw/deepseek-ai'
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-28_02-00-05.md`

```
[Errno 28] No space left on device: '/mnt/models/d5/raw/deepseek-ai'
```

### `meta-llama/Llama-3.2-90B-Vision-Instruct`

**Primary error:**

```
[Errno 28] No space left on device: '/mnt/models/d5/raw/meta-llama'
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-28_02-00-05.md`

```
[Errno 28] No space left on device: '/mnt/models/d5/raw/meta-llama'
```

### `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16`

**Primary error:**

```
Download abandoned (operator removed d5 scratch ~37 GiB, ~16% of target). disk space / abandoned
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00004-of-00050.safetensors after 5 attempts: aria2c error for model-00004-of-00050.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `Undi95/dbrx-base`

**Primary error:**

```
Download abandoned (operator removed d5 scratch ~32 GiB, ~13% of target). disk space / abandoned
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00001-of-00061.safetensors after 5 attempts: aria2c error for model-00001-of-00061.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `unsloth/DeepSeek-R1-GGUF`

**Primary error:**

```
Download abandoned (operator removed d5 scratch ~131 GiB, ~35% of target). disk space / abandoned
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-01_03-22-55.md`

```
Failed to download DeepSeek-R1-Q4_K_M/DeepSeek-R1-Q4_K_M-00001-of-00009.gguf after 5 attempts: aria2c error for DeepSeek-R1-Q4_K_M/DeepSeek-R1-Q4_K_M-00001-of-00009.gguf: Download aborted.
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-30_14-40-54.md`

```
Failed to download DeepSeek-R1-Q4_K_M/DeepSeek-R1-Q4_K_M-00002-of-00009.gguf after 5 attempts: aria2c error for DeepSeek-R1-Q4_K_M/DeepSeek-R1-Q4_K_M-00002-of-00009.gguf: Download aborted.
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-29_21-45-34.md`

```
Failed to download DeepSeek-R1-Q4_K_M/DeepSeek-R1-Q4_K_M-00003-of-00009.gguf after 5 attempts: aria2c error for DeepSeek-R1-Q4_K_M/DeepSeek-R1-Q4_K_M-00003-of-00009.gguf: Download aborted.
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-28_02-00-05.md`

```
[Errno 28] No space left on device: '/mnt/models/d5/quantized'
```

</details>

## Unavailable (404 / resolve) (`unavailable`)

| Model id | Drive | Tier | Reason kind | Primary | Hist-only | #inc | Updated (UTC) |
|----------|-------|------|-------------|---------|-----------|-----|---------------|
| `mistralai/Leanstral-120B-A6B` | d5 | E | repository not found / cannot resolve | run_state | — | 0 | 2026-04-03T08:12:47 |
| `mosaicml/mpt-30b` | d2 | A | repository not found / cannot resolve | run_state | — | 0 | 2026-03-23T02:50:57 |
| `mosaicml/mpt-30b-instruct` | d2 | A | repository not found / cannot resolve | run_state | — | 0 | 2026-03-23T02:50:57 |
| `mosaicml/mpt-7b` | d2 | A | repository not found / cannot resolve | run_state | — | 0 | 2026-03-23T02:50:57 |
| `mosaicml/mpt-7b-instruct` | d2 | A | repository not found / cannot resolve | run_state | — | 0 | 2026-03-23T02:50:58 |
| `Salesforce/CoDA-1.7B-Base` | d3 | G | repository not found / cannot resolve | run_state | — | 1 | 2026-04-03T09:37:51 |

<details><summary>Error text + run-report history</summary>

### `mistralai/Leanstral-120B-A6B`

**Primary error:**

```
Cannot resolve HF repo mistralai/Leanstral-120B-A6B: 404 Client Error. (Request ID: Root=1-69c1fc8a-024c4bb304000eb478f6c116;ef20d6d7-b308-4535-ad2f-2349e41ae9d9)

Repository Not Found for url: https://huggingface.co/api/models/mistralai/Leanstral-120B-A6B/revision/main?blobs=true.
Please make sure you specified the correct `repo_id` and `repo_type`.
If you are trying to access a private or gated repo, make sure you are authenticated. For more details, see https://huggingface.co/docs/huggingface_hub/authentication
```

### `mosaicml/mpt-30b`

**Primary error:**

```
Cannot resolve HF repo mosaicml/mpt-30b: 404 Client Error. (Request ID: Root=1-69c0aa99-4982627a699808a4370a9d6c;64987960-9da2-4c2d-92fa-68ec59fe9560)

Repository Not Found for url: https://huggingface.co/api/models/mosaicml/mpt-30b/revision/main?blobs=true.
Please make sure you specified the correct `repo_id` and `repo_type`.
If you are trying to access a private or gated repo, make sure you are authenticated. For more details, see https://huggingface.co/docs/huggingface_hub/authentication
```

### `mosaicml/mpt-30b-instruct`

**Primary error:**

```
Cannot resolve HF repo mosaicml/mpt-30b-instruct: 404 Client Error. (Request ID: Root=1-69c0aa99-5cfd55e94455f9d97e81a86f;a23b6a4a-737f-4fa0-a13d-f0981d45c07e)

Repository Not Found for url: https://huggingface.co/api/models/mosaicml/mpt-30b-instruct/revision/main?blobs=true.
Please make sure you specified the correct `repo_id` and `repo_type`.
If you are trying to access a private or gated repo, make sure you are authenticated. For more details, see https://huggingface.co/docs/huggingface_hub/authentication
```

### `mosaicml/mpt-7b`

**Primary error:**

```
Cannot resolve HF repo mosaicml/mpt-7b: 404 Client Error. (Request ID: Root=1-69c0aa99-721898887eeed4475a859cfb;b59f6a6f-e6fd-4d19-ad05-6b386649f77a)

Repository Not Found for url: https://huggingface.co/api/models/mosaicml/mpt-7b/revision/main?blobs=true.
Please make sure you specified the correct `repo_id` and `repo_type`.
If you are trying to access a private or gated repo, make sure you are authenticated. For more details, see https://huggingface.co/docs/huggingface_hub/authentication
```

### `mosaicml/mpt-7b-instruct`

**Primary error:**

```
Cannot resolve HF repo mosaicml/mpt-7b-instruct: 404 Client Error. (Request ID: Root=1-69c0aa99-0dd62c7466ab20b30ec9f6db;59c9ea5d-c625-4674-b328-30b1dd882556)

Repository Not Found for url: https://huggingface.co/api/models/mosaicml/mpt-7b-instruct/revision/main?blobs=true.
Please make sure you specified the correct `repo_id` and `repo_type`.
If you are trying to access a private or gated repo, make sure you are authenticated. For more details, see https://huggingface.co/docs/huggingface_hub/authentication
```

### `Salesforce/CoDA-1.7B-Base`

**Primary error:**

```
Cannot resolve HF repo Salesforce/CoDA-1.7B-Base: 404 Client Error. (Request ID: Root=1-69cea576-65b0a08a0816df410ef4c871;386f65dd-cc2f-4948-a73d-5d42a10231b3)

Repository Not Found for url: https://huggingface.co/api/models/Salesforce/CoDA-1.7B-Base/revision/main?blobs=true.
Please make sure you specified the correct `repo_id` and `repo_type`.
If you are trying to access a private or gated repo, make sure you are authenticated. For more details, see https://huggingface.co/docs/huggingface_hub/authentication
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00002-of-00012.safetensors after 5 attempts: aria2c error for model-00002-of-00012.safetensors: Authorization failed.
```

</details>

## Auth / gated (`auth`)

| Model id | Drive | Tier | Reason kind | Primary | Hist-only | #inc | Updated (UTC) |
|----------|-------|------|-------------|---------|-----------|-----|---------------|
| `Intel/neural-chat-7b-v3-1` | d3 | G | gated / access denied | run_report | yes | 1 | 2026-03-30T02:01:22 |

<details><summary>Error text + run-report history</summary>

### `Intel/neural-chat-7b-v3-1`

**Primary error:**

```
Access denied for pytorch_model-00001-of-00002.bin: aria2c error for pytorch_model-00001-of-00002.bin: The response status is not successful. status=403
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-27_05-30-32.md`

```
Access denied for pytorch_model-00001-of-00002.bin: aria2c error for pytorch_model-00001-of-00002.bin: The response status is not successful. status=403
```

</details>

## Failed shards / retries exhausted (`failed_shards`)

| Model id | Drive | Tier | Reason kind | Primary | Hist-only | #inc | Updated (UTC) |
|----------|-------|------|-------------|---------|-----------|-----|---------------|
| `alpindale/dbrx-instruct` | d5 | A | download retries exhausted | run_state | — | 1 | 2026-04-03T08:12:46 |
| `cognitivecomputations/dolphin-2.9.2-qwen2-72b` | d5 | D | download retries exhausted | run_report | yes | 2 | 2026-04-02T22:24:01 |
| `google/gemma-3-4b-it` | d3 | F | download retries exhausted | run_report | yes | 1 | 2026-04-02T22:24:01 |
| `google/gemma-4-26B-A4B` | d2 | F | download retries exhausted | run_state | — | 1 | 2026-04-02T23:12:02 |
| `google/gemma-4-26B-A4B-it` | d2 | F | download retries exhausted | run_state | — | 1 | 2026-04-02T23:21:41 |
| `google/gemma-4-31B` | d1 | F | download retries exhausted | run_state | — | 1 | 2026-04-02T23:31:21 |
| `google/gemma-4-31B-it` | d1 | F | download retries exhausted | run_state | — | 1 | 2026-04-02T23:41:02 |
| `google/gemma-4-E2B` | d3 | F | download retries exhausted | run_state | — | 1 | 2026-04-02T22:33:35 |
| `google/gemma-4-E2B-it` | d3 | F | download retries exhausted | run_state | — | 1 | 2026-04-02T22:43:08 |
| `google/gemma-4-E4B` | d3 | F | download retries exhausted | run_state | — | 1 | 2026-04-02T22:52:44 |
| `google/gemma-4-E4B-it` | d3 | F | download retries exhausted | run_state | — | 1 | 2026-04-02T23:02:21 |
| `google/medgemma-27b-it` | d3 | F | download retries exhausted | run_state | — | 0 | 2026-04-03T09:55:20 |
| `HuggingFaceH4/zephyr-7b-beta` | d3 | G | download retries exhausted | run_report | yes | 1 | 2026-03-30T03:42:05 |
| `mlx-community/dbrx-instruct-4bit` | d3 | C | download retries exhausted | run_state | — | 1 | 2026-04-03T06:55:29 |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16` | d1 | D | download retries exhausted | run_state | — | 1 | 2026-04-03T01:56:00 |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8` | d5 | D | download retries exhausted | run_state | — | 1 | 2026-04-03T09:14:29 |
| `Qwen/Qwen2.5-Math-72B-Instruct` | d5 | G | download retries exhausted | run_report | yes | 2 | 2026-04-02T22:24:01 |
| `Qwen/Qwen2.5-VL-72B-Instruct` | d5 | F | download retries exhausted | run_report | yes | 2 | 2026-04-02T22:24:01 |
| `Qwen/Qwen3.5-122B-A10B` | d1 | G | download retries exhausted | run_report | yes | 2 | 2026-04-02T22:24:01 |
| `Qwen/Qwen3.5-27B` | d2 | G | download retries exhausted | run_report | yes | 1 | 2026-04-01T16:13:42 |
| `Qwen/Qwen3.5-35B-A3B` | d5 | G | download retries exhausted | run_report | yes | 1 | 2026-04-02T22:24:01 |
| `Qwen/Qwen3.5-35B-A3B-Base` | d5 | G | download retries exhausted | run_report | yes | 1 | 2026-04-02T22:24:01 |
| `Qwen/Qwen3.5-397B-A17B` | d1 | G | download retries exhausted | run_report | yes | 2 | 2026-04-02T22:24:01 |
| `rombodawg/Rombos-LLM-V2.5-Qwen-72b` | d5 | D | download retries exhausted | run_report | yes | 2 | 2026-04-02T22:24:01 |
| `SinclairSchneider/dbrx-base-quantization-fixed` | d3 | C | download retries exhausted | run_state | — | 1 | 2026-04-03T05:18:56 |
| `SinclairSchneider/dbrx-instruct-quantization-fixed` | d3 | C | download retries exhausted | run_state | — | 1 | 2026-04-03T06:36:08 |
| `tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF` | d5 | D | download retries exhausted | run_report | yes | 1 | 2026-03-29T01:27:21 |
| `tiiuae/falcon-180B` | d1 | A | download retries exhausted | run_state | — | 0 | 2026-03-25T15:24:52 |
| `unsloth/DeepSeek-V3-GGUF` | d1 | C | download retries exhausted | run_report | yes | 3 | 2026-04-02T22:24:01 |
| `xai-org/grok-2` | d1 | G | download retries exhausted | run_state | — | 1 | 2026-04-03T02:44:21 |

<details><summary>Error text + run-report history</summary>

### `alpindale/dbrx-instruct`

**Primary error:**

```
Failed to download model-00002-of-00061.safetensors after 5 attempts: aria2c error for model-00002-of-00061.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00002-of-00061.safetensors after 5 attempts: aria2c error for model-00002-of-00061.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `cognitivecomputations/dolphin-2.9.2-qwen2-72b`

**Primary error:**

```
Failed to download model-00004-of-00031.safetensors after 5 attempts: aria2c error for model-00004-of-00031.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-01_03-22-55.md`

```
Failed to download model-00004-of-00031.safetensors after 5 attempts: aria2c error for model-00004-of-00031.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-28_02-00-05.md`

```
[Errno 28] No space left on device: '/mnt/models/d5/uncensored/cognitivecomputations'
```

### `google/gemma-3-4b-it`

**Primary error:**

```
Failed to download model-00002-of-00002.safetensors after 5 attempts: aria2c error for model-00002-of-00002.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-01_03-22-55.md`

```
Failed to download model-00002-of-00002.safetensors after 5 attempts: aria2c error for model-00002-of-00002.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `google/gemma-4-26B-A4B`

**Primary error:**

```
Failed to download model-00001-of-00002.safetensors after 5 attempts: aria2c error for model-00001-of-00002.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00001-of-00002.safetensors after 5 attempts: aria2c error for model-00001-of-00002.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `google/gemma-4-26B-A4B-it`

**Primary error:**

```
Failed to download model-00002-of-00002.safetensors after 5 attempts: aria2c error for model-00002-of-00002.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00002-of-00002.safetensors after 5 attempts: aria2c error for model-00002-of-00002.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `google/gemma-4-31B`

**Primary error:**

```
Failed to download model-00002-of-00002.safetensors after 5 attempts: aria2c error for model-00002-of-00002.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00002-of-00002.safetensors after 5 attempts: aria2c error for model-00002-of-00002.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `google/gemma-4-31B-it`

**Primary error:**

```
Failed to download model-00001-of-00002.safetensors after 5 attempts: aria2c error for model-00001-of-00002.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00001-of-00002.safetensors after 5 attempts: aria2c error for model-00001-of-00002.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `google/gemma-4-E2B`

**Primary error:**

```
Failed to download model.safetensors after 5 attempts: aria2c error for model.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model.safetensors after 5 attempts: aria2c error for model.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `google/gemma-4-E2B-it`

**Primary error:**

```
Failed to download tokenizer.json after 5 attempts: aria2c error for tokenizer.json: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download tokenizer.json after 5 attempts: aria2c error for tokenizer.json: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `google/gemma-4-E4B`

**Primary error:**

```
Failed to download tokenizer.json after 5 attempts: aria2c error for tokenizer.json: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download tokenizer.json after 5 attempts: aria2c error for tokenizer.json: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `google/gemma-4-E4B-it`

**Primary error:**

```
Failed to download tokenizer.json after 5 attempts: aria2c error for tokenizer.json: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download tokenizer.json after 5 attempts: aria2c error for tokenizer.json: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `google/medgemma-27b-it`

**Primary error:**

```
Failed to download model-00002-of-00012.safetensors after 5 attempts: aria2c error for model-00002-of-00012.safetensors: Authorization failed.
```

### `HuggingFaceH4/zephyr-7b-beta`

**Primary error:**

```
Failed to download model-00005-of-00008.safetensors after 5 attempts: aria2c error for model-00005-of-00008.safetensors: File /mnt/models/d3/.tmp/HuggingFaceH4_zephyr-7b-beta/model-00005-of-00008.safetensors exists, but a control file(*.aria2) does not exist. Download was canceled in order to prevent your file from being truncated to 0. If you are sure to download the file all over again, then delete it or add --allow-overwrite=true option and restart aria2.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-27_05-30-32.md`

```
Failed to download model-00005-of-00008.safetensors after 5 attempts: aria2c error for model-00005-of-00008.safetensors: File /mnt/models/d3/.tmp/HuggingFaceH4_zephyr-7b-beta/model-00005-of-00008.safetensors exists, but a control file(*.aria2) does not exist. Download was canceled in order to prevent your file from being truncated to 0. If you are sure to download the file all over again, then delete it or add --allow-overwrite=true option and restart aria2.
```

### `mlx-community/dbrx-instruct-4bit`

**Primary error:**

```
Failed to download model-00002-of-00014.safetensors after 5 attempts: aria2c error for model-00002-of-00014.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00002-of-00014.safetensors after 5 attempts: aria2c error for model-00002-of-00014.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16`

**Primary error:**

```
Failed to download model-00007-of-00050.safetensors after 5 attempts: aria2c error for model-00007-of-00050.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00007-of-00050.safetensors after 5 attempts: aria2c error for model-00007-of-00050.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8`

**Primary error:**

```
Failed to download model-00001-of-00026.safetensors after 5 attempts: aria2c error for model-00001-of-00026.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00001-of-00026.safetensors after 5 attempts: aria2c error for model-00001-of-00026.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `Qwen/Qwen2.5-Math-72B-Instruct`

**Primary error:**

```
Failed to download model-00033-of-00037.safetensors after 5 attempts: aria2c error for model-00033-of-00037.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-01_03-22-55.md`

```
Failed to download model-00033-of-00037.safetensors after 5 attempts: aria2c error for model-00033-of-00037.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-28_02-00-05.md`

```
[Errno 28] No space left on device: '/mnt/models/d5/raw/Qwen'
```

### `Qwen/Qwen2.5-VL-72B-Instruct`

**Primary error:**

```
Failed to download model-00006-of-00038.safetensors after 5 attempts: aria2c error for model-00006-of-00038.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-01_03-22-55.md`

```
Failed to download model-00006-of-00038.safetensors after 5 attempts: aria2c error for model-00006-of-00038.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-28_02-00-05.md`

```
[Errno 28] No space left on device: '/mnt/models/d5/raw/Qwen'
```

### `Qwen/Qwen3.5-122B-A10B`

**Primary error:**

```
Failed to download model.safetensors-00011-of-00039.safetensors after 5 attempts: aria2c error for model.safetensors-00011-of-00039.safetensors: Download aborted.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-01_03-22-55.md`

```
Failed to download model.safetensors-00011-of-00039.safetensors after 5 attempts: aria2c error for model.safetensors-00011-of-00039.safetensors: Download aborted.
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-30_14-40-54.md`

```
Failed to download model.safetensors-00008-of-00039.safetensors after 5 attempts: aria2c error for model.safetensors-00008-of-00039.safetensors: Download aborted.
```

### `Qwen/Qwen3.5-27B`

**Primary error:**

```
Failed to download model.safetensors-00005-of-00094.safetensors after 5 attempts: aria2c error for model.safetensors-00005-of-00094.safetensors: Download aborted.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-30_14-40-54.md`

```
Failed to download model.safetensors-00005-of-00094.safetensors after 5 attempts: aria2c error for model.safetensors-00005-of-00094.safetensors: Download aborted.
```

### `Qwen/Qwen3.5-35B-A3B`

**Primary error:**

```
Failed to download model.safetensors-00006-of-00014.safetensors after 5 attempts: aria2c error for model.safetensors-00006-of-00014.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-01_03-22-55.md`

```
Failed to download model.safetensors-00006-of-00014.safetensors after 5 attempts: aria2c error for model.safetensors-00006-of-00014.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `Qwen/Qwen3.5-35B-A3B-Base`

**Primary error:**

```
Failed to download model.safetensors-00002-of-00014.safetensors after 5 attempts: aria2c error for model.safetensors-00002-of-00014.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-01_03-22-55.md`

```
Failed to download model.safetensors-00002-of-00014.safetensors after 5 attempts: aria2c error for model.safetensors-00002-of-00014.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `Qwen/Qwen3.5-397B-A17B`

**Primary error:**

```
Failed to download model.safetensors-00001-of-00094.safetensors after 5 attempts: aria2c error for model.safetensors-00001-of-00094.safetensors: Download aborted.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-01_03-22-55.md`

```
Failed to download model.safetensors-00001-of-00094.safetensors after 5 attempts: aria2c error for model.safetensors-00001-of-00094.safetensors: Download aborted.
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-29_21-45-34.md`

```
[Errno 28] No space left on device: '/mnt/models/d1/raw/Qwen/Qwen3.5-397B-A17B'
```

### `rombodawg/Rombos-LLM-V2.5-Qwen-72b`

**Primary error:**

```
Failed to download model-00002-of-00031.safetensors after 5 attempts: aria2c error for model-00002-of-00031.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-01_03-22-55.md`

```
Failed to download model-00002-of-00031.safetensors after 5 attempts: aria2c error for model-00002-of-00031.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-28_02-00-05.md`

```
[Errno 28] No space left on device: '/mnt/models/d5/uncensored/rombodawg'
```

### `SinclairSchneider/dbrx-base-quantization-fixed`

**Primary error:**

```
Failed to download model-00001-of-00061.safetensors after 5 attempts: aria2c error for model-00001-of-00061.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00001-of-00061.safetensors after 5 attempts: aria2c error for model-00001-of-00061.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `SinclairSchneider/dbrx-instruct-quantization-fixed`

**Primary error:**

```
Failed to download model-00003-of-00061.safetensors after 5 attempts: aria2c error for model-00003-of-00061.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download model-00003-of-00061.safetensors after 5 attempts: aria2c error for model-00003-of-00061.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

### `tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF`

**Primary error:**

```
Failed to download Llama-3.3-70B-Instruct-abliterated-Q3_K_M.gguf after 5 attempts: aria2c error for Llama-3.3-70B-Instruct-abliterated-Q3_K_M.gguf: Download aborted.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-28_02-00-05.md`

```
Failed to download Llama-3.3-70B-Instruct-abliterated-Q3_K_M.gguf after 5 attempts: aria2c error for Llama-3.3-70B-Instruct-abliterated-Q3_K_M.gguf: Download aborted.
```

### `tiiuae/falcon-180B`

**Primary error:**

```
Failed to download model-00005-of-00081.safetensors after 5 attempts: aria2c error for model-00005-of-00081.safetensors: Download aborted.
```

### `unsloth/DeepSeek-V3-GGUF`

**Primary error:**

```
Failed to download DeepSeek-V3-Q4_K_M/DeepSeek-V3-Q4_K_M-00002-of-00009.gguf after 5 attempts: aria2c error for DeepSeek-V3-Q4_K_M/DeepSeek-V3-Q4_K_M-00002-of-00009.gguf: Download aborted.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-01_03-22-55.md`

```
Failed to download DeepSeek-V3-Q4_K_M/DeepSeek-V3-Q4_K_M-00002-of-00009.gguf after 5 attempts: aria2c error for DeepSeek-V3-Q4_K_M/DeepSeek-V3-Q4_K_M-00002-of-00009.gguf: Download aborted.
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-29_21-45-34.md`

```
[Errno 28] No space left on device: '/mnt/models/d5/quantized/unsloth/DeepSeek-V3-GGUF'
```

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-03-28_02-00-05.md`

```
[Errno 28] No space left on device: '/mnt/models/d5/quantized'
```

### `xai-org/grok-2`

**Primary error:**

```
Failed to download pytorch_model-00002-TP-common.safetensors after 5 attempts: aria2c error for pytorch_model-00002-TP-common.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

**Incidents from run reports (newest first):**

- `download_fail` — `/mnt/models/d3/logs/run-report-2026-04-02_18-24-01.md`

```
Failed to download pytorch_model-00002-TP-common.safetensors after 5 attempts: aria2c error for pytorch_model-00002-TP-common.safetensors: SSL/TLS handshake failure: The TLS connection was non-properly terminated.
```

</details>

## Skipped (gated / token) (`skipped_gated`)

| Model id | Drive | Tier | Reason kind | Primary | Hist-only | #inc | Updated (UTC) |
|----------|-------|------|-------------|---------|-----------|-----|---------------|
| `databricks/dbrx-base` | — | — | skipped | run_state | — | 0 | 2026-03-25T15:24:55 |
| `databricks/dbrx-instruct` | — | — | skipped | run_state | — | 0 | 2026-03-25T15:24:55 |
| `google/gemini-3-flash-preview` | — | F | skipped | run_state | — | 0 | 2026-04-01T07:22:55 |
| `google/gemini-3.1-flash-lite-preview` | — | F | skipped | run_state | — | 0 | 2026-04-01T07:22:55 |
| `MiniMaxAI/MiniMax-M2.7` | — | G | skipped | run_state | — | 0 | 2026-04-01T07:22:55 |

<details><summary>Error text + run-report history</summary>

### `databricks/dbrx-base`

**Primary error:**

```
No HF token access
```

### `databricks/dbrx-instruct`

**Primary error:**

```
No HF token access
```

### `google/gemini-3-flash-preview`

**Primary error:**

```
No HF token access
```

### `google/gemini-3.1-flash-lite-preview`

**Primary error:**

```
No HF token access
```

### `MiniMaxAI/MiniMax-M2.7`

**Primary error:**

```
No HF token access
```

</details>
