#!/usr/bin/env bash
# Agent2048 — one-command installer
# Usage: curl -fsSL https://raw.githubusercontent.com/reesli/Agent2048/main/install.sh | bash
set -e

INSTALL_DIR="${AGENT2048_INSTALL_DIR:-$HOME/.agent2048-src}"
VENV_DIR="${AGENT2048_VENV_DIR:-$HOME/.venvs/agent2048}"
BIN_DIR="$HOME/.local/bin"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║          Agent2048 — Installer                           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "✗ Python 3 not found. Install python3 first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "→ Python $PYTHON_VERSION found"

# Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "→ Updating existing install at $INSTALL_DIR"
    cd "$INSTALL_DIR"
    git pull --quiet
else
    echo "→ Cloning Agent2048 to $INSTALL_DIR"
    git clone --quiet https://github.com/reesli/Agent2048.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create venv
echo "→ Creating virtualenv at $VENV_DIR"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Install
echo "→ Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -e .

# Create symlink
mkdir -p "$BIN_DIR"
ln -sf "$VENV_DIR/bin/agent2048" "$BIN_DIR/agent2048"

# Check PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "⚠  $BIN_DIR is not in your PATH"
    echo "   Add this to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

# Create global .env if not exists
CONFIG_DIR="$HOME/.config/agent2048"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/.env" ]; then
    cat > "$CONFIG_DIR/.env" << 'ENVEOF'
OPENAI_API_KEY=your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o-mini
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
DB_PATH=
ENVEOF
    echo "→ Created global config at $CONFIG_DIR/.env"
    echo "  Edit it to add your API key:"
    echo "  vi $CONFIG_DIR/.env"
else
    echo "→ Global config already exists at $CONFIG_DIR/.env"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✓ Agent2048 installed!                                  ║"
echo "║                                                          ║"
echo "║  Quick start:                                            ║"
echo "║    agent2048 providers    # list providers               ║"
echo "║    agent2048 use openai   # activate provider            ║"
echo "║    agent2048 tui          # interactive control panel    ║"
echo "║                                                          ║"
echo "║  Set your API key:                                       ║"
echo "║    vi ~/.config/agent2048/.env                           ║"
echo "╚══════════════════════════════════════════════════════════╝"
