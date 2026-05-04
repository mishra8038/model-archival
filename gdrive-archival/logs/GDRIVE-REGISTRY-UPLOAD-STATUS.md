# GDrive registry upload status

_Generated: 2026-05-02T14:45:23Z (UTC) — discovery under `models_mount` + [`logs/uploaded.log`](uploaded.log) (`registry-model` / `registry-tree` / `registry-d5`)._

## Summary

| Item | Value |
|------|-------|
| `models_mount` | `/mnt` |
| Model revision dirs discovered | 88 |
| Uploaded at least once (in log ∩ on disk) | 0 |
| Pending (on disk, not in log) | 88 |
| In log but path missing locally | 0 |
| Newest `registry-model` log timestamp | — |
| Last `registry-d5` (full `d5/` tree) log timestamp | — (not logged yet) |
| **Tracker** (`registry-upload-state.json`): models marked uploaded (skip rclone) | 0 |
| **Tracker**: `d5/` full tree marked complete | no |
| Pre-upload verify failure lines (`gdrive-preupload-verify-failures.jsonl`) | 0 |

**Regenerate:** `python3 backup.py upload-registry-status` — also refreshed automatically at the end of each `backup-registry` run.

## Pending (not yet in uploaded.log)

- `d1/raw/Qwen/Qwen2.5-14B/97e1e76335b7017d8f67c08a19d103c0504298c9`
- `d1/raw/Qwen/Qwen2.5-3B/3aab1f1954e9cc14eb9509a215f9e5ca08227a9b`
- `d1/raw/Qwen/Qwen2.5-7B/d149729398750b98c0af14eb82c78cfe92750796`
- `d1/raw/Qwen/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137`
- `d2/raw/Qwen/Qwen2.5-14B-Instruct-1M/620fad32de7bdd2293b3d99b39eba2fe63e97438`
- `d2/raw/Qwen/Qwen2.5-14B-Instruct/cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8`
- `d2/raw/Qwen/Qwen2.5-32B-Instruct/5ede1c97bbab6ce5cda5812749b4c0bdf79b18dd`
- `d2/raw/Qwen/Qwen2.5-72B-Instruct/495f39366efef23836d0cfae4fbe635880d2be31`
- `d2/raw/Qwen/Qwen2.5-7B-Instruct/a09a35458c702b33eeacc393d103063234e8bc28`
- `d2/raw/Qwen/Qwen2.5-Coder-32B-Instruct/381fc969f78efac66bc87ff7ddeadb7e73c218a7`
- `d2/raw/Qwen/Qwen3-14B/40c069824f4251a91eefaf281ebe4c544efd3e18`
- `d2/raw/Qwen/Qwen3-30B-A3B/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39`
- `d2/raw/Qwen/Qwen3-8B/b968826d9c46dd6066d109eabc6255188de91218`
- `d2/raw/Qwen/Qwen3-Coder-30B-A3B-Instruct/b2cff646eb4bb1d68355c01b18ae02e7cf42d120`
- `d2/raw/Qwen/Qwen3.5-27B/b7ca741b86de18df552fd2cc952861e04621a4bd`
- `d2/uncensored/cognitivecomputations/Dolphin3.0-Llama3.1-8B/f065677950dfc7e708d518d64cf1f5041ee007a0`
- `d2/uncensored/huihui-ai/DeepSeek-R1-Distill-Llama-70B-abliterated/116ff0fa55425b094a38a6bbf6faf2f5cafea335`
- `d2/uncensored/huihui-ai/DeepSeek-R1-Distill-Qwen-32B-abliterated/939b7e288235a393e2aac8a16ddc3d48f9406f03`
- `d2/uncensored/huihui-ai/Llama-3.3-70B-Instruct-abliterated/fa13334669544bab573e0e5313cad629a9c02e2c`
- `d2/uncensored/huihui-ai/Mistral-Small-24B-Instruct-2501-abliterated/04d6728a8ecd8236b59f5f91ad7a8b9f3dafa57d`
- `d2/uncensored/mlabonne/Llama-3.1-70B-Instruct-lorablated/5bb381611cfa4512f63affbb199c218b8a38bd76`
- `d2/uncensored/mlabonne/NeuralDaredevil-8B-abliterated/6567010926ff93a5e9fb809534d61ab667a86674`
- `d3/quantized/Qwen/QwQ-32B-GGUF/8728e66249190b78dee8404869827328527f6b3b`
- `d3/quantized/Qwen/Qwen3-32B-GGUF/938a7432affaec9157f883a87164e2646ae17555`
- `d3/quantized/bartowski/Codestral-22B-v0.1-GGUF/0e6abe14d6aeaf2c99d5dc9973205e8e38692d90`
- `d3/quantized/bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF/8f248fa2072348f77a8bc37754e470de1f61866e`
- `d3/quantized/bartowski/DeepSeek-R1-Distill-Llama-70B-GGUF/1842c5f7280f933ead58adf8afd078672c9f6cd0`
- `d3/quantized/bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF/1dc8cf9ffa5dd333057ea1b09ccf4772d8726dec`
- `d3/quantized/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/bf5b95e96dac0462e2a09145ec66cae9a3f12067`
- `d3/quantized/bartowski/Mistral-7B-Instruct-v0.3-GGUF/61fd4167fff3ab01ee1cfe0da183fa27a944db48`
- `d3/quantized/bartowski/Mistral-Small-24B-Instruct-2501-GGUF/62a613c92d5a5f73bba6d348b51433b232c4640c`
- `d3/quantized/bartowski/Qwen2.5-14B-Instruct-GGUF/05244aa5d871c661c80082a15d3bce44714d068d`
- `d3/quantized/bartowski/Qwen2.5-32B-Instruct-GGUF/2116cbb385b8ce3a4d28cf3bf1cd2039a55821a6`
- `d3/quantized/bartowski/Qwen2.5-7B-Instruct-GGUF/8911e8a47f92bac19d6f5c64a2e2095bd2f7d031`
- `d3/quantized/bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/40b525506a4f98ed425882fa6dfc90cc8139065e`
- `d3/quantized/bartowski/google_gemma-3-27b-it-GGUF/4a05c54413bd0d87d77a97af403266f69cec0ee6`
- `d3/quantized/bartowski/phi-4-GGUF/19cd65f97c2f1712a81c506611d3f9c94b16a1e1`
- `d3/quantized/mistralai/Devstral-Small-2507_gguf/ee2f0c00c5c86862f471fbf533268cf01b80d4a6`
- `d3/quantized/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4/ce1b118ae66ec705d02c241525192832eb045fd3`
- `d3/quantized/unsloth/Phi-4-mini-instruct-GGUF/78eb92a46fc37e6b524df991ed9aca9bc6aa7b80`
- `d3/quantized/unsloth/Qwen3-4B-Instruct-2507-GGUF/a06e946bb6b655725eafa393f4a9745d460374c9`
- `d3/quantized/unsloth/phi-4-unsloth-bnb-4bit/26dd1bdcaaab6bf52793b1a09b259ceed592d092`
- `d3/raw/Qwen/Qwen2.5-Math-7B-Instruct/ef9926d75ab1d54532f6a30dd5e760355eb9aa4d`
- `d3/raw/Qwen/Qwen2.5-VL-7B-Instruct/cc594898137f460bfe9f0759e9844b3ce807cfb5`
- `d3/raw/Qwen/Qwen3.5-4B-Base/57370f0ea82c3cca33558a95212e032c344e5fd5`
- `d3/raw/Qwen/Qwen3.5-4B/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`
- `d3/raw/Qwen/Qwen3.5-9B-Base/2d021f1887f1fe402bf2c53ed69d7f0fc4709ec9`
- `d3/raw/Qwen/Qwen3.5-9B/c202236235762e1c871ad0ccb60c8ee5ba337b9a`
- `d3/specialist/chemistry/raw/AI4Chem/ChemLLM-7B-Chat/b8b2ea19e48f53d190fe8dced94572717f8e89a2`
- `d3/specialist/chemistry/raw/OpenDFM/ChemDFM-v1.5-8B/f5790d56a903ce480b1eff8d0adf9613d8acee0c`
- `d3/specialist/chemistry/raw/OpenDFM/ChemDFM-v2.0-14B/b3b1d2143bb3e307e6b6dae794f6e9b0a83a45ef`
- `d3/specialist/chemistry/raw/seyonec/ChemBERTa-zinc-base-v1/761d6a18cf99db371e0b43baf3e2d21b3e865a20`
- `d3/specialist/embeddings/raw/jinaai/jina-embeddings-v3/f1944de8402dcd5f2b03f822a4bc22a7f2de2eb9`
- `d3/specialist/law/raw/Equall/Saul-7B-Instruct-v1/2133ba7923533934e78f73848045299dd74f08d2`
- `d3/specialist/math/raw/EleutherAI/llemma_7b/e223eee41c53449e6ea6548c9b71c50865e4a85c`
- `d3/specialist/math/raw/Qwen/Qwen2.5-Math-1.5B/4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2`
- `d3/specialist/math/raw/deepseek-ai/deepseek-math-7b-instruct/0a5828f800a36df0fd7f0ed581b983246c0677ff`
- `d3/specialist/math/raw/mistralai/Mathstral-7B-v0.1/ec3a48484ef241dfe03282edcb0f25e564923823`
- `d3/specialist/medicine/raw/FreedomIntelligence/HuatuoGPT2-7B/1490cc91a93d2d0d2fdc9d3681bc1c5099cde163`
- `d3/specialist/medicine/raw/aaditya/Llama3-OpenBioLLM-8B/70d6bb521cab6ca755b675ade38831eedf89d31c`
- `d3/specialist/medicine/raw/cambridgeltl/SapBERT-from-PubMedBERT-fulltext/090663c3ae57bf35ffe4d0d468a2a88d03051a4d`
- `d3/specialist/medicine/raw/dmis-lab/biobert-base-cased-v1.2/67c9c25b46986521ca33df05d8540da1210b3256`
- `d3/specialist/medicine/raw/emilyalsentzer/Bio_ClinicalBERT/d5892b39a4adaed74b92212a44081509db72f87b`
- `d3/specialist/medicine/raw/google/medgemma-27b-text-it/5b667cf2ddcf064085bc90952edb35a0edbfb79c`
- `d3/specialist/medicine/raw/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext/e1354b7a3a09615f6aba48dfad4b7a613eef7062`
- `d3/specialist/medicine/raw/stanford-crfm/BioMedLM/3e1a0abb814b8398bc34b4b6680ecf2c26d6a66f`
- `d3/specialist/reasoning/raw/Qwen/QwQ-32B/976055f8c83f394f35dbd3ab09a285a984907bd0`
- `d3/specialist/science/quantized/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8/f8dc1c0afee92f44417695b4f5ddca9afc95ea58`
- `d3/specialist/science/quantized/tensorblock/Llama-3.2-3B-Instruct-GGUF/a95b197289958265f8eb95fc455b5766aed89b02`
- `d3/specialist/science/raw/OpenDFM/RetroDFM-R-v0-8B/c828b32bf1da3143ed1d8402dd09cc7f8747727f`
- `d3/specialist/science/raw/allenai/OLMo-2-1124-7B/7df9a82518afdecae4e8c026b27adccc8c1f0032`
- `d3/specialist/science/raw/apple/DiffuCoder-7B-Base/a2c33054cbe99b9ab7af074f09b1d13943157ff1`
- `d3/specialist/science/raw/apple/DiffuCoder-7B-Instruct/4fdd4580064ca5d11808069ce78f88d068753c96`
- `d3/specialist/science/raw/apple/DiffuCoder-7B-cpGRPO/98bc42bfd871eeec92fd0a8439ab34f75b405204`
- `d3/specialist/science/raw/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/cbd3fa9f933d55ef16a84236559f4ee2a0526848`
- `d3/specialist/science/raw/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-Base-BF16/97ab8012882a655dc38df4fee47422aca9caca07`
- `d3/uncensored/CombinHorizon/d976a5d6768d54c5e59a88fe63238a055c30c06a`
- `d3/uncensored/FINGU-AI/49b7b720ddd40ccdca303922037a4bb34b1ca33b`
- `d3/uncensored/FINGU-AI/RomboUltima-32B/98a732a32e2366a2ab8f08fdc3d668892e7c1f7f`
- `d3/uncensored/failspy/Meta-Llama-3-70B-Instruct-abliterated-v3.5/fc951b03d92972ab52ad9392e620eba6173526b9`
- `d3/uncensored/huihui-ai/Qwen2.5-72B-Instruct-abliterated/ff4f9fe269d95bad2bd741af23b805cd9f449a8b`
- `d3/uncensored/mlabonne/NeuralDaredevil-8B-abliterated-GGUF/1b757b9c39eb38b8d12a7c0f71c6e48b5cc23053`
- `d3/uncensored/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8/03c8909abace9e03b0d29fe4fb574e1cdee620cb`
- `d3/uncensored/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4/b1ffe4992d7db6d768453a551a656b8d12c638fb`
- `d3/uncensored/tensorblock/DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF/89b48f9faec5188e7a05011676538aaf0889ad9a`
- `d3/uncensored/tensorblock/DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF/de00cb261ea6fea79a45ffbb6e583befed7be954`
- `d3/uncensored/tensorblock/Llama-3.3-70B-Instruct-abliterated-GGUF/92582e3714cbade9d0211778c8b9bd08c9fca8f6`
- `d3/uncensored/tensorblock/Mistral-Small-24B-Instruct-2501-abliterated-GGUF/dd90f4a1a90029c907f18b8111fd64df05a8c6f3`

## Uploaded model dirs (present on disk + in log)

*None.*

## Related logs

- Pre-upload checksum skips: [`gdrive-preupload-verify-report.md`](gdrive-preupload-verify-report.md)
