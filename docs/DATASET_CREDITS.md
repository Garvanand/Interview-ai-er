# Dataset & Foundation Model Credits

This document provides formal attribution, citations, licenses, and usage descriptions for all open-source datasets and foundational pre-trained models integrated into the **Interview Intelligence Platform (`Interview-ai-er`)**.

---

## 1. Primary Datasets

### 1.1. TACO (Topics in Algorithmic Code and Optimization)
- **Source**: Beijing Academy of Artificial Intelligence (BAAI)
- **Hugging Face**: [https://huggingface.co/datasets/BAAI/TACO](https://huggingface.co/datasets/BAAI/TACO)
- **Paper**: *TACO: Topics in Algorithmic Code and Optimization Dataset* (Li et al., 2023)
- **License**: Apache 2.0 / MIT
- **Description**: 25,443 coding problems gathered from programming competitions (Codeforces, LeetCode, HackerRank, etc.) labeled with difficulty rating levels (800 to 3500) and algorithmic topics.
- **Role in Platform**: Primary training corpus for:
  - Question Difficulty Prediction
  - Question Skill / Topic Multi-Label Classification
- **Loader Module**: [`ml/datasets/taco_loader.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/datasets/taco_loader.py)

---

### 1.2. APPS (Automated Programming Progress Standard)
- **Source**: UC Berkeley & Hugging Face CodeParrot
- **Hugging Face**: [https://huggingface.co/datasets/codeparrot/apps](https://huggingface.co/datasets/codeparrot/apps)
- **Paper**: *Measuring Coding Challenge Competence With APPS* (Hendrycks et al., NeurIPS 2021)
- **License**: MIT License
- **Description**: 10,000 algorithmic problems categorized into `introductory`, `interview`, and `competition` difficulty with over 130,000 Python reference solutions and test cases.
- **Role in Platform**:
  - Benchmark calibration for interview difficulty boundaries
  - Canonical reference code for semantic answer similarity comparisons
- **Loader Module**: [`ml/datasets/apps_loader.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/datasets/apps_loader.py)

---

### 1.3. CodeXGLUE Defect Detection Benchmark
- **Source**: Microsoft Research
- **Repository**: [https://github.com/microsoft/CodeXGLUE/tree/main/Code-Code/Defect-detection](https://github.com/microsoft/CodeXGLUE/tree/main/Code-Code/Defect-detection)
- **Paper**: *CodeXGLUE: A Machine Learning Benchmark for Code Understanding and Generation* (Lu et al., 2021)
- **Dataset Foundation**: Devign vulnerability and defect detection corpus (Zhou et al., 2019)
- **License**: **Computational Use of Data Agreement (C-UDA)**
- **Description**: 27,318 source code functions labeled for the presence of software defects and security vulnerabilities.
- **Role in Platform**: Training and fine-tuning target for CodeBERT defect risk scoring.
- **Fine-tuned Model Version**: `codebert_defect_v1.0`
- **Fine-tuned Model Artifact**: [`ml/models/weights/codebert_defect/`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/models/weights/codebert_defect)
- **Training Pipeline**: [`ml/training/train_defect_detector.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/training/train_defect_detector.py)
- **Loader Module**: [`ml/datasets/codexglue_loader.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/datasets/codexglue_loader.py)

> **⚠️ LICENSING WARNING (C-UDA)**
>
> The CodeXGLUE Defect Detection dataset is released under the **Computational Use of Data Agreement (C-UDA)**.
> This license permits use for **computational/non-commercial research purposes only**.
> We do **NOT** claim unrestricted commercial licensing over this dataset or any models trained on it.
> Any deployment of the fine-tuned defect detection model in a commercial setting must comply with C-UDA terms.
> See: https://github.com/microsoft/Computational-Use-of-Data-Agreement

---

### 1.4. EdNet (Educational Data Network)
- **Source**: Riiid! AI Research & mgor
- **Hugging Face**: [https://huggingface.co/datasets/mgor/EDNet](https://huggingface.co/datasets/mgor/EDNet)
- **Paper**: *EdNet: A Large-scale Hierarchical Dataset in Education* (Choi et al., 2020)
- **License**: CC BY 4.0
- **Description**: A multi-level hierarchical dataset of 131,441,538 student learning interactions collected from active digital tutoring sessions.
- **Role in Platform**: Prior distributions and response function calibration for:
  - Candidate Skill / Mastery Modeling (Two-Parameter Logistic IRT)
  - Bayesian Knowledge Tracing (BKT) transition parameters
- **Loader Module**: [`ml/datasets/ednet_loader.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/datasets/ednet_loader.py)

---

## 2. Pretrained Foundational Models

### 2.1. DeBERTa-v3 NLI Cross-Encoder
- **Identifier**: `cross-encoder/nli-deberta-v3-base`
- **Hugging Face**: [https://huggingface.co/cross-encoder/nli-deberta-v3-base](https://huggingface.co/cross-encoder/nli-deberta-v3-base)
- **Authors**: Nils Reimers (UKP Lab) & He et al. (Microsoft Research)
- **License**: Apache 2.0
- **Description**: Cross-encoder transformer trained on SNLI and Multi-Genre NLI (MNLI) benchmarks.
- **Role in Platform**: Zero-shot concept coverage evaluation on candidate technical responses.
- **Module**: [`ml/models/concept_coverage.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/models/concept_coverage.py)

---

### 2.2. all-MiniLM-L6-v2
- **Identifier**: `sentence-transformers/all-MiniLM-L6-v2`
- **Hugging Face**: [https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- **Authors**: Sentence-Transformers / UKP Lab (Reimers and Gurevych, 2019)
- **License**: Apache 2.0
- **Description**: 22.7M parameter transformer mapping sentences into a 384-dimensional dense vector space tuned for semantic search.
- **Role in Platform**: Semantic similarity comparisons and dense representation inputs for question classifiers.
- **Module**: [`ml/features/text_embeddings.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/features/text_embeddings.py)

---

### 2.3. CodeBERT
- **Identifier**: `microsoft/codebert-base`
- **Hugging Face**: [https://huggingface.co/microsoft/codebert-base](https://huggingface.co/microsoft/codebert-base)
- **Authors**: Feng et al. (Microsoft Research Asia)
- **License**: MIT License
- **Description**: Bimodal pre-trained model for natural language and programming languages (Python, Java, JavaScript, etc.).
- **Role in Platform**: Base encoder for fine-tuned defect and vulnerability detection.
- **Module**: [`ml/models/defect_detector.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/models/defect_detector.py)

---

### 2.4. OpenAI Whisper
- **Identifier**: `openai/whisper-base.en`
- **Hugging Face**: [https://huggingface.co/openai/whisper-base.en](https://huggingface.co/openai/whisper-base.en)
- **Authors**: Radford et al. (OpenAI, 2022)
- **License**: MIT License
- **Description**: Multi-task sequence-to-sequence model trained on 680,000 hours of multilingual speech audio.
- **Role in Platform**: Speech-to-text audio transcription for voice interview answering.
- **Module**: [`ml/models/speech_to_text.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/models/speech_to_text.py)
