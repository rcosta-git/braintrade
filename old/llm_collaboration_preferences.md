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
    *   Use `apply_diff` for targeted changes to existing files. See specific guidelines below.
    *   Use `write_to_file` for creating new files or for significant rewrites of existing files. Always provide the *complete* file content.
    *   Confirm file paths before writing or modifying.
    *   **Never** overwrite critical configuration files (e.g., `.env`, potentially `docker-compose.yml`) without explicit user confirmation via `ask_followup_question`.

    ### Specific Guidelines for `apply_diff`
    *   **Verify the `SEARCH` Block Rigorously:**
        *   **Rule:** **Never assume content.** Always use `read_file` to fetch the *exact* lines intended for the `SEARCH` block immediately before constructing the `apply_diff` call. Pay extremely close attention to whitespace (leading/trailing spaces, tabs) and line endings.
        *   **Rule:** Ensure the `:start_line:` and `:end_line:` numbers in the `SEARCH` block precisely match the lines fetched by `read_file`.
    *   **Construct the `REPLACE` Block Carefully:**
        *   **Rule:** **Match initial indentation:** The *first line* of the `REPLACE` block must have the *exact same indentation* as the *first line* of the `SEARCH` block, unless the explicit goal is to change the indentation level of that line itself.
        *   **Rule:** **Maintain relative indentation:** All subsequent lines within the `REPLACE` block must maintain correct indentation *relative* to the first line of the `REPLACE` block, adhering strictly to the project's established style (e.g., 4 spaces, tabs).
        *   **Rule:** **Handle Multi-line Replacements:** When the `REPLACE` block contains multiple lines, ensure every line after the first maintains correct indentation *relative to the first line of the REPLACE block* and adheres to the project's style. Double-check indentation for nested structures within the multi-line replacement.
    *   **Anticipate Contextual Indentation Changes:**
        *   **Rule:** If the `REPLACE` block introduces a new scope (like `if`, `for`, `class`, `def`, `try`, `{ ... }`), ensure all lines *within* that new scope in the `REPLACE` block are correctly indented relative to the line introducing the scope.
        *   **Rule:** If the changes logically require lines *after* the `end_line` of the `SEARCH` block to be indented or un-indented (e.g., wrapping existing code in a new block, removing an enclosing block), these subsequent lines *must* be handled. This might require extending the `SEARCH` block, adding more `SEARCH/REPLACE` blocks in the same call, or using a subsequent call.
        *   **Suggestion:** After applying a diff that alters code structure, consider a follow-up `read_file` on the modified section and its surroundings to visually confirm correct indentation.
    *   **Identify and Respect Project Style:**
        *   **Suggestion:** Before making edits, use `read_file` on existing project files to determine the indentation style (spaces vs. tabs, width). Check for configuration files like `.editorconfig`, `pyproject.toml`, `.prettierrc`, `.eslintrc.js`.
        *   **Rule:** Consistently apply the identified project style in all `REPLACE` blocks.
    *   **Strategic Use of `apply_diff` vs. `write_to_file`:**
        *   **Suggestion:** Prefer `apply_diff` for targeted changes. Use multiple `SEARCH/REPLACE` blocks within a single `apply_diff` call for related changes in close proximity.
        *   **Suggestion:** For unrelated changes in different parts of a file, consider separate `apply_diff` calls.
        *   **Rule:** Only use `write_to_file` as a fallback for `apply_diff` if complex structural changes make diffing impractical or error-prone.
    *   **Post-Change Verification (Optional but Recommended):**
        *   **Suggestion:** If the project has automated linters or formatters, suggest running them via `execute_command` after applying changes to catch/fix indentation and style errors automatically.

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