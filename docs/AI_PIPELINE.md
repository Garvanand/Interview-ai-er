# AI Pipeline Architecture

The AI layer has been completely rebuilt as a reliable assessment engine with domain separation, typed schemas, and strict validation. 

## 1. Domain Service Layer
The AI pipeline is encapsulated within the `app.services.ai` package, eliminating ad-hoc API calls scattered across the application. 

### Key Components:
- **`schemas.py`**: Defines strict Pydantic models for all expected AI outputs (`AnswerEvaluation`, `CodeEvaluation`, `Question`, `SkillExtraction`, `SessionSynthesis`).
- **`engine.py` (`AssessmentEngine`)**: The central orchestrator that applies context, telemetry, and error handling for all generation capabilities.
- **`providers/base.py` (`AIProvider`)**: An abstract interface allowing swapping of LLM models without rewriting the engine.
- **`providers/gemini.py` (`GeminiProvider`)**: The implementation utilizing the new official `google-genai` SDK and the `response_schema` config to ensure strict adherence to Pydantic models.

## 2. Separation of Concerns
The engine strictly separates:
- **Question Generation**: Emits `Question` schema with explicit difficulty, topic, and rubric data.
- **Answer Evaluation**: Parses text submissions into an `AnswerEvaluation` containing `overall_score`, strengths, weaknesses, and a suggested follow-up.
- **Code Evaluation**: Analyzes complexity, code quality, testability, and edge cases into a `CodeEvaluation` schema.
- **Follow-Up Generation**: Generates new questions specifically tailored to weaknesses identified in the previous `AnswerEvaluation`.
- **Skill Extraction & Synthesis**: Reads full session transcripts to extract candidate skill levels (`SkillExtraction`) and generate a final verdict (`SessionSynthesis`).

## 3. Structured Output & Validation
Instead of manually slicing markdown or using regex to parse JSON, the pipeline uses Gemini's native `response_schema` parameter. 
When generating content, the `GeminiProvider` forces the model to return data matching the Pydantic schema structure. The raw JSON is then directly validated via `schema.model_validate_json()`, ensuring data integrity *before* it enters the database.

## 4. Telemetry and Error Handling
Every AI call is wrapped with telemetry, attaching metadata to the output:
- **Latency**: Tracks how long the generation took (`latency_seconds`).
- **Status & Errors**: Records success/failure states.
- **Traceability**: Notes the exact provider and model version used (e.g. `gemini-2.5-flash`).

Crucially, **the engine never silently invents a score**. If the model fails or times out after retries, the engine explicitly raises an error (`RuntimeError("AI Generation Failed")`), causing the API layer to return a clear 500 error rather than faking an evaluation. 

## 5. Configuration
Dependencies include `pydantic` and `google-genai`. Configuration and keys are managed via the standard `.env` file through `GEMINI_API_KEY`.
