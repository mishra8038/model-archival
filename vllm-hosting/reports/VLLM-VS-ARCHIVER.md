# vLLM archive manifest vs archiver

- **Manifest:** `/home/x/dev/model-archival/vllm-hosting/config/vllm-archive-manifest.yaml`
- **run_state.json:** `/mnt/models/d3/run_state.json` (present)
- **Merged registry:** `/home/x/dev/model-archival/model-archiver/config` (`registry.yaml` + `registry-specialists.yaml` + …)
- **Verified on disk** (complete `manifest.json` + `.sha256` sidecars): **34** / 61

| Status | HF repo | Category | run_state | Registry id | Verified path(s) |
|--------|---------|----------|-----------|-------------|------------------|
| yes | `deepseek-ai/deepseek-coder-6.7b-instruct` | core_queue | `complete` | `deepseek-ai/deepseek-coder-6.7b-instruct` | `d3:/mnt/models/d3/raw/deepseek-ai/deepseek-coder-6.7b-instruct/e5d64addd26a6a1db0f9b863abf6ee3141936807` |
| no | `Qwen/Qwen2.5-Coder-7B-Instruct` | core_queue | `pending` | — | — |
| no | `meta-llama/Meta-Llama-3.1-8B-Instruct` | core_queue | `pending` | — | — |
| yes | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | core_queue | `complete` | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | `d2:/mnt/models/d2/raw/deepseek-ai/DeepSeek-R1-Distill-Llama-8B/6a6f4aa4197940add57724a7707d069478df56b1`<br>`d2:/mnt/models/d2/raw/deepseek-ai/DeepSeek-R1-Distill-Llama-8B/latest` |
| yes | `google/gemma-4-E2B-it` | core_queue | `complete` | `google/gemma-4-E2B-it` | `d3:/mnt/models/d3/raw/google/gemma-4-E2B-it/4742fe843cc01b9aed62122f6e0ddd13ea48b3d3` |
| yes | `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct` | core_queue | `complete` | `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct` | `d2:/mnt/models/d2/raw/deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct/e434a23f91ba5b4923cf6c9d9a238eb4a08e3a11` |
| yes | `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | core_queue | `complete` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | `d2:/mnt/models/d2/raw/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B/1df8507178afcc1bef68cd8c393f61a886323761`<br>`d2:/mnt/models/d2/raw/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B/latest` |
| no | `Qwen/Qwen2.5-Coder-14B-Instruct` | core_queue | `pending` | — | — |
| yes | `bigcode/starcoder2-15b` | core_queue | `complete` | `bigcode/starcoder2-15b` | `d2:/mnt/models/d2/raw/bigcode/starcoder2-15b/46d44742909c03ac8cee08eb03fdebce02e193ec` |
| yes | `google/gemma-4-E4B-it` | core_queue | `complete` | `google/gemma-4-E4B-it` | `d3:/mnt/models/d3/raw/google/gemma-4-E4B-it/292a7e278a400932df35f9fd4b1501edd04133a5` |
| yes | `google/gemma-4-26B-A4B-it` | core_queue | `complete` | `google/gemma-4-26B-A4B-it` | `d2:/mnt/models/d2/raw/google/gemma-4-26B-A4B-it/47b6801b24d15ff9bcd8c96dfaea0be9ed3a0301` |
| yes | `Qwen/Qwen2.5-Coder-32B-Instruct` | core_queue | `complete` | `Qwen/Qwen2.5-Coder-32B-Instruct` | `d2:/mnt/models/d2/raw/Qwen/Qwen2.5-Coder-32B-Instruct/381fc969f78efac66bc87ff7ddeadb7e73c218a7`<br>`d2:/mnt/models/d2/raw/Qwen/Qwen2.5-Coder-32B-Instruct/latest` |
| yes | `deepseek-ai/deepseek-coder-33b-instruct` | core_queue | `complete` | `deepseek-ai/deepseek-coder-33b-instruct` | `d1:/mnt/models/d1/raw/deepseek-ai/deepseek-coder-33b-instruct/61dc97b922b13995e7f83b7c8397701dbf9cfd4c` |
| no | `mistralai/Mixtral-8x7B-Instruct-v0.1` | core_queue | `pending` | `mistralai/Mixtral-8x7B-Instruct-v0.1` | — |
| no | `dphn/dolphin-2.6-mistral-7b` | core_queue | `pending` | — | — |
| yes | `cognitivecomputations/Dolphin3.0-Llama3.1-8B` | core_queue | `complete` | `cognitivecomputations/Dolphin3.0-Llama3.1-8B` | `d2:/mnt/models/d2/uncensored/cognitivecomputations/Dolphin3.0-Llama3.1-8B/f065677950dfc7e708d518d64cf1f5041ee007a0` |
| no | `huihui-ai/Dolphin3.0-Llama3.1-8B-abliterated` | core_queue | `pending` | — | — |
| no | `dphn/dolphin-2.7-mixtral-8x7b` | core_queue | `pending` | — | — |
| yes | `mlabonne/NeuralDaredevil-8B-abliterated` | core_queue | `complete` | `mlabonne/NeuralDaredevil-8B-abliterated` | `d2:/mnt/models/d2/uncensored/mlabonne/NeuralDaredevil-8B-abliterated/6567010926ff93a5e9fb809534d61ab667a86674`<br>`d2:/mnt/models/d2/uncensored/mlabonne/NeuralDaredevil-8B-abliterated/latest` |
| yes | `Qwen/Qwen3-8B` | core_queue | `complete` | `Qwen/Qwen3-8B` | `d2:/mnt/models/d2/raw/Qwen/Qwen3-8B/b968826d9c46dd6066d109eabc6255188de91218` |
| yes | `Qwen/Qwen3-14B` | core_queue | `complete` | `Qwen/Qwen3-14B` | `d2:/mnt/models/d2/raw/Qwen/Qwen3-14B/40c069824f4251a91eefaf281ebe4c544efd3e18` |
| no | `Qwen/Qwen3-30B-A3B-Instruct-2507` | core_queue | `pending` | — | — |
| yes | `Qwen/Qwen3-32B` | core_queue | `complete` | `Qwen/Qwen3-32B` | `d1:/mnt/models/d1/raw/Qwen/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137` |
| yes | `meta-llama/Llama-3.2-3B-Instruct` | core_queue | `complete` | `meta-llama/Llama-3.2-3B-Instruct` | `d2:/mnt/models/d2/raw/meta-llama/Llama-3.2-3B-Instruct/0cb88a4f764b7a12671c53f0838cd831a0843b95` |
| yes | `BAAI/bge-m3` | core_queue | `complete` | `BAAI/bge-m3` | `d3:/mnt/models/d3/raw/BAAI/bge-m3/5617a9f61b028005a4858fdac845db406aefb181`<br>`d3:/mnt/models/d3/raw/BAAI/bge-m3/latest` |
| no | `ibm-granite/granite-embedding-107m-multilingual` | core_queue | `pending` | — | — |
| no | `nomic-ai/nomic-embed-text-v1.5` | core_queue | `pending` | — | — |
| no | `google/embeddinggemma-300m` | core_queue | `pending` | — | — |
| no | `Snowflake/snowflake-arctic-embed-m-long` | core_queue | `pending` | — | — |
| no | `mixedbread-ai/mxbai-embed-large-v1` | core_queue | `pending` | — | — |
| yes | `BAAI/bge-large-en-v1.5` | core_queue | `complete` | `BAAI/bge-large-en-v1.5` | `d3:/mnt/models/d3/raw/BAAI/bge-large-en-v1.5/d4aa6901d3a41ba39fb536a557fa166f842b0e09`<br>`d3:/mnt/models/d3/raw/BAAI/bge-large-en-v1.5/latest` |
| no | `Qwen/Qwen3-Embedding-4B` | core_queue | `pending` | — | — |
| no | `Qwen/Qwen3.5-4B-Instruct-2507` | core_queue | `pending` | — | — |
| no | `google/gemma-3-4b-it` | core_queue | `pending` | `google/gemma-3-4b-it` | — |
| no | `google/medgemma-4b-it` | core_queue | `pending` | `google/medgemma-4b-it` | — |
| no | `mistralai/Mathstral-7B-v0.1` | core_queue | `complete` | `mistralai/Mathstral-7B-v0.1` | — |
| yes | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | core_queue | `complete` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | `d3:/mnt/models/d3/raw/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B/916b56a44061fd5cd7d6a8fb632557ed4f724f60`<br>`d3:/mnt/models/d3/raw/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B/latest` |
| yes | `Qwen/Qwen2.5-VL-7B-Instruct` | core_queue | `complete` | `Qwen/Qwen2.5-VL-7B-Instruct` | `d3:/mnt/models/d3/raw/Qwen/Qwen2.5-VL-7B-Instruct/cc594898137f460bfe9f0759e9844b3ce807cfb5`<br>`d3:/mnt/models/d3/raw/Qwen/Qwen2.5-VL-7B-Instruct/latest` |
| yes | `Qwen/Qwen3.5-9B` | core_queue | `complete` | `Qwen/Qwen3.5-9B` | `d3:/mnt/models/d3/raw/Qwen/Qwen3.5-9B/c202236235762e1c871ad0ccb60c8ee5ba337b9a`<br>`d3:/mnt/models/d3/raw/Qwen/Qwen3.5-9B/latest` |
| no | `microsoft/Phi-4` | core_queue | `pending` | — | — |
| yes | `mistralai/Mistral-Small-24B-Instruct-2501` | core_queue | `complete` | `mistralai/Mistral-Small-24B-Instruct-2501` | `d2:/mnt/models/d2/raw/mistralai/Mistral-Small-24B-Instruct-2501/9527884be6e5616bdd54de542f9ae13384489724`<br>`d2:/mnt/models/d2/raw/mistralai/Mistral-Small-24B-Instruct-2501/latest` |
| yes | `google/gemma-3-27b-it` | core_queue | `complete` | `google/gemma-3-27b-it` | `d2:/mnt/models/d2/raw/google/gemma-3-27b-it/005ad3404e59d6023443cb575daa05336842228a`<br>`d2:/mnt/models/d2/raw/google/gemma-3-27b-it/latest` |
| yes | `Qwen/Qwen3.5-27B` | core_queue | `complete` | `Qwen/Qwen3.5-27B` | `d2:/mnt/models/d2/raw/Qwen/Qwen3.5-27B/b7ca741b86de18df552fd2cc952861e04621a4bd`<br>`d2:/mnt/models/d2/raw/Qwen/Qwen3.5-27B/latest` |
| yes | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | core_queue | `complete` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | `d2:/mnt/models/d2/raw/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B/711ad2ea6aa40cfca18895e8aca02ab92df1a746`<br>`d2:/mnt/models/d2/raw/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B/latest` |
| no | `Qwen/QwQ-32B` | core_queue | `complete` | `Qwen/QwQ-32B` | — |
| no | `Qwen/Qwen2.5-VL-32B-Instruct` | core_queue | `pending` | — | — |
| no | `Qwen/Qwen3.5-35B-A3B` | core_queue | `pending` | `Qwen/Qwen3.5-35B-A3B` | — |
| no | `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B` | specialist | `pending` | — | — |
| no | `TechxGenus/starcoder2-15b-instruct` | specialist | `pending` | — | — |
| no | `open-r1/OlympicCoder-7B` | specialist | `pending` | — | — |
| yes | `open-r1/OlympicCoder-32B` | specialist | `complete` | `open-r1/OlympicCoder-32B` | `d2:/mnt/models/d2/raw/open-r1/OlympicCoder-32B/34113aee9d255591a1fa75b60d1e3422e82c3b1f` |
| yes | `Qwen/Qwen2.5-Math-7B-Instruct` | specialist | `complete` | `Qwen/Qwen2.5-Math-7B-Instruct` | `d3:/mnt/models/d3/raw/Qwen/Qwen2.5-Math-7B-Instruct/ef9926d75ab1d54532f6a30dd5e760355eb9aa4d`<br>`d3:/mnt/models/d3/raw/Qwen/Qwen2.5-Math-7B-Instruct/latest` |
| no | `deepseek-ai/deepseek-math-7b-instruct` | specialist | `complete` | `deepseek-ai/deepseek-math-7b-instruct` | — |
| yes | `Alibaba-NLP/gte-Qwen2-7B-instruct` | specialist | `complete` | `Alibaba-NLP/gte-Qwen2-7B-instruct` | `d3:/mnt/models/d3/raw/Alibaba-NLP/gte-Qwen2-7B-instruct/a8d08b36ada9cacfe34c4d6f80957772a025daf2`<br>`d3:/mnt/models/d3/raw/Alibaba-NLP/gte-Qwen2-7B-instruct/latest` |
| yes | `intfloat/e5-mistral-7b-instruct` | specialist | `complete` | `intfloat/e5-mistral-7b-instruct` | `d3:/mnt/models/d3/raw/intfloat/e5-mistral-7b-instruct/07163b72af1488142a360786df853f237b1a3ca1`<br>`d3:/mnt/models/d3/raw/intfloat/e5-mistral-7b-instruct/latest` |
| yes | `BAAI/bge-en-icl` | specialist | `complete` | `BAAI/bge-en-icl` | `d3:/mnt/models/d3/raw/BAAI/bge-en-icl/971c7e1445cc86656ca0bd85ed770b8675a40bb5`<br>`d3:/mnt/models/d3/raw/BAAI/bge-en-icl/latest` |
| yes | `meta-llama/Llama-3.2-11B-Vision-Instruct` | specialist | `complete` | `meta-llama/Llama-3.2-11B-Vision-Instruct` | `d3:/mnt/models/d3/raw/meta-llama/Llama-3.2-11B-Vision-Instruct/9eb2daaa8597bf192a8b0e73f848f3a102794df5`<br>`d3:/mnt/models/d3/raw/meta-llama/Llama-3.2-11B-Vision-Instruct/latest` |
| yes | `huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated` | uncensored | `complete` | `huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated` | `d2:/mnt/models/d2/uncensored/huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated/939b7e288235a393e2aac8a16ddc3d48f9406f03` |
| yes | `huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated` | uncensored | `complete` | `huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated` | `d2:/mnt/models/d2/uncensored/huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated/04d6728a8ecd8236b59f5f91ad7a8b9f3dafa57d`<br>`d2:/mnt/models/d2/uncensored/huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated/latest` |
| no | `huihui-ai/Qwen2.5-14B-Instruct-abliterated-v2` | uncensored | `pending` | `huihui-ai/Qwen2.5-14B-Instruct-abliterated-v2` | — |
| yes | `FINGU-AI/RomboUltima-32B` | uncensored | `complete` | `FINGU-AI/RomboUltima-32B` | `d3:/mnt/models/d3/uncensored/FINGU-AI/RomboUltima-32B/98a732a32e2366a2ab8f08fdc3d668892e7c1f7f` |
