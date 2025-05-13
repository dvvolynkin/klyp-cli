#!/usr/bin/env bash

# Klyp Uninstaller Script
#
# This script removes the Klyp CLI tool previously installed by install.sh.

# Exit immediately if a command exits with a non-zero status (optional, but good for safety).
# set -e

# --- Script Configuration ---
SCRIPT_NAME="klyp"                # The command name of the installed tool
# Installation directory (should match install.sh)
INSTALL_DIR_BASE="$HOME/.local"
INSTALL_DIR="$INSTALL_DIR_BASE/bin"
# --- End Script Configuration ---

# --- Helper Functions ---
info() {
    echo "[INFO] $1"
}

warn() {
    echo "[WARN] $1"
}

# --- Main Uninstallation Logic ---
info "Starting Klyp CLI uninstallation..."

# 1. Confirm with the user
echo ""
read -p "Are you sure you want to uninstall $SCRIPT_NAME from $INSTALL_DIR? (y/N): " confirmation
echo ""
if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
    info "Uninstallation cancelled by user."
    exit 0
fi

# 2. Remove the script executable
SCRIPT_PATH="$INSTALL_DIR/$SCRIPT_NAME"
if [ -f "$SCRIPT_PATH" ]; then
    info "Removing $SCRIPT_PATH..."
    if rm -f "$SCRIPT_PATH"; then
        info "$SCRIPT_NAME executable has been successfully removed."
    else
        warn "Failed to remove $SCRIPT_PATH. Please check permissions or remove it manually."
    fi
else
    info "$SCRIPT_NAME not found at $SCRIPT_PATH. It might have been already removed or installed elsewhere."
fi

# 3. Inform about Python dependencies (not automatically removed)
echo ""
warn "Python dependencies (pyperclip, colorama) installed by Klyp are NOT automatically uninstalled."
warn "This is to prevent breaking other tools that might rely on them."
warn "If you are sure you no longer need these packages system-wide (or for your user), you can"
warn "attempt to uninstall them manually using pip:"
warn "  python3 -m pip uninstall pyperclip colorama"
warn "(You might need to confirm the uninstallation for each package)."

# 4. Inform about configuration files
echo ""
warn "Project-specific '.klyp.json' configuration files created in your project directories"
warn "are NOT removed by this uninstaller. You can delete them manually if desired."

# 5. Final message
info ""
info "------------------------------------------------------------"
info " Klyp CLI uninstallation process finished."
info "------------------------------------------------------------"
info "If $SCRIPT_NAME was in your PATH, you might need to open a new terminal"
info "for the command to no longer be recognized (if the PATH entry was specific)."
info "------------------------------------------------------------"

exit 0