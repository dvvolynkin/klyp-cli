#!/usr/bin/env bash

# Klyp Installer Script
# Version: 1.2 (Update Support & Robust Shebang)
#
# This script installs the Klyp CLI tool.
# It downloads the main Python script from GitHub, modifies its shebang
# to point to a specific Python 3 interpreter, configures it for updates,
# places it in a common user binary directory, makes it executable,
# and installs/upgrades Python dependencies for that specific interpreter.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Script Configuration (USER CAN UPDATE THESE FOR THEIR FORK) ---
GITHUB_USER="dvvolynkin"          # Your GitHub username (e.g., dvvolynkin)
GITHUB_REPO="klyp-cli"            # Your Klyp repository name (e.g., klyp-cli)
DEFAULT_BRANCH="main"             # Default branch of your repository (e.g., main, master)
SCRIPT_NAME="klyp"                # The command name for the installed tool
# --- End Script Configuration ---

# Installation directory
INSTALL_DIR_BASE="$HOME/.local"
INSTALL_DIR="$INSTALL_DIR_BASE/bin"

# Source URL for the main klyp.py script
KLYP_PY_URL="https://raw.githubusercontent.com/${GITHUB_USER}/${GITHUB_REPO}/${DEFAULT_BRANCH}/klyp.py"
TEMP_KLYP_PY="/tmp/klyp.py.download.$$" # Temporary download location for klyp.py
INSTALLED_KLYP_SCRIPT_PATH="$INSTALL_DIR/$SCRIPT_NAME"

# Python dependencies
PYTHON_DEPENDENCIES="pyperclip colorama"

# --- Helper Functions ---
info() {
    # Using printf for better compatibility and control over newlines
    printf "[INFO] %s\n" "$1"
}

warn() {
    printf "[WARN] %s\n" "$1"
}

error() {
    printf "[ERROR] %s\n" "$1" >&2
    exit 1
}

TEMP_FILES_TO_CLEANUP=()
cleanup_temp_files() {
    for temp_file in "${TEMP_FILES_TO_CLEANUP[@]}"; do
        if [ -f "$temp_file" ]; then
            rm -f "$temp_file"
        fi
    done
}
# Ensure cleanup on exit, interrupt, or termination
trap cleanup_temp_files EXIT SIGINT SIGTERM

# Register a temp file for cleanup
add_to_cleanup() {
    TEMP_FILES_TO_CLEANUP+=("$1")
}

# --- Main Installation Logic ---
info "Starting Klyp CLI installation/update..."

# 1. Check prerequisites & determine Python 3 path
info "Determining Python 3 interpreter path..."
if ! PYTHON3_PATH=$(command -v python3); then
    error "Python 3 is not installed or not found in your PATH. Please install Python 3."
fi
PYTHON_VERSION=$("$PYTHON3_PATH" --version 2>&1)
info "Using Python 3 interpreter: $PYTHON3_PATH ($PYTHON_VERSION)"

info "Checking for pip (for this Python 3 interpreter)..."
if ! "$PYTHON3_PATH" -m pip --version &> /dev/null; then
    error "pip is not available for $PYTHON3_PATH. Please ensure pip is installed for this Python interpreter."
fi
info "Found pip: $($PYTHON3_PATH -m pip --version | head -n 1)"

# 2. Download klyp.py
info "Downloading Klyp script from $KLYP_PY_URL..."
add_to_cleanup "$TEMP_KLYP_PY" # Register for cleanup
if command -v curl &> /dev/null; then
    # -f: fail silently on server errors, -s: silent, -S: show error on fail, -L: follow redirects
    if ! curl -fsSL "$KLYP_PY_URL" -o "$TEMP_KLYP_PY"; then
        error "curl failed to download $KLYP_PY_URL. Check URL and internet connection."
    fi
elif command -v wget &> /dev/null; then
    # -q: quiet, -O: output to file
    if ! wget -q "$KLYP_PY_URL" -O "$TEMP_KLYP_PY"; then
        error "wget failed to download $KLYP_PY_URL. Check URL and internet connection."
    fi
else
    error "Neither curl nor wget is available. Please install one to download Klyp."
fi

if [ ! -s "$TEMP_KLYP_PY" ]; then # Check if file is not empty
    error "Failed to download klyp.py or downloaded file is empty. Check the URL: $KLYP_PY_URL"
fi
info "Download successful to temporary location: $TEMP_KLYP_PY"

# 2b. Configure klyp.py with repository information for updates
TEMP_KLYP_PY_TO_INSTALL="$TEMP_KLYP_PY" # Default to the original download

CONFIGURED_KLYP_PY="/tmp/klyp.py.configured.$$"
add_to_cleanup "$CONFIGURED_KLYP_PY" # Register for cleanup

info "Attempting to configure Klyp script with repository information for 'klyp update'..."
# Replace placeholder strings within klyp.py with actual values from this script's config.
# This allows 'klyp update' to point to the correct repository if Klyp is forked.
# Using | as sed delimiter.
if sed \
    -e "s/__KLYP_GITHUB_USER__/${GITHUB_USER}/g" \
    -e "s/__KLYP_GITHUB_REPO__/${GITHUB_REPO}/g" \
    -e "s/__KLYP_DEFAULT_BRANCH__/${DEFAULT_BRANCH}/g" \
    "$TEMP_KLYP_PY" > "$CONFIGURED_KLYP_PY"; then
    
    TEMP_KLYP_PY_TO_INSTALL="$CONFIGURED_KLYP_PY" # Use configured version for installation
    info "Klyp script configured to update from ${GITHUB_USER}/${GITHUB_REPO} (branch: ${DEFAULT_BRANCH})."
