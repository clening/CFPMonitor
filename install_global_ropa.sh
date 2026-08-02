#!/bin/bash
# Install global ROPA hooks — runs once, applies to all git repos on this machine.
# After running this, every git commit triggers an automatic ROPA check.
#
# What this does:
#   1. Copies check_ropa.py and audit_history.py to ~/.config/git/hooks/
#   2. Installs a global pre-commit shell hook there
#   3. Sets git's global core.hooksPath so every repo uses it
#
# NOTE: If a repo sets its own core.hooksPath, that takes precedence.
# NOTE: audit_history.py can be run from any project directory:
#   python3 ~/.config/git/hooks/audit_history.py --since 2026-01-01

set -e

HOOKS_DIR="$HOME/.config/git/hooks"
mkdir -p "$HOOKS_DIR"

echo "Installing global ROPA hooks to $HOOKS_DIR..."

cp "$HOME/.config/git/hooks/check_ropa.py" "$HOOKS_DIR/check_ropa.py"
cp "$HOME/.config/git/hooks/audit_history.py" "$HOOKS_DIR/audit_history.py"
cp "$HOME/.config/git/hooks/pre-commit" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit" "$HOOKS_DIR/check_ropa.py" "$HOOKS_DIR/audit_history.py"

git config --global core.hooksPath "$HOOKS_DIR"

echo ""
echo "Done. Global ROPA hook is active for all git repos."
echo ""
echo "To scan an existing project's history:"
echo "  cd /path/to/your/project"
echo "  python3 $HOOKS_DIR/audit_history.py --since 2026-01-01"
echo ""
echo "To disable for a specific repo:"
echo "  git config core.hooksPath .git/hooks  # (inside that repo)"
