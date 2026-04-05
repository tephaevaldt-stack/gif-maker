#!/bin/bash
# ─────────────────────────────────────────
#  GIF Maker — Setup & Inicialização
# ─────────────────────────────────────────

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ██████╗ ██╗███████╗    ███╗   ███╗ █████╗ ██╗  ██╗███████╗██████╗"
echo "  ██╔════╝ ██║██╔════╝    ████╗ ████║██╔══██╗██║ ██╔╝██╔════╝██╔══██╗"
echo "  ██║  ███╗██║█████╗      ██╔████╔██║███████║█████╔╝ █████╗  ██████╔╝"
echo "  ██║   ██║██║██╔══╝      ██║╚██╔╝██║██╔══██║██╔═██╗ ██╔══╝  ██╔══██╗"
echo "  ╚██████╔╝██║██║         ██║ ╚═╝ ██║██║  ██║██║  ██╗███████╗██║  ██║"
echo "   ╚═════╝ ╚═╝╚═╝         ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝"
echo ""
echo "  YouTube · Instagram · TikTok → GIF"
echo ""

# Detectar OS
if [[ "$OSTYPE" == "darwin"* ]]; then
  OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  OS="linux"
else
  OS="other"
fi

# Verificar dependências
check_dep() {
  if ! command -v "$1" &>/dev/null; then
    echo "  ✗ $1 não encontrado."
    if [[ "$OS" == "macos" ]]; then
      echo "    Instale com: brew install $2"
    elif [[ "$OS" == "linux" ]]; then
      echo "    Instale com: sudo apt install $2   ou   sudo dnf install $2"
    fi
    return 1
  else
    echo "  ✓ $1 encontrado"
    return 0
  fi
}

echo "[ Verificando dependências do sistema ]"
MISSING=0
check_dep python3 python3 || MISSING=1
check_dep ffmpeg ffmpeg || MISSING=1
check_dep yt-dlp yt-dlp || MISSING=1

if [[ $MISSING -eq 1 ]]; then
  echo ""
  echo "  ⚠ Instale as dependências acima e rode este script novamente."
  echo ""
  if [[ "$OS" == "macos" ]]; then
    echo "  Instalação rápida no macOS:"
    echo "    brew install ffmpeg yt-dlp python3"
  elif [[ "$OS" == "linux" ]]; then
    echo "  Instalação rápida no Ubuntu/Debian:"
    echo "    sudo apt update && sudo apt install ffmpeg python3 python3-pip"
    echo "    pip3 install yt-dlp"
  fi
  exit 1
fi

echo ""
echo "[ Instalando dependências Python ]"
pip3 install flask flask-cors --quiet
echo "  ✓ Flask instalado"

echo ""
echo "[ Iniciando servidor ]"
echo "  ➜  http://localhost:5000"
echo ""
echo "  Pressione Ctrl+C para parar."
echo ""

python3 app.py
