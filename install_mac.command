#!/bin/zsh
set -e
cd "$(dirname "$0")"

echo "=== PDF 水印清理：首次安装 ==="
if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 python3。请先安装 Python 3（推荐 python.org 或 Homebrew）。"
  read -k 1 "?按任意键退出..."
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/make_icon.py

# Convert PNG iconset to .icns on macOS.
if command -v iconutil >/dev/null 2>&1; then
  iconutil -c icns assets/AppIcon.iconset -o assets/AppIcon.icns
fi

ICON_ARGS=()
if [ -f assets/AppIcon.icns ]; then
  ICON_ARGS=(--icon assets/AppIcon.icns)
fi

pyinstaller --noconfirm --clean --windowed \
  --name "PDF 水印清理" \
  "${ICON_ARGS[@]}" \
  app.py

mkdir -p "$HOME/Applications"
rm -rf "$HOME/Applications/PDF 水印清理.app"
cp -R "dist/PDF 水印清理.app" "$HOME/Applications/"

echo ""
echo "安装完成：$HOME/Applications/PDF 水印清理.app"
echo "Finder 已打开。把应用拖到 Dock，以后直接点图标即可。"
open "$HOME/Applications"
read -k 1 "?按任意键结束..."
