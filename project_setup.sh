#!/bin/bash
# -------------------------------------------
# Project Setup Script
#
# Usage:
#   bash project_setup.sh
#
# This script will:
# - Create a Python virtual environment (if missing)
# - Initialize a Git repository (if missing)
# - Create .gitignore and .rooignore files
# - Create a .env file with example variables (if missing)
# -------------------------------------------


echo "Starting project setup..."

# 1. Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists. Skipping."
fi

# 2. Initialize Git repository if not already initialized
if [ ! -d ".git" ]; then
    echo "Initializing Git repository..."
    git init
else
    echo "Git repository already initialized. Skipping."
fi

# 3. Create .gitignore file
echo -e "venv/\n__pycache__/\n.env" > .gitignore
echo ".gitignore created."

# 4. Create .rooignore file
echo -e "venv/\n__pycache__/\n.env" > .rooignore
echo ".rooignore created."

# 5. Create .env file with example variables if it doesn't exist
if [ ! -f ".env" ]; then
    cat <<EOL > .env
DATABASE_URL=your_database_url
SECRET_KEY=your_secret_key
DEBUG=True
EOL
    echo ".env file created with example variables."
else
    echo ".env file already exists. Skipping."
fi

# 6. Create docs directory if it doesn't exist
if [ ! -d "docs" ]; then
    echo "Creating docs directory..."
    mkdir docs
else
    echo "docs directory already exists. Skipping."
fi

# 7. Create llm_collaboration_preferences.md if it doesn't exist
if [ ! -f "docs/llm_collaboration_preferences.md" ]; then
    echo "Creating docs/llm_collaboration_preferences.md..."
    cat <<EOL > docs/llm_collaboration_preferences.md
# LLM Collaboration Preferences & Guidelines

**Goal:** To establish clear guidelines and preferences for how the user and the LLM (e.g., Roo) should collaborate effectively on this project, ensuring consistency and efficiency.

---

## General Principles

*   **Iterative Approach:** Follow the defined planning and development processes iteratively.
*   **Clarity & Context:** Provide context for actions and decisions. Explain the "why" behind technical choices or tool usage.
*   **Confirmation:** Wait for user confirmation after each significant action or tool use before proceeding to the next step.

## Planning Phase (Architect Mode)

1.  **Granularity:** Create detailed, step-by-step plans for each distinct activity within a phase before starting implementation for that phase.
2.  **Decision Making:** Actively discuss technical options, outlining pros, cons, risks, and alternatives before finalizing an approach. Use \`ask_followup_question\` for key decision points.
3.  **Documentation:** Maintain comprehensive planning documents in the \`docs/\` folder, keeping them updated as decisions are made.

## Implementation Phase (Code Mode)

4.  **Follow Plans:** Adhere to the detailed activity plans created during the planning phase.
5.  **File Modifications:**
    *   Use \`apply_diff\` for targeted changes to existing files. Ensure the \`SEARCH\` block exactly matches current file content (use \`read_file\` first if unsure).
    *   Use \`write_to_file\` for creating new files or for significant rewrites of existing files. Always provide the *complete* file content.
    *   Confirm file paths before writing or modifying.
    *   **Never** overwrite critical configuration files (e.g., \`.env\`, potentially \`docker-compose.yml\`) without explicit user confirmation via \`ask_followup_question\`.
6.  **Coding Standards:**
    *   Follow Python best practices (PEP 8).
    *   Write clear, readable code.
    *   Add comments for complex logic sections.
    *   Implement basic error handling (e.g., try-except blocks for file I/O, API calls, database operations).
7.  **Testing:** Write unit tests (e.g., using \`pytest\`) for new functions/classes *after* the implemented feature passes a user smoke test. Ensure tests cover main logic and edge cases.
8.  **Tool Usage:** Select the most appropriate tool for each specific task based on tool descriptions.

## Communication

9.  **Style:** Be concise but clear in explanations and justifications.
10. **Questions:** Use \`ask_followup_question\` when clarification or a decision is needed from the user. Provide sensible default suggestions.

## Documentation (During Development)

11. **Update Plans:** Mark completed activities in \`docs/phased_plan.md\` and archive detailed activity plans as per \`docs/development_process.md\`.
12. **Update Project Docs:** Keep \`README.md\`, \`CHANGELOG.md\`, and potentially \`docs/architecture.md\` or \`docs/product_spec.md\` updated with relevant changes resulting from the implementation.

---

*This document can be updated as needed based on evolving project requirements or user preferences.*
EOL
    echo "docs/llm_collaboration_preferences.md created."
else
    echo "docs/llm_collaboration_preferences.md already exists. Skipping."
fi

# 8. Activate virtual environment (only within this script)
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Virtual environment not found. Skipping activation."
fi

# 9. Git add and initial commit
if [ -d ".git" ]; then
    echo "Adding all files to git and making initial commit..."
    git add .
    git commit -m "Initial project setup"
else
    echo "Git repository not found. Skipping git add and commit."
fi

echo "Project setup complete."

echo ""
echo "Note: To activate the virtual environment in your shell, run:"
echo "source venv/bin/activate"