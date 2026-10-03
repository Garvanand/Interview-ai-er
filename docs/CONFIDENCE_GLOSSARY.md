# Confidence & Uncertainty Glossary

> **Purpose**: Define and distinguish three concepts that are easy to conflate — *prediction probability*, *confidence*, and *candidate skill estimate*. Everyone working on Interview-ai-er's ML pipeline should reference this glossary to avoid presenting false precision.

---

## 1. Prediction Probability

| Attribute | Value |
|---|---|
| **What it is** | The raw numeric output of a softmax or sigmoid layer in a neural network. |
| **Mathematical form** | `P(class_i | input) = exp(z_i) / Σ exp(z_j)` where `z` are pre-softmax logits. |
| **Produced by** | DeBERTa NLI, CodeBERT, transformer difficulty classifiers, MiniLM similarity scores. |
| **Common misconception** | ❌ "A softmax output of 0.92 means the model is correct 92% of the time." |
| **Reality** | Modern neural networks are **systematically overconfident**. A softmax output of 0.92 on an uncalibrated model might correspond to only 75% actual accuracy. The gap between predicted probability and observed accuracy is measured by the *Expected Calibration Error (ECE)*. |
| **How to interpret** | Use as a **relative ranking** — higher values indicate the model is more decisive. Do NOT present to users as calibrated certainty without post-hoc calibration. |

### Example

```
DeBERTa NLI output for a concept coverage check:
  entailment:     0.87   ← prediction probability (NOT calibrated confidence)
  contradiction:  0.03
  neutral:        0.10

The model strongly favours "entailment", but whether 0.87 really
means 87% accuracy depends on calibration quality.
```

---

## 2. Confidence

| Attribute | Value |
|---|---|
| **What it is** | A **calibrated** measure of how certain the system is in a prediction. |
| **Key property** | Among all predictions where the system reports 80% confidence, approximately 80% should actually be correct. |
| **How it's obtained** | Post-hoc calibration techniques: temperature scaling, Platt scaling, isotonic regression, or histogram binning — applied to held-out validation data. |
| **Produced by** | Only models that have undergone post-hoc calibration produce true *confidence*. All others produce *model scores* or *heuristic confidence*. |

### Confidence Types in Our Pipeline

| Type | Meaning | Models |
|---|---|---|
| **Calibrated probability** | Post-hoc calibrated via temperature/Platt scaling. The number IS a probability. | *(Currently none — upgrade path documented per model.)* |
| **Model score** | Raw softmax/sigmoid output, NOT calibrated. Higher = more decisive, but the numeric value is NOT a probability. | `question-difficulty-v1`, `question-skill-v1`, `answer-nli-v1`, `code-risk-v1` |
| **Heuristic confidence** | A synthetic score from a rule-based system (keyword matching, Jaccard overlap). Indicates relative signal strength but has no probabilistic interpretation. | Deterministic fallback tiers for all models. |
| **Unavailable** | No meaningful confidence signal. The output is a point estimate with no uncertainty quantification. | `mastery-v1` (theta is a latent ability, not a confidence). |

### Production Confidence Bands

Instead of showing numeric scores, the production UI uses three bands:

| Band | Label | When to use |
|---|---|---|
| 🟢 **High** | "High confidence" | Calibrated prob ≥ 0.75, or model score ≥ 0.85 |
| 🟡 **Moderate** | "Moderate confidence" | Calibrated prob ∈ [0.45, 0.75), or model score ∈ [0.65, 0.85) |
| 🔴 **Insufficient** | "Insufficient evidence" | Below moderate thresholds, or confidence type is unavailable |

> [!IMPORTANT]
> The thresholds are **intentionally asymmetric** — uncalibrated model scores
> require a HIGHER numeric value to reach "High confidence" because neural
> networks are overconfident. A model score of 0.80 corresponds to
> "Moderate confidence", not "High confidence".

---

## 3. Candidate Skill Estimate (Theta)

| Attribute | Value |
|---|---|
| **What it is** | A latent ability parameter estimated by the 2PL Item Response Theory (IRT) model. |
| **Mathematical form** | `θ ∈ [-3.0, +3.0]` on the standard IRT scale, mapped to `[0, 100]` as proficiency. |
| **Produced by** | `mastery-v1` (`ItemResponseTheoryMasteryModel`). |
| **Key distinction** | θ is **NOT** a probability or a confidence. It is a **point estimate** of the candidate's latent ability, analogous to an SAT score — not a measure of certainty. |
| **Uncertainty measure** | The appropriate uncertainty measure is the **Standard Error of Measurement (SEM)**, not confidence. SEM decreases as more items are administered. |

### Example

```
After 5 interview questions:
  θ = 0.84     → proficiency = 64.0 / 100
  SEM = 0.45   → "We know the candidate's ability to within ±0.9 on the theta scale"

After 15 interview questions:
  θ = 1.12     → proficiency = 68.7 / 100
  SEM = 0.22   → "Much tighter estimate — more data has narrowed uncertainty"
```

### IRT Response Probability vs. Confidence

The IRT model also produces `P(correct | θ, b, a)` — the probability that a
candidate with ability θ answers a question with difficulty b correctly. This IS
a calibrated probability under the model assumptions, but it measures **item
response likelihood**, not **prediction confidence**:

```
P(Y = 1 | θ) = 1 / (1 + exp(-a * (θ - b)))

This tells you: "A candidate at this ability level has a 72% chance of
answering this difficulty-level question correctly."

It does NOT tell you: "We are 72% confident in our ability estimate."
```

---

## Summary Comparison

| Concept | Numeric range | Calibrated? | What it means | Example |
|---|---|---|---|---|
| **Prediction probability** | [0, 1] | ❌ No | Model's raw softmax output | DeBERTa says 0.87 for entailment |
| **Confidence** | [0, 1] | ✅ Yes (or typed) | Calibrated certainty in prediction | After temp scaling: 0.74 → "Moderate confidence" |
| **Skill estimate (θ)** | [-3, +3] | N/A | Latent ability on psychometric scale | θ = 1.2 → proficiency = 70.0 |

---

## For Developers

When adding a new model or modifying inference output:

1. **Never** call raw softmax output "confidence" without documenting the confidence type.
2. **Always** attach `confidence_metadata` to every inference using `get_confidence_metadata()`.
3. **Always** include `confidence_band` ("High confidence" / "Moderate confidence" / "Insufficient evidence") in any user-facing output.
4. If you have validation data (≥100 samples), **run temperature scaling** and record the learned T and post-calibration ECE.
5. For IRT theta estimates, report **SEM** instead of confidence.

---

## References

- Guo et al., "On Calibration of Modern Neural Networks" (ICML 2017)
- Niculescu-Mizil & Caruana, "Predicting Good Probabilities with Supervised Learning" (ICML 2005)
- Baker & Kim, "Item Response Theory: Parameter Estimation Techniques" (2004)
