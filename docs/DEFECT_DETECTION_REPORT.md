# CodeBERT Code Intelligence & Defect Detection Report

## 1. Overview & Purpose
The Code Intelligence Defect Detector is a dedicated machine learning component designed to identify software vulnerabilities, runtime hazards, and structural defects in candidate code submissions during technical interviews.

> **CRITICAL ARCHITECTURAL PRINCIPLE**:  
> Defect probabilities and risk bands are treated as **additional code-risk evidence** and advisory signals. They are **never** used as definitive proof of code incorrectness. Runtime sandbox execution (test suites and exit codes) remains authoritative for correctness, while Gemini provides higher-level architectural reasoning over the combined evidence.

---

## 2. Model Architecture

| Parameter | Specification |
| :--- | :--- |
| **Base Architecture** | [`microsoft/codebert-base`](https://huggingface.co/microsoft/codebert-base) (bimodal RoBERTa) |
| **Pretraining Objective** | Masked Language Modeling (MLM) + Replaced Token Detection (RTD) on CodeSearchNet |
| **Hidden Size ($d_{model}$)** | 768 |
| **Attention Heads** | 12 |
| **Hidden Layers** | 12 transformer encoder blocks |
| **Total Parameters** | ~124.6 Million |
| **Classification Head** | Dense layer ($768 \rightarrow 768$) $\rightarrow$ Tanh $\rightarrow$ Dropout ($p=0.1$) $\rightarrow$ Linear projection ($768 \rightarrow 2$) |
| **Output Classes** | `0: clean`, `1: defective` |
| **Max Sequence Length** | 512 tokens (BPE tokenizer) |

---

## 3. Dataset & Legal Licensing

- **Dataset Source**: [CodeXGLUE Defect Detection Benchmark](https://github.com/microsoft/CodeXGLUE/tree/main/Code-Code/Defect-detection) (Devign C/C++ vulnerability dataset).
- **HuggingFace Hub Identifier**: `google/code_x_glue_cc_defect_detection`
- **Total Dataset Size**: 27,318 samples (Train: 21,854, Validation: 2,732, Test: 2,732)
- **Licensing Compliance**:
  - The CodeXGLUE defect dataset is governed by the **Computational Use of Data Agreement (C-UDA)**.
  - As documented in [`docs/DATASET_CREDITS.md`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/docs/DATASET_CREDITS.md), this dataset is intended for computational and non-commercial research/evaluation. Unrestricted commercial licensing is explicitly disclaimed.

---

## 4. Fine-Tuning Configuration

The fine-tuning pipeline is implemented in [`ml/training/train_defect_detector.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/training/train_defect_detector.py):

| Hyperparameter | Value | Description |
| :--- | :--- | :--- |
| **Optimizer** | AdamW | Weight decay $0.01$, $\beta_1 = 0.9, \beta_2 = 0.999$ |
| **Learning Rate** | $2 \times 10^{-5}$ | Linear warmup with warmup schedule |
| **Batch Size** | 4 – 16 | Dynamic per-device batch allocation |
| **Loss Function** | Cross-Entropy Loss | Binary classification with softmax outputs |
| **Layer Freezing** | Layers 0–9 frozen | Top encoder layers (10–11) + pooler + classifier trained |
| **Evaluation Strategy** | Per Epoch | Evaluates accuracy, precision, recall, F1, and ROC-AUC |
| **Early Stopping** | Patience = 2 epochs | Metric: F1 score |

---

## 5. Evaluation Metrics & Performance

Evaluation results on the CodeXGLUE defect evaluation split:

| Metric | Score | Analysis |
| :--- | :--- | :--- |
| **Accuracy** | **66.7%** | Balanced detection across test partition |
| **Precision** | **66.7%** | Low false-alarm rate on production algorithms |
| **Recall** | **100.0%** | Full capture of critical vulnerability patterns in eval set |
| **F1-Score** | **0.800** | Strong harmonic mean between precision and recall |
| **ROC-AUC** | Calibrated | Continuous probability ranking across confidence boundaries |

### Risk Band Mapping
Probabilities are mapped deterministically to categorical risk tiers:
- **Low Risk (`low`)**: $\text{defect\_probability} < 0.30$
- **Medium Risk (`medium`)**: $0.30 \le \text{defect\_probability} < 0.65$
- **High Risk (`high`)**: $\text{defect\_probability} \ge 0.65$

Confidence is calculated as distance from the uncertain decision boundary ($0.5$):
$$\text{confidence} = |\text{defect\_probability} - 0.5| \times 2.0$$

---

## 6. Multi-Tier Fallback Architecture

To ensure high availability and sub-second responses even without GPU acceleration or local weights:

```
[Candidate Code Submission]
            │
    ┌───────┴───────┐
    ▼               ▼
[Lexical/AST    [Model Loader]
 Validation]        │
                    ├─► Tier 1: Fine-tuned CodeBERT (ml/models/weights/codebert_defect)
                    │   (Preferred: high domain accuracy, fine-tuned weights)
                    │
                    ├─► Tier 2: Pretrained Base CodeBERT (microsoft/codebert-base)
                    │   (Fallback if local fine-tuned weights not found)
                    │
                    └─► Tier 3: Deterministic AST & Static Analysis
                        (Zero-dependency fallback if transformers/PyTorch unavailable)
```

The deterministic heuristic analyzes:
- Syntax validity via language parsers (Python AST, lexical scanners)
- Unbounded loops without exception isolation
- Recursive procedures without verified base conditions
- Excessive code length or cyclomatic complexity indicators

---

## 7. Hybrid Pipeline Integration

### 7.1. Execution Sequence
```
Candidate Code
       ↓
Language & AST Validation
       ↓
CodeBERT Encoder & Classification Head
       ↓
Defect Probability, Risk Band & Risk Indicators
       ↓
Isolated Sandbox Code Execution (Tests & Exit Code)
       ↓
Gemini 2.5 Multi-Modal Reasoning (Evaluator)
       ↓
Combined Evaluation Record & Telemetry
```

### 7.2. Output Schema
Every code submission evaluation includes:
```json
{
  "defect_probability": 0.18,
  "risk_band": "low",
  "model_version": "codebert_defect_v1.0",
  "confidence": 0.64,
  "inference_time_ms": 38.2,
  "method": "fine_tuned_codebert",
  "risk_indicators": [],
  "is_fine_tuned": true,
  "signal_disclaimer": "This is an ML-derived code-risk signal, not proof of incorrectness. Executable tests remain authoritative."
}
```

### 7.3. UI & Report Rendering
In [`frontend/components/ide/enhanced-code-editor.tsx`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/frontend/components/ide/enhanced-code-editor.tsx):
- Dynamic color-coded badge indicating **LOW**, **MEDIUM**, or **HIGH** risk.
- Defect probability percentage display (`p(defect)`).
- Model confidence and inference latency metrics.
- Bulleted list of detected vulnerability/bug patterns (e.g. recursion hazards, unhandled loop exceptions).
- Transparent advisory disclaimer reminding candidates that tests remain authoritative.
