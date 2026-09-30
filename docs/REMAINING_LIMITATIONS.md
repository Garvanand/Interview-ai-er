# Remaining Limitations and Unbacked Features

After auditing and cleaning up the majority of the mock data and demo behaviors in the frontend (such as fake hardcoded sessions, scores, and Math.random() usage), there remain several areas where the application advertises capabilities that are not supported by the underlying backend architecture.

For now, these have been explicitly documented or disabled in the UI to prevent misleading users, rather than reverting to hardcoded responses.

### 1. Actual Code Execution
- **Current State:** The backend currently does not provide any code execution sandboxes or runners. It only provides a `/submit_code` endpoint which uses Gemini to perform a static evaluation of the code.
- **Frontend Mitigation:** The "Run Code" button in the IDE now explicitly informs the user that code execution is unavailable, prompting them to use the "Submit for Evaluation" button instead.

### 2. Practice Mode Evaluation
- **Current State:** The backend has a `/practice/coding` route to generate random practice questions using Gemini. However, there is no corresponding endpoint to evaluate the user's answers for practice mode (since `/submit_answer` requires an active DB-backed interview session).
- **Frontend Mitigation:** Users can generate practice questions, but upon submitting an answer, the UI explicitly states that "Evaluation is currently unavailable in practice mode" rather than assigning a random pass/fail grade.

### 3. Interactive AI Interview Chat
- **Current State:** The `interview-chat.tsx` component exposes features for requesting hints, clarifications, and general conversational interactions with the AI. The backend does not implement these conversational states or endpoints.
- **Frontend Mitigation:** The chat actions (Hints, Clarifications, General) now return explicit messages stating that interactive chat is currently unintegrated or unavailable.

### 4. Advanced Security and Anti-Cheating
- **Current State:** While the backend has a `/security/check` endpoint that passes JSON data to Gemini for analysis, the actual client-side capabilities for tracking webcam, microphone, and browser anomalies are entirely structural/UI facades. The backend's `/security/report` endpoint was also missing/broken and has been disabled with a 501.
- **Frontend Mitigation:** Retained as structural code for future implementation (Phase 8), but currently operates on minimal/null data.

### 5. Detailed Analytics Breakdown
- **Current State:** The backend tracks `interview_type` (e.g., "Technical", "Behavioral"). However, the frontend Analytics page groups data by more granular tags (e.g., "Algorithms", "System Design") which are not strictly emitted by the backend session endpoints.
- **Frontend Mitigation:** The Analytics page currently maps the backend's generic `interview_type` into the category charts dynamically. True granular skill tracking will require Phase 7 (Skill Modeling Engine) implementation.

These limitations must be resolved by implementing their respective systems in the upcoming rebuilt phases.
