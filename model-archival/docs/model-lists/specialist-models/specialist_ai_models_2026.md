# Specialist AI & Small Language Models — 2026 Reference Guide

---

## 1. Top Small Language Models (SLMs)

> Models up to ~10B parameters emerging as production leaders

| Model | Developer | Highlights |
|---|---|---|
| **Llama 4 Scout** | Meta | GPT-4-level reasoning, open weights, enterprise starting point (~10B active params) |
| **Gemma 3** | Google DeepMind | Multilingual + STEM leader, multimodal (vision + text), strong benchmark scores |
| **Qwen3 (0.6B–8B)** | Alibaba | 200+ languages, thinking/non-thinking dual mode, 131K context, CJK dominant |
| **Phi-3.5 Mini** | Microsoft | 3.8B params, 128K context, excels at math, logic & edge/mobile deployment |
| **Llama 3.2 (1B–3B)** | Meta | Default for on-device/mobile AI, optimised for Qualcomm & Apple Silicon |
| **Mistral Small 3** | Mistral AI | SMB-friendly, Apache 2.0, fast inference, available on HuggingFace & Ollama |
| **SmolLM3 (3B)** | Hugging Face | Agentic tool-calling, dual reasoning mode, strong math & coding for its size |

---

## 2. Top AI Models for Coding

| Model / Tool | Developer | Highlights |
|---|---|---|
| **Claude (Sonnet / Opus)** | Anthropic | Best for complex reasoning, refactoring, debugging, and deep code explanation |
| **GPT-5.2** | OpenAI | Gold standard for algorithmic tasks, SQL, unit tests, lowest syntax error rate |
| **Gemini 2.5 Pro** | Google | 1M token context, best for large codebase understanding and monorepos |
| **Llama 4** | Meta (open source) | Local/private deployment, highly customisable, enterprise data security |
| **DeepSeek V3 / R1-Distill** | DeepSeek | RL-driven reasoning, 78.65% HumanEval Pass@1, fast sprints |
| **Cursor** | Anysphere (IDE agent) | Best AI-native IDE; multi-file refactors, repo-level context, agent mode |
| **Claude Code** | Anthropic (CLI agent) | Terminal-native agentic coding, scriptable, MCP-powered, zero data retention option |
| **GitHub Copilot** | Microsoft / GitHub | IDE inline autocomplete, PR review, widest editor coverage |

---

## 3. Leading Specialist Domain Models

### ⚖️ Legal

| Model | Type | Highlights |
|---|---|---|
| **LegalBERT** | BERT-based | Pre-trained on EU legislation, court cases & contracts; strong at legal NER, classification, and judgment analysis |
| **DISC-LawLLM** | RAG + fine-tuned | Combines fine-tuned LLM with external legal databases for factual legal research, advisory, and statute retrieval |
| **LawGPT / LawGPT-zh** | Open source | Pre-trained on large-scale Chinese legal texts; covers judicial Q&A, case analysis, and bar exam tasks |
| **Llama-LegalBar (fine-tune)** | Fine-tuned SFT | Efficient supervised fine-tuning of Llama on multi-state bar exam data; strong common-law reasoning |

### ∑ Mathematics

| Model | Type | Highlights |
|---|---|---|
| **DeepSeekMath-V2** | Open weights | IMO 2025 gold-level (5/6 problems); 118/120 on Putnam 2024 — verifier-generator dual engine for formal proof reasoning |
| **Llemma (7B / 34B)** | Open source | Continued pre-training on Proof-Pile-2 (math papers, formal proofs, STEM code); strong at theorem proving |
| **InternLM-Math (7B)** | Open source | Verifiable chain-of-thought reasoning; integrates with Lean 4 for formal proof verification |
| **MathCoder (7B / 13B)** | Code + math | Blends code execution with symbolic math — solves problems by generating and running Python alongside reasoning |

### ⚗️ Chemistry & Materials Science

