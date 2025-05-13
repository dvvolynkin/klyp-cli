# Klyp CLI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- Optional: Add other badges like build status, version, etc. if you set them up -->

**Klyp** is a command-line utility designed to help you efficiently manage, package, and copy scoped project file contents and structure to your clipboard. It's optimized for preparing comprehensive context for AI models like Gemini, Claude, or OpenAI's GPT, making it easier to provide them with the necessary code and information for your prompts.

## Why Klyp?

When working with AI models for coding assistance, analysis, or documentation, providing accurate and complete context is crucial. Klyp streamlines this by:

*   Allowing you to define **scopes** – logical groups of files relevant to a specific task or feature.
*   Generating a clear **project structure** overview.
*   Copying the names and full contents of all files within a scope to your clipboard in a **formatted, AI-friendly way**.
*   Saving you from manually opening, copying, and pasting multiple files.

## Features

*   ✨ **Scoped File Management:** Organize your project files into named scopes.
*   🚀 **One-Liner Installation:** Quick and easy setup.
*   📋 **Clipboard Integration:** Copies structured output directly to your clipboard.
*   🌈 **Colorized Output:** Enhanced readability in the terminal.
*   🔍 **Status Checking:** Verify the integrity of your scopes and find missing files.
*   ➕ **Easy Add/Remove:** Effortlessly manage files within scopes.
*   🎯 **Current Active Scope:** Set a default scope for even faster operations.
*   🐍 **Python-Powered:** Cross-platform (macOS, Linux).

## Prerequisites

