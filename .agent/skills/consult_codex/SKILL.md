---
name: consult_codex
description: Consults the external 'codex' CLI tool for feedback by sending the current context. Triggered by "给我提意见".
---

# Consult Codex Skill

This skill allows you to send the current context to the `codex` CLI tool to get feedback or advice.

## When to use
- When the user says "给我提意见" (Give me feedback).
- When you want a second opinion or high-level architectural advice.

## Instructions

1.  **Analyze Request Type**:
    Determine if the user's request involves **writing code/implementation details** or **general/architectural advice**.
    - If **Coding/Implementation**: Use model `gpt-5.2-codex`.
    - If **General/Architecture** (default): Use model `gpt-5.2`.

2.  **Synthesize Context**:
    Create a concise summary of the current situation. Include:
    - The task at hand.
    - Relevant decisions made.
    - Specific questions.

3.  **Formulate the Prompt**:
    Combine the context into a single string.
    *Draft*: "Context: [Summary]. Question: [Your Question]."

4.  **Execute Command**:
    Use the `codex exec` subcommand to run non-interactively. This ensures the command exits and returns output.
    Add `--skip-git-repo-check` to work even if the repo isn't initialized yet.

    ```bash
    codex exec --skip-git-repo-check -m <SELECTED_MODEL> "YOUR_PROMPT_HERE"
    ```

    *Example*:
    - For architectural advice:
      `codex exec --skip-git-repo-check -m gpt-5.2 "Review my project proposal..."`
    - For coding help:
      `codex exec --skip-git-repo-check -m gpt-5.2-codex "Write a Python script to..."`

5.  **Retrieve and Analyze**:
    - Wait for the command to completion (Status: DONE).
    - Read the output.
    - **Action**: Reflect on the feedback and present it to the user.