| Model | Type | Highlights |
|---|---|---|
| **ChemCrow** | Tool-augmented | LLM augmented with 17 chemistry tools (RDKit, synthesis planners, databases); handles drug discovery and reaction planning |
| **ChemAgent** | Agentic | Self-updating tool library; excels at multi-step chemical reasoning via structured planning prompts and tool calls |
| **Darwin 1.5** | Materials AI | Two-stage training on natural language + materials science corpus; designed for materials discovery pipelines |
| **MolBERT / ChemBERTa** | Molecular | SMILES-trained encoder models for molecular property prediction, drug–target interaction, and retrosynthesis |

### 🧬 Biomedical & Healthcare

| Model | Type | Highlights |
|---|---|---|
| **BioGPT (355M / 1.5B)** | PubMed-trained | Trained on 15M PubMed abstracts; top performer in biomedical relation extraction, Q&A, and text generation |
| **BioMedLM (2.7B)** | Open source | Outperforms models 10x its size on clinical NLP benchmarks; ideal for EHR summarisation and clinical Q&A |
| **HuatuoGPT (7B / 13B)** | RLHF medical | Doctor–patient dialogue specialist; RLHF-tuned on real physician feedback for safe clinical interaction |
| **ESM-2 (ProteinLM)** | Protein sequences | Meta's protein language model trained on 250M sequences; predicts structure, function, and mutation effects |

### 🌐 Language Translation

| Model | Type | Highlights |
|---|---|---|
| **NLLB-200** | Meta (600M–54B) | No Language Left Behind: 200-language translation model, strong on low-resource languages, open weights |
| **GemmaX2-28 (9B)** | Top-tier MT | Parallel-First Monolingual-Second training; outperforms TowerInstruct and X-ALMA across 28 languages, rivals GPT-4 Turbo on MT |
| **TowerInstruct (7B)** | Instruction-tuned | Fine-tuned on high-quality parallel data for European language pairs; strong post-editing and context-aware MT |
| **Aya Expanse** | Cohere (101 languages) | Multilingual instruction-following model; excels at cross-lingual generation, summarisation, and dialogue in low-resource settings |

### 🔍 Advanced Reasoning

| Model | Type | Highlights |
|---|---|---|
| **DeepSeek-R1 / R1-Distill** | Open weights | RL-trained chain-of-thought reasoning; distilled into 7B–14B packages matching o1-level logic at fraction of the cost |
| **Qwen3 (thinking mode)** | Dual mode | Extended thinking mode enables deep multi-step reasoning; strong on AIME, logic, and planning benchmarks |
| **Phi-4 Mini** | Microsoft (3.8B) | MMLU ~82%; reasoning-dense training data; top reasoning per parameter ratio for edge and mobile inference |
| **AM-Thinking-v1** | Open source | Specialised RL-trained reasoning model; strong competition math and logical puzzle solving; efficient inference |

### 📈 Finance

| Model | Type | Highlights |
|---|---|---|
| **FinGPT** | Open source | Open-source financial LLM fine-tuned on market news, SEC filings, and earnings calls; sentiment & forecasting tasks |
| **BloombergGPT (50B)** | Proprietary | Trained on 363B tokens of financial text; best-in-class for financial NER, sentiment, and headline classification |
| **FinBERT** | BERT-based | Fine-tuned on financial communications; industry standard for earnings call sentiment, risk classification, and compliance |

### 🛡️ Cybersecurity & Other Sciences

| Model | Type | Highlights |
|---|---|---|
| **SecureFalcon** | Security | Fine-tuned Falcon for vulnerability detection, C code analysis, and CWE classification at low compute cost |
| **AstroLLaMA (7B)** | Astronomy | Continued pre-training on 300K arXiv astrophysics abstracts; strong at literature Q&A and hypothesis generation |
| **GeoGPT** | Geoscience | Trained on geological surveys, seismic data, and earth science literature; supports mineral exploration and climate research |

---

## 4. Specialist Models for Materials Science

### 📖 Literature Mining & Text Understanding

