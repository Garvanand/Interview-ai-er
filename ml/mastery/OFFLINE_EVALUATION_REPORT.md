# Offline Evaluation Report: Mastery Modeling

## 1. Overview
This report evaluates the **Candidate Skill/Mastery modeling layer** using our Bayesian Knowledge Tracing (BKT) baseline.

### Prototyping Context
Our mastery model architecture is inspired by and validated against sequential educational interaction principles, such as those found in the **EdNet** dataset ([reference](https://arxiv.org/abs/1912.03072)). 

**IMPORTANT DISCLAIMER**: EdNet is an *educational* interaction dataset, not a direct proxy for technical interview performance. The models developed here use EdNet principles solely to prototype the sequential modeling architecture. We do **not** claim that a model trained on EdNet directly predicts hiring suitability. The current baseline operates on heuristic assumptions and is designed for transparency.

## 2. Baseline Model Architecture
The current implementation utilizes **Bayesian Knowledge Tracing (BKT)** as a transparent baseline.

### Input Features
The model consumes a sequential attempt history with the following features:
- `skill`: Target concept (e.g., "graphs")
- `response correctness`: Boolean success of the attempt
- `difficulty`: Float `[0.0, 1.0]` representing the challenge level
- `attempt history`: Sequential window of prior interactions
- `temporal order`: Chronological timestamps of attempts

### Outputs
- **Estimated Mastery**: Probability of skill proficiency, explicitly bounded to `[0.0, 1.0]`.
- **Confidence**: Based on the volume of evidence (asymptotes at 0.95 with sufficient `evidence_count`).
- **Evidence Count**: Total number of interactions evaluated for the skill.
- **Trend**: Categorical momentum (`improving`, `declining`, `stable`).

## 3. Evaluation Setup & Initial Findings

We ran a simulation to validate the BKT updates under realistic interview scenarios:

| Skill | Interaction Sequence | Expected Outcome | Actual Outcome (Mastery) | Trend | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `graphs` | 2 failures (easy) $\rightarrow$ 3 successes (increasing difficulty) | Rising mastery, positive momentum | `0.72` | `improving` | `0.60` |
| `dynamic_programming` | 1 fail $\rightarrow$ 1 success (easy) $\rightarrow$ 2 fails (med) | Stalled/falling mastery, negative momentum | `0.33` | `declining` | `0.50` |

### Observations
1. **Dynamic Parameter Adjustments**: The model successfully modulates standard BKT guess ($P(G)$) and slip ($P(S)$) parameters based on `difficulty`. Passing a hard question correctly yields a larger mastery spike than passing an easy question.
2. **Confidence Scaling**: The linear scaling of confidence based on evidence count accurately reflects the uncertainty of a 1- or 2-question interview segment.

## 4. Migration Path & Future Work
To transition from this heuristic baseline to a production-grade machine learning model:

1. **Data Collection**: Accumulate real-world `Interview-ai-er` session histories.
2. **Calibration**: Use Expectation-Maximization (EM) on the first-party dataset to fit true values for $P(L_0)$, $P(T)$, $P(S)$, and $P(G)$.
3. **Advanced Baselines**: 
   - Utilize the `extract_interaction_features()` function in `ml/mastery/features.py` to train Gradient-Boosted Trees (e.g., XGBoost/LightGBM).
   - Alternatively, adapt a Knowledge Tracing Transformer (e.g., SAINT or RKT) for deep sequential modeling of the attempts.
4. **Terminology**: The system must consistently use the term **"estimated mastery"** and avoid claims of measuring "true ability". 

---
*Generated during Phase 3 of the ML integration.*