else
    warn "Failed to configure klyp.py with specific repository information using sed."
    warn "The 'klyp update' command will use default update URLs compiled into klyp.py."
    # TEMP_KLYP_PY_TO_INSTALL remains $TEMP_KLYP_PY (the original download)
fi


# 3. Prepare installation directory
info "Preparing installation directory: $INSTALL_DIR"
if ! mkdir -p "$INSTALL_DIR"; then
    error "Failed to create installation directory $INSTALL_DIR. Check permissions."
fi

# 4. Check if INSTALL_DIR is in PATH
PATH_MSG_SHOWN=0
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    PATH_MSG_SHOWN=1
    warn ""
    warn "Directory '$INSTALL_DIR' is not in your PATH."
    warn "To use the '$SCRIPT_NAME' command directly from any location,"
    warn "you need to add this directory to your PATH environment variable."
    warn "You can usually do this by adding the following line to your shell"
    warn "configuration file (e.g., ~/.bashrc, ~/.zshrc, ~/.profile, or ~/.bash_profile):"
    warn ""
    warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    warn ""
    warn "After adding this line, you'll need to either open a new terminal session"
    warn "or source your shell configuration file (e.g., 'source ~/.zshrc')."
    warn ""
    # shellcheck disable=SC2162 # We want the user to press enter
    read -p "Press Enter to continue with the installation, or Ctrl+C to abort..."
fi

# 5. Create and install the Klyp script with the correct shebang
info "Installing $SCRIPT_NAME to $INSTALLED_KLYP_SCRIPT_PATH..."

# Create the script content
# The first line is the shebang pointing to the specific Python interpreter
# The rest is the content of the (potentially configured) klyp.py
{
    echo "#!${PYTHON3_PATH}"
    echo "# Klyp CLI - Main executable script"
    echo "# This script was generated by the Klyp installer."
    echo "# It uses the Python interpreter at ${PYTHON3_PATH} and its associated site-packages."
    echo "# Repository for updates: ${GITHUB_USER}/${GITHUB_REPO} (branch: ${DEFAULT_BRANCH})"
    echo ""
    cat "$TEMP_KLYP_PY_TO_INSTALL" # Use the (possibly) sed-modified file
} > "$INSTALLED_KLYP_SCRIPT_PATH"

if [ ! -s "$INSTALLED_KLYP_SCRIPT_PATH" ]; then # Check if target script was created and is not empty
    error "Failed to create the Klyp script at $INSTALLED_KLYP_SCRIPT_PATH."
fi

# Make it executable
if ! chmod +x "$INSTALLED_KLYP_SCRIPT_PATH"; then
    error "Failed to make $INSTALLED_KLYP_SCRIPT_PATH executable. Check permissions."
fi
info "Script installed and made executable."

# Temporary files are handled by the trap EXIT

# 6. Install/Upgrade Python dependencies for the chosen PYTHON3_PATH
info "Installing/Upgrading Python dependencies ($PYTHON_DEPENDENCIES) for $PYTHON3_PATH..."
# Use the specific PYTHON3_PATH to run pip, and --upgrade flag
if "$PYTHON3_PATH" -m pip install --upgrade $PYTHON_DEPENDENCIES; then
    info "Python dependencies installed/upgraded successfully."
else
    warn "Failed to install/upgrade Python dependencies automatically using $PYTHON3_PATH."
    warn "Please try installing/upgrading them manually for that interpreter:"
    warn "  $PYTHON3_PATH -m pip install --upgrade $PYTHON_DEPENDENCIES"
    warn "Klyp might not function correctly without these dependencies."
fi

# 7. OS-specific checks (e.g., for Linux clipboard tools)
if [[ "$(uname)" == "Linux" ]]; then
    info "Checking for Linux clipboard utilities (xclip or xsel for pyperclip)..."
    if ! command -v xclip &> /dev/null && ! command -v xsel &> /dev/null; then
        warn "'xclip' or 'xsel' not found. These are typically required by 'pyperclip' on Linux."
        warn "If clipboard functionality doesn't work, please install one of them."
        warn "Example (Debian/Ubuntu): sudo apt-get install xclip"
        warn "Example (Fedora):       sudo dnf install xclip"
    else
        info "Found a Linux clipboard utility (or one is not strictly needed by pyperclip on your setup)."
    fi
fi

# 8. Final messages
info ""
info "------------------------------------------------------------"
info " Klyp CLI installation/update complete!"
info "------------------------------------------------------------"
info "$SCRIPT_NAME has been installed to: $INSTALLED_KLYP_SCRIPT_PATH"
if [ "$PATH_MSG_SHOWN" -eq 1 ]; then
    info "IMPORTANT: Remember to update your PATH as mentioned above if it wasn't already set."
    info "You may need to open a new terminal or source your shell configuration file."
fi
info "You can now try running: $SCRIPT_NAME --version"
info "For help, run: $SCRIPT_NAME --help"
info "To update Klyp in the future, run: $SCRIPT_NAME update"
info "------------------------------------------------------------"

exit 0