| Model | Type | Highlights |
|---|---|---|
| **MatSciBERT** | BERT-based | Trained on peer-reviewed materials science publications; state-of-the-art for NER, relation classification, and abstract classification |
| **LLaMat / LLaMat-Chat** | LLaMA-based | Continued pre-training of LLaMA-2 on 30B tokens from ~4M materials science publications; outperforms larger general LLMs on 42 MatSci tasks |
| **MaterialsBERT** | Property extraction | Trained on 2.4M abstracts; builds ~300K structured property records; powers PolymerScholar database |
| **ChemDFM** | Chemistry + MatSci | Handles synthesis information extraction, document classification, and literature-based reasoning |

### ⚛️ Atomistic Simulation & Interatomic Potentials

| Model | Type | Highlights |
|---|---|---|
| **MatterSim** | Microsoft (Universal MLIP) | Trained on 17M DFT-labeled structures; zero-shot universal interatomic potential across all elements; near-DFT accuracy |
| **MACE-MP-0** | Equivariant GNN | State-of-the-art for periodic systems using equivariant message-passing; physically symmetric force/energy predictions |

### 🔬 Property Prediction

| Model | Type | Highlights |
|---|---|---|
| **GNoME** | DeepMind (GNN discovery) | Discovered 2.2M new stable crystal candidates via GNN ensembles with active-learning DFT validation |
| **AtomGPT** | GPT + atomics | Uses GPT-2 and quantised Mistral to learn atomic structure–property relationships from JARVIS-DFT |
| **LLaMP** | RAG-powered | Grounds LLM reasoning in the Materials Project database to prevent hallucinations in property queries |

### 🧲 Generative Materials Design & Discovery

| Model | Type | Highlights |
|---|---|---|
| **MatterGen** | Microsoft (Diffusion) | Generates stable inorganic crystals across the periodic table; outputs are 2× more novel/stable and 15× closer to energy minima vs. prior models |
| **MatterGPT** | Transformer generative | Autoregressive transformer using SLICES notation for multi-property inverse design; targets both formation energy and band gap simultaneously |
| **CrysVCD** | Valence-constrained diffusion | 85% thermodynamic stability and 68% phonon stability in generated structures; built-in chemical valence constraints |
| **CrystaLLM** | LLM + CIF strings | Treats crystallographic information files as text for autoregressive crystal structure generation |

### 🤖 Agentic & Tool-Augmented Systems

| Model | Type | Highlights |
|---|---|---|
| **ChatMOF** | MOF specialist | LLM agent for metal-organic frameworks: 96.9% search accuracy, 95.7% property prediction, 87.5% structure generation |
| **LLMatDesign** | Self-reflective agent | Iterative design loop: proposes atomic modifications → calls ML property predictors → evaluates → repeats until target met |
| **MatPilot** | Human-in-the-loop | Covers literature search, hypothesis generation, experimental design, and autonomous verification via physical lab robots |

### 🧪 Synthesis Planning & Process Optimisation

| Model | Type | Highlights |
|---|---|---|
| **Molecular Transformer** | Reaction prediction | Sequence-to-sequence reaction translation; state-of-the-art for retrosynthesis and forward reaction prediction |
| **ChemFormer** | BART-based | Handles forward synthesis, retrosynthesis, and reaction condition prediction; generalises to novel reaction classes |
| **Darwin 1.5** | Materials discovery | Two-stage training for autonomous materials discovery pipelines and synthesis route recommendation |
| **AlloyGAN** | Alloy design | LLM text mining + conditional GAN; predicts thermodynamic properties of metallic glasses with <8% error vs. experiment |

### 🌐 Multimodal & Cross-Domain Models

| Model | Type | Highlights |
|---|---|---|
| **nach0** | Text + structure | Cross-modal reasoning over text, molecular structures, and spectral data in a single unified model |
| **MatterChat** | Multimodal chat | Conversational interface reasoning over structural, textual, and spectral data for materials research assistants |
| **Hybrid-LLM-GNN** | GNN + LLM fusion | Up to 25% improvement over GNN-only models in materials property predictions by combining structural precision with LLM contextual understanding |

---

*Compiled March 2026. Models and capabilities evolve rapidly — verify current benchmarks and licensing before production deployment.*
