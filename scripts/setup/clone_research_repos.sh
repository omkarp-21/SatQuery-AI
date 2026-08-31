#!/usr/bin/env bash
# Clone the research reference repos into external/research/ at pinned commits.
# Read-only reference. These dirs are gitignored. Do NOT modify their source.
# Do NOT install their deps into the main env (see docs/research/*).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="$ROOT/external/research"
mkdir -p "$DEST"

# name | url | pinned commit
REPOS=(
  "awesome-rs-vlms|https://github.com/lzw-lzw/awesome-remote-sensing-vision-language-models|4d620f38e07a4c77a5d4d362fa68a012bc7ab011"
  "GeoChat|https://github.com/mbzuai-oryx/GeoChat|4850920e005a849bd224d0ce35aa9db031fa5155"
  "Change-Agent|https://github.com/Chen-Yang-Liu/Change-Agent|68cbaa7f388b36e4fc10872f7a2911482d26ae5b"
  "ChangeChat|https://github.com/hanlinwu/ChangeChat|9facf50c68efa32f446f0f3aa700c0b76309029e"
  "ChangeFormer|https://github.com/wgcban/ChangeFormer|afd1b7ed640aa265a2c730de958416ae7356a2f9"
  "RemoteCLIP|https://github.com/ChenDelong1999/RemoteCLIP|a6a4787507e441f444c20404c90dd18520a8960d"
  "CROMA|https://github.com/antofuller/CROMA|59505a6bcadbf36ba20767270154bf9f3067c5e7"
  "DOFA|https://github.com/zhu-xlab/DOFA|0cfb7e1099f4d4c4022946ff7862c7cd7b8411b9"
)

for entry in "${REPOS[@]}"; do
  IFS='|' read -r name url commit <<<"$entry"
  target="$DEST/$name"
  if [ -d "$target/.git" ]; then
    echo "== $name already present, skipping"
    continue
  fi
  echo "== cloning $name"
  git clone --depth 1 "$url" "$target"
  # Best-effort pin to the recorded commit (shallow clones may need a fetch).
  if ! git -C "$target" cat-file -e "$commit^{commit}" 2>/dev/null; then
    git -C "$target" fetch --depth 1 origin "$commit" 2>/dev/null || true
  fi
  git -C "$target" checkout -q "$commit" 2>/dev/null \
    && echo "   pinned to $commit" \
    || echo "   WARNING: could not pin $name to $commit (using clone HEAD)"
done

echo "Done. See docs/research/model_inventory.md"
