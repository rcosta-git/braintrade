# LLM Collaboration Preferences & Guidelines

**Goal:** To establish clear guidelines and preferences for how the user and the LLM (e.g., Roo) should collaborate effectively on this project, ensuring consistency and efficiency.

---

## General Principles

*   **Iterative Approach:** Follow the defined planning and development processes iteratively.
*   **Clarity & Context:** Provide context for actions and decisions. Explain the "why" behind technical choices or tool usage.
*   **Confirmation:** Wait for user confirmation after each significant action or tool use before proceeding to the next step.

## Planning Phase (Architect Mode)

1.  **Granularity:** Create detailed, step-by-step plans for each distinct activity within a phase before starting implementation for that phase.
2.  **Decision Making:** Actively discuss technical options, outlining pros, cons, risks, and alternatives before finalizing an approach. Use `ask_followup_question` for key decision points.
3.  **Documentation:** Maintain comprehensive planning documents in the `docs/` folder, keeping them updated as decisions are made.

## Implementation Phase (Code Mode)

4.  **Follow Plans:** Adhere to the detailed activity plans created during the planning phase.
5.  **File Modifications:**
    *   Use `apply_diff` for targeted changes to existing files. Ensure the `SEARCH` block exactly matches current file content (use `read_file` first if unsure).
    *   Use `write_to_file` for creating new files or for significant rewrites of existing files. Always provide the *complete* file content.
    *   Confirm file paths before writing or modifying.
    *   **Never** overwrite critical configuration files (e.g., `.env`, potentially `docker-compose.yml`) without explicit user confirmation via `ask_followup_question`.
6.  **Coding Standards:**
    *   Follow Python best practices (PEP 8).
    *   Write clear, readable code.
    *   Add comments for complex logic sections.
    *   Implement basic error handling (e.g., try-except blocks for file I/O, API calls, database operations).
7.  **Testing:** Write unit tests (e.g., using `pytest`) for new functions/classes *after* the implemented feature passes a user smoke test. Ensure tests cover main logic and edge cases.
8.  **Tool Usage:** Select the most appropriate tool for each specific task based on tool descriptions.

## Communication

9.  **Style:** Be concise but clear in explanations and justifications.
10. **Questions:** Use `ask_followup_question` when clarification or a decision is needed from the user. Provide sensible default suggestions.

## Documentation (During Development)

11. **Update Plans:** Mark completed activities in `docs/phased_plan.md` and archive detailed activity plans as per `docs/development_process.md`.
12. **Update Project Docs:** Keep `README.md`, `CHANGELOG.md`, and potentially `docs/architecture.md` or `docs/product_spec.md` updated with relevant changes resulting from the implementation.

---

*This document can be updated as needed based on evolving project requirements or user preferences.*