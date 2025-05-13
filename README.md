# Klyp-CLI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- Optional: Add other badges like build status, version, etc. if you set them up -->

**Klyp-CLI** is your personal assistant for packaging project files and instructions into perfectly formatted context for Large Language Models (LLMs). Stop the tedious copy-pasting and let Klyp streamline your AI interactions!

## Why Klyp-CLI?

Tired of manually juggling code snippets, project overviews, and specific instructions every time you want to ask an LLM for help? Preparing comprehensive context for models like Gemini, Claude, or GPT can be a significant time sink and prone to errors.

Klyp-CLI is designed to:

*   🚀 **Save You Time & Effort:** Define your context needs once, then recall them instantly. No more hunting for files or repeatedly typing out system messages.
*   📋 **Eliminate Manual Copy-Pasting:** Assemble content from multiple files and instructions into a single block, copied directly to your clipboard with one command.
*   🎯 **Ensure Consistent & Complete Context:** Provide LLMs with a well-structured overview of relevant files and their content, plus any preparatory "context files" (like project descriptions or specific instructions) and concluding "prompt files" (for specific questions or tasks).
*   ✨ **Simplify LLM Prompting:** Focus on your prompt, not the mechanics of gathering information.

## Key Features

*   📁 **Scoped File Management:** Group related project files into logical "scopes" for different tasks or contexts.
*   📄 **Context File Integration:** Associate each scope with an optional "context file" (e.g., `project_overview.md`, `system_prompt.txt`) that gets prepended to your output. This is perfect for project summaries, LLM system messages, or general instructions.
*   ✍️ **Prompt File Integration:** Optionally append a dedicated "prompt file" (e.g., `final_questions.txt`, `llm_task.md`) at the very end of your assembled output, perfect for specific questions or tasks based on the preceding context and code.
*   🚀 **One-Liner Installation:** Quick and easy setup for macOS & Linux.
*   📋 **Clipboard Power (`klyp copy`):** The primary command. Assembles everything and copies it to your clipboard, ready to paste into your LLM interface.
*   📠 **Print to Terminal (`klyp run`):** View the assembled context directly or pipe it to other tools.
*   🌈 **Colorized Output:** Enhanced readability for commands in your terminal.
*   🔍 **Status Checking:** Easily verify the files included in your scopes, their associated context and prompt files, and check for missing ones.
*   ➕ **Effortless Management:** Simple commands to add/remove files, context, and prompt files.
*   🎯 **Active Scope:** Set a default scope for even faster operations.
*   🐍 **Python-Powered:** Cross-platform (macOS, Linux, Windows with Python).
*   🔄 **Self-Update & Notifications:** Keep Klyp fresh with a simple `klyp update` command, and get notified of new versions.

## Prerequisites

*   **Python 3.7+**
*   **pip** (Python package installer, usually comes with Python)
*   **For Linux users (Clipboard Access):** `xclip` or `xsel` is required by the `pyperclip` library.
    *   Debian/Ubuntu: `sudo apt-get install xclip`
    *   Fedora: `sudo dnf install xclip`
    *   Arch Linux: `sudo pacman -S xclip`
*   **For Windows users (Clipboard Access):** Usually works out-of-the-box.

## Installation

The easiest way to get started on macOS & Linux is with the one-liner installation script.

**Using `curl`:**
```bash
curl -fsSL https://raw.githubusercontent.com/dvvolynkin/klyp-cli/main/install.sh | bash
```

**Or using `wget`:**
```bash
wget -qO- https://raw.githubusercontent.com/dvvolynkin/klyp-cli/main/install.sh | bash
```

This script will:
1.  Download the `klyp.py` script.
2.  Install it to `~/.local/bin/klyp` (a common directory for user-installed executables).
3.  Make it executable.
4.  Install required Python dependencies (`pyperclip`, `colorama`) using `pip`.
5.  Provide guidance if `~/.local/bin` is not in your `PATH`.

**After installation:**
You might need to open a new terminal session or source your shell configuration file (e.g., `source ~/.bashrc`, `source ~/.zshrc`) for the `klyp` command to be available.
Verify by typing:
```bash
klyp --version
```

## How It Works: Scopes, Context Files, and Prompt Files

The core idea behind Klyp-CLI is organizing your project information into **scopes**.

*   A **Scope** is simply a named collection of files relevant to a specific task. For example, you might have a `frontend` scope with your UI components, or a `backend_api` scope with server-side logic files.
*   Each scope can optionally have one **Context File**. This is a text or markdown file (e.g., `project_description.md`, `llm_instructions.txt`) containing any preparatory information, system messages, or general instructions you want to include when you use that scope. Klyp will place the content of this file at the very beginning of the output.
*   Additionally, each scope can optionally have one **Prompt File**. This file's content is appended at the *end* of the Klyp output, after all code files. It's ideal for your specific questions to the LLM, task instructions, or any text that should follow the provided context and code.

When you run `klyp copy <scope_name>`:
1.  Klyp reads the content of the **Context File** (if defined for that scope).
2.  It then lists the paths of all **code files** in the scope.
3.  Then, it includes the full content of each of those **code files**.
4.  Finally, it appends the content of the **Prompt File** (if defined for that scope).
5.  All this is packaged into a single, neatly formatted text block and copied to your clipboard.

## Usage

Once `klyp` is installed, navigate to your project's root directory in the terminal.

### 1. Initialize Klyp
Start by initializing Klyp in your project:
```bash
klyp init
```
This creates a `.klyp.json` configuration file and a default scope named `default`, setting it as the active scope.

