# AI Evaluation & Observability

This document describes the design, responsibilities, and observability architecture for the AI assessment pipeline in the Interview Intelligence Platform.

## Architecture

The AI engine relies on structured generation (enforced via JSON Schema in `Pydantic`) paired with an overarching observability layer that tracks the telemetry of every LLM interaction.

### What the Model Does

The generative AI model is strictly responsible for:
- **Natural Language Understanding**: Parsing the context, nuance, and intent behind a candidate's unstructured text or code submission.
- **Inference & Scoring**: Assigning quantitative scores across established axes (e.g., technical accuracy, conceptual depth, code quality, readability) based on provided rubrics.
- **Feedback Generation**: Drafting actionable recommendations, identifying key strengths, and surfacing weaknesses or "red flags".
- **Dynamic Follow-Ups**: Synthesizing the candidate's previous response to construct targeted follow-up questions that probe specific weaknesses.

### What Deterministic Code Does

Deterministic application code (and the database layer) is strictly responsible for:
- **Telemetry & Observability**: Measuring input/output token counts, latency, retries, and tracking model versions via the `AIRun` schema.
- **Schema Validation**: Enforcing that the AI's output exactly matches the expected data structures before it is accepted into the system.
- **Aggregation**: Synthesizing scores across multiple rounds into a final overarching interview score. (The AI does *not* do math across rounds).
- **Retry Logic**: Safely attempting exponential backoff and retries when the model fails to produce valid JSON or times out.
- **Failure Recovery**: Defaulting to fallback states or surfacing graceful error UI to the user when the model ultimately fails.

### What is Inferred

- **Domain Competence**: The model infers the candidate's skill level (0-100) on specific technical tags (e.g., `react`, `python`, `system_design`) based on the evidence presented in the transcript.
- **Time/Space Complexity**: The model analyzes code submissions to infer algorithmic efficiency.
- **Overall Rating**: During session synthesis, the model infers a holistic rating ("Strong Hire", "Hire", "Leaning Hire", "No Hire") based on the entirety of the session data.

### What is Not Inferred

- **Execution Correctness**: The model's evaluation of "correctness" is a static analysis of logic, not a runtime guarantee. (Actual execution should happen in a deterministic sandbox if applicable).
- **Cross-Session Analytics**: The model only evaluates the current context window. It does not infer longitudinal progress (e.g., "The candidate improved since last time"); this is handled by database-driven analytics.
- **System-level Errors**: The model is not aware of backend latency, token limits, or network failures.

## Evaluation Reliability & Testing

To ensure the reliability of the AI assessment pipeline, we utilize a suite of internal evaluation tests against a curated set of fixtures.

### Fixtures
Our fixture set contains representative inputs covering a wide spectrum of candidate responses:
- **Technical & Behavioral Answers**: Spanning strong, weak, and ambiguous responses to verify the model can confidently discern quality.
- **Coding Submissions**: Including optimal, suboptimal, and broken code.

### Reliability Tests
The evaluation pipeline is tested deterministically to guarantee safety:
- **Schema Validity**: Verifying that responses perfectly serialize into Pydantic models.
- **Field Completeness**: Ensuring that crucial evaluation metrics (scores, strengths, recommendations) are consistently populated.
- **Graceful Failure**: Simulating model timeouts or malformed outputs to verify that the application recovers via the `RuntimeError` boundary without corrupting session state.
- **Follow-up Generation Behavior**: Validating that the engine correctly synthesizes previous weaknesses into context-aware follow-ups rather than generic prompts.
- **Observability Telemetry**: Ensuring `latency`, `input_tokens`, `output_tokens`, `retry_count`, and `schema_validation` are tracked correctly for every event.

> Note: Empirical accuracy percentages of the model's evaluations against human baselines are targeted as a future measurement and are not yet fabricated or stated here.