*   **Python 3.7+** (Python 3.6 might work but 3.7+ is recommended for newer features like `capture_output` in `subprocess` if used, though `klyp` doesn't currently rely heavily on advanced 3.7+ features).
*   **pip** (Python package installer, usually comes with Python).
*   **For Linux users:** `xclip` or `xsel` is required by the `pyperclip` library for clipboard access.
    *   You can typically install one using your system's package manager:
        *   Debian/Ubuntu: `sudo apt-get install xclip`
        *   Fedora: `sudo dnf install xclip`
        *   Arch Linux: `sudo pacman -S xclip`

## Installation

### One-Liner Install (Recommended for macOS & Linux)

You can install or update `klyp` with a single command. Open your terminal and run:

**Using `curl`:**
```bash
curl -fsSL https://raw.githubusercontent.com/your-username/klyp-cli/main/install.sh | bash
```

**Or using `wget`:**
```bash
wget -qO- https://raw.githubusercontent.com/your-username/klyp-cli/main/install.sh | bash
```

*(Remember to replace `your-username`, `klyp-cli`, and `main` with your actual GitHub username, repository name, and default branch if they differ.)*

The installation script will:
1.  Download the `klyp` script.
2.  Install it to `~/.local/bin/klyp` (a common directory for user-installed executables).
3.  Make it executable.
4.  Install required Python dependencies (`pyperclip`, `colorama`) using `pip`.
5.  Provide guidance if `~/.local/bin` is not in your `PATH`.

**After installation:**
You might need to open a new terminal session or source your shell configuration file (e.g., `source ~/.bashrc`, `source ~/.zshrc`) for the `klyp` command to be available system-wide.
Verify by typing: `klyp --version`

### Manual Installation

If you prefer, or if the one-liner doesn't work for your environment:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/klyp-cli.git
    cd klyp-cli
    ```
    *(Replace with your repository URL)*
2.  **Run the installation script:**
    ```bash
    ./install.sh
    ```

## Usage

Once `klyp` is installed and in your `PATH`, you can use it from any project directory.

### 1. Initialize Klyp
In your project's root directory, run:
```bash
klyp init
```
This creates a `.klyp.json` configuration file and prompts you to name your first scope (e.g., `main_context`, `frontend_api`). This scope will be set as the current active scope.

### 2. Manage Scopes
A "scope" is a named collection of files.

*   **View current and available scopes:**
    ```bash
    klyp scope
    ```
*   **Set a scope as active (or create a new one):**
    ```bash
    klyp scope <scope_name>
    ```
    Example: `klyp scope backend_logic`

### 3. Add Files to a Scope
*   **Add to the current active scope:**
    ```bash
    klyp add ./src/utils.py
    klyp add ./config/settings.json
    ```
*   **Add to a specific scope:**
    ```bash
    klyp add ./docs/README.md documentation_scope
    ```

### 4. Remove Files from a Scope
*   **Remove from the current active scope:**
    ```bash
    klyp remove ./src/old_feature.py
    ```
*   **Remove from a specific scope:**
    ```bash
    klyp remove ./config/settings.json documentation_scope
    ```

### 5. Check Scope Status
See which files are tracked and if any are missing:
*   **Status of all scopes:**
    ```bash
    klyp status
    ```
*   **Status of a specific scope:**
    ```bash
    klyp status backend_logic
    ```

### 6. Run a Scope (Copy to Clipboard)
This is the primary action: it gathers the structure and content of files in a scope and copies it to your clipboard.
*   **Run the current active scope:**
    ```bash
    klyp
    ```
    or
    ```bash
    klyp run
    ```
*   **Run a specific scope by name:**
    ```bash
    klyp <scope_name>
    ```
    Example: `klyp frontend_api`
    or
    ```bash
    klyp run <scope_name>
    ```
    Example: `klyp run frontend_api`

If any files in the scope are missing, `klyp run` will fail and list the problematic files.

### 7. Get Help
*   **General help:**
    ```bash
    klyp --help
    ```
*   **Help for a specific command:**
    ```bash
    klyp <command> --help
    ```
    Example: `klyp add --help`

## Example Workflow

```bash
# Navigate to your project
cd my_ai_project

# Initialize klyp and create a 'core' scope
klyp init
# (Enter 'core' when prompted for scope name)

# Add some key files to the 'core' scope
klyp add ./main.py
klyp add ./src/models.py
klyp add ./src/api/endpoints.py

# Check the status
klyp status

# Create a new scope for documentation tasks
klyp scope docs

# Add documentation files to the 'docs' scope
klyp add README.md
klyp add ./docs/usage.md

# Now, to give context about the core logic to an AI:
klyp core # or `klyp run core`
# The structure and content of main.py, models.py, and endpoints.py are now in your clipboard!

# Later, to give context about documentation:
klyp docs
# README.md and usage.md are now in your clipboard.
```

## Configuration File

Klyp stores its configuration in a `.klyp.json` file in the root of your project directory. You can manually inspect or edit this file, but it's generally recommended to use the `klyp` commands.

## Uninstallation

To uninstall `klyp`:

1.  Navigate to the directory where you originally cloned `klyp-cli` (if you installed manually) or simply run the uninstaller if you have it.
    Alternatively, you can re-download just the uninstaller:
    ```bash
    curl -fsSL https://raw.githubusercontent.com/your-username/klyp-cli/main/uninstall.sh -o uninstall_klyp.sh
    chmod +x uninstall_klyp.sh
    ./uninstall_klyp.sh
    ```
2.  The script will remove the `klyp` executable from `~/.local/bin/klyp`.

Python dependencies (`pyperclip`, `colorama`) are not automatically uninstalled as other tools might use them. If you wish to remove them:
```bash
python3 -m pip uninstall pyperclip colorama
```

Project-specific `.klyp.json` files will remain in your projects unless you manually delete them.

## Contributing

Contributions are welcome! If you have ideas for improvements, new features, or bug fixes, please:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -am 'Add some feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a Pull Request.

Please ensure your code adheres to basic Python best practices and include updates to documentation if necessary.

## Issues

If you encounter any bugs or have issues, please report them via the [GitHub Issues](https://github.com/your-username/klyp-cli/issues) page for this repository.# klyp-cli