### 2. Manage Scopes
*   **List scopes:**
    ```bash
    klyp scope
    ```
*   **Create a new scope & set it active:**
    ```bash
    klyp use <new_scope_name>
    ```
    Example: `klyp use frontend_feature`
    (You can also use `klyp scope add <name>` and `klyp scope set <name>`)

### 3. Add Files, Context, and Prompts to a Scope

*   **Add code files to the current active scope:**
    ```bash
    klyp add ./src/component.js ./styles/main.css
    ```
*   **Add code files to a specific scope:**
    ```bash
    klyp add ./api/routes.py ./api/models.py backend_api_scope
    ```
*   **Set (or change) the Context File for the current active scope:**
    This file's content will be included first in the output.
    ```bash
    klyp add --context ./docs/project_overview.md
    ```
*   **Set the Context File for a specific scope:**
    ```bash
    klyp add --context ./prompts/api_instructions.txt backend_api_scope
    ```
*   **Set (or change) the Prompt File for the current active scope:**
    This file's content will be included last in the output.
    ```bash
    klyp add --prompt ./prompts/llm_questions.md
    ```
*   **Set the Prompt File for a specific scope:**
    ```bash
    klyp add --prompt ./prompts/task_specific_questions.txt backend_api_scope
    ```

### 4. The Magic: Copying Context to Clipboard
This is the primary command you'll use to prepare context for your LLM.

*   **Copy the current active scope's content to clipboard:**
    ```bash
    klyp copy
    ```
*   **Copy a specific scope's content to clipboard:**
    ```bash
    klyp copy <scope_name>
    ```
    Example: `klyp copy frontend_feature`

Now, just paste (Ctrl+V or Cmd+V) into your LLM chat interface!

### 5. Other Useful Commands

*   **Print scope content to terminal (instead of clipboard):**
    ```bash
    klyp run
    klyp run <scope_name>
    ```
*   **Check scope status (see included files, context file, prompt file, and any missing files):**
    ```bash
    klyp status
    klyp status <scope_name>
    ```
*   **Remove files, context, or prompt file:**
    ```bash
    klyp remove ./src/old_component.js # From active scope
    klyp remove ./docs/old_readme.md old_docs_scope
    klyp remove --context # Remove context from active scope
    klyp remove --context old_docs_scope
    klyp remove --prompt # Remove prompt file from active scope
    klyp remove --prompt old_docs_scope
    ```
*   **Update Klyp to the latest version:**
    ```bash
    klyp update
    ```
*   **Get help:**
    ```bash
    klyp --help
    klyp <command> --help
    ```

## Example Workflow

Let's say you're working on a new feature for your web app.

1.  **Initialize Klyp in your project:**
    ```bash
    cd my_web_app_project
    klyp init
    ```

2.  **Create a scope for this feature and make it active:**
    ```bash
    klyp use auth_feature
    ```

3.  **Add relevant code files:**
    ```bash
    klyp add ./src/auth/login.js ./src/auth/api.js ./src/components/AuthForm.vue
    ```

4.  **Add a context file with general instructions for the LLM:**
    Create a file, say `llm_auth_prompt_setup.md`, with content like:
    ```markdown
    You are an expert Vue.js and Node.js developer.
    The following files are part of an authentication feature.
    Please help me by reviewing the code for security best practices and suggesting improvements.
    Focus on the interaction between the frontend components and the backend API.
    ```
    Then add it to the scope:
    ```bash
    klyp add --context ./llm_auth_prompt_setup.md
    ```

5.  **(Optional) Add a prompt file with specific questions:**
    Create a file, say `llm_review_questions.md`, with content like:
    ```markdown
    Based on the provided context and code:
    1. Are there any obvious race conditions?
    2. How could the `AuthForm.vue` component be made more accessible?
    3. Suggest an alternative approach for handling API tokens.
    ```
    Then add it to the scope:
    ```bash
    klyp add --prompt ./llm_review_questions.md
    ```

6.  **Check the status (optional):**
    ```bash
    klyp status auth_feature
    ```

7.  **Copy everything to clipboard for your LLM:**
    ```bash
    klyp copy auth_feature
    ```
    Now, the content of `llm_auth_prompt_setup.md`, followed by the paths and contents of `login.js`, `api.js`, and `AuthForm.vue`, and finally the content of `llm_review_questions.md`, are all in your clipboard, ready to be pasted into your LLM prompt!

## Uninstallation

1.  If you don't have `uninstall.sh` from the initial installation (e.g., if you cloned the repo), download it from the Klyp repository:
    ```bash
    curl -fsSL https://raw.githubusercontent.com/dvvolynkin/klyp-cli/main/uninstall.sh -o uninstall_klyp.sh
    chmod +x uninstall_klyp.sh
    ```
2.  Run the uninstaller:
    ```bash
    ./uninstall_klyp.sh
    ```
This will typically remove the `klyp` executable from `~/.local/bin/klyp`.

Python dependencies (`pyperclip`, `colorama`) are not automatically uninstalled as other tools might use them. If you wish to remove them:
```bash
python3 -m pip uninstall pyperclip colorama
```
Project-specific `.klyp.json` files will remain in your projects unless you manually delete them.

## Contributing

Contributions are welcome! If you have ideas for improvements, new features, or bug fixes, please:

1.  Fork the repository (`https://github.com/dvvolynkin/klyp-cli.git`).
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -am 'Add some feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a Pull Request against the `main` branch of the original repository.

## Issues

If you encounter any bugs or have issues, please report them via the [GitHub Issues](https://github.com/dvvolynkin/klyp-cli/issues) page for this repository.
```