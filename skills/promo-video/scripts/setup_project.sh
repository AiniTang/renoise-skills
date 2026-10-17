#!/usr/bin/env bash
# Create a promo video project from the Remotion template and install deps.
# Usage: setup_project.sh <project-dir>
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:?usage: setup_project.sh <project-dir>}"
NODE_CACHE="$HOME/.cache/promo-video/node"
NODE_VERSION="v22.14.0"

find_node() {
  if [ -n "${PROMO_NODE:-}" ] && [ -x "$PROMO_NODE/node" ]; then echo "$PROMO_NODE"; return; fi
  if command -v node >/dev/null 2>&1; then
    local major
    major="$(node -p 'process.versions.node.split(".")[0]')"
    if [ "$major" -ge 18 ]; then dirname "$(command -v node)"; return; fi
  fi
  if [ -x "$NODE_CACHE/bin/node" ]; then echo "$NODE_CACHE/bin"; return; fi
  for d in "$HOME"/.nvm/versions/node/*/bin /opt/homebrew/bin /usr/local/bin; do
    if [ -x "$d/node" ]; then echo "$d"; return; fi
  done
  echo ""
}

NODE_BIN="$(find_node)"
if [ -z "$NODE_BIN" ]; then
  arch="$(uname -m)"; [ "$arch" = "x86_64" ] && arch="x64"
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  pkg="node-$NODE_VERSION-$os-$arch"
  echo "Node.js not found; downloading portable $pkg to $NODE_CACHE" >&2
  mkdir -p "$NODE_CACHE"
  curl -fsSL "https://nodejs.org/dist/$NODE_VERSION/$pkg.tar.gz" | tar -xz -C "$NODE_CACHE" --strip-components=1
  NODE_BIN="$NODE_CACHE/bin"
fi
export PATH="$NODE_BIN:$PATH"
echo "Using node $(node --version) from $NODE_BIN"

if [ -e "$TARGET/package.json" ]; then
  echo "Project already exists at $TARGET; installing deps only."
else
  mkdir -p "$TARGET"
  cp -R "$SKILL_DIR/templates/remotion/." "$TARGET/"
  mkdir -p "$TARGET/public/music" "$TARGET/public/brand" "$TARGET/public/images" "$TARGET/out"
  cp -R "$SKILL_DIR/assets/sfx" "$TARGET/public/sfx"
  rm -f "$TARGET/public/sfx/preview.wav"
fi

printf 'NODE_BIN=%q\nPROMO_VIDEO_SKILL=%q\n' "$NODE_BIN" "$SKILL_DIR" > "$TARGET/.promo-env"

cd "$TARGET"
npm install --no-audit --no-fund --loglevel=error

SHELL_DIR="node_modules/.remotion/chrome-headless-shell"
if [ ! -d "$SHELL_DIR" ]; then
  cached="$(find "$HOME" -maxdepth 7 -type d -path '*/node_modules/.remotion/chrome-headless-shell' \
    -not -path "$(pwd)/*" 2>/dev/null | head -1 || true)"
  if [ -n "$cached" ]; then
    mkdir -p node_modules/.remotion
    cp -R "$cached" node_modules/.remotion/ && echo "Reused headless browser from $cached"
  else
    echo "Remotion will download its headless browser on first render."
  fi
fi

# rn (renoise-kit) finishes, checks and audits every render; it drives a system ffmpeg built with libass.
if ! command -v rn >/dev/null 2>&1; then
  echo "WARNING: rn not found. Install renoise-kit before rendering: uv tool install 'renoise-kit[all]'" >&2
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "WARNING: ffmpeg not on PATH. macOS: brew install ffmpeg-full && export PATH=\"\$(brew --prefix ffmpeg-full)/bin:\$PATH\"" >&2
fi

echo "Ready: $TARGET"
