#!/data/data/com.termux/files/usr/bin/bash
# RXOS-TUI Installer for Termux
# Run: bash install.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  RXOS-TUI Installer v1.2"
echo "  Termux-native build"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "[1/6] Updating packages..."
pkg update -y && pkg upgrade -y

echo "[2/6] Installing Python + build tools..."
pkg install -y python python-pip build-essential libffi openssl

echo "[3/6] Installing native Python packages via pkg..."
pkg install -y python-psutil python-cryptography 2>/dev/null || {
  echo "  pkg fallback: trying pip..."
  pip install --break-system-packages psutil cryptography --no-build-isolation
}

echo "[4/6] Installing mpv (music playback)..."
pkg install -y mpv 2>/dev/null || echo "  Warning: mpv not available — music disabled"

echo "[5/6] Installing Textual + yt-dlp via pip..."
pip install --break-system-packages textual yt-dlp

echo "[6/6] Creating rxos command..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p $PREFIX/bin
cat > $PREFIX/bin/rxos << RXEOF
#!/data/data/com.termux/files/usr/bin/bash
cd "$SCRIPT_DIR"
python run.py
RXEOF
chmod +x $PREFIX/bin/rxos

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Done! Run with: rxos"
echo ""
echo "  New in v1.2:"
echo "  💻 Terminal  →  key B (Bash)"
echo "  🎵 Music     →  key F (FM/audio)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
