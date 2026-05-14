"""One-shot asset generator for the onboarding library backdrop.

Reads the original Unsplash JPEG and writes three optimised variants:
  - library-bg.webp        — 1920px desktop WebP, quality 80
  - library-bg-mobile.webp — 768px mobile WebP, quality 80
  - library-bg.jpg         — 1920px JPEG fallback, quality 85

Uses Image.thumbnail() so the aspect ratio is preserved; the CSS
background-size: cover handles responsive cropping.

Build-time only — Pillow is not a runtime dependency.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


SRC = Path.home() / "Downloads" / "peter-herrmann-O_DUcg4cDlc-unsplash.jpg"
OUT_DIR = Path(__file__).resolve().parent.parent / "app" / "static" / "images" / "onboarding"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with Image.open(SRC) as im:
        im = im.convert("RGB")

        # Desktop WebP — 1920px wide.
        desktop = im.copy()
        desktop.thumbnail((1920, 1920), Image.LANCZOS)
        desktop_path = OUT_DIR / "library-bg.webp"
        desktop.save(desktop_path, format="WEBP", quality=80, method=6)
        print(f"  {desktop_path.name}: {desktop.size}, {desktop_path.stat().st_size // 1024} KB")

        # Mobile WebP — 768px wide.
        mobile = im.copy()
        mobile.thumbnail((768, 768), Image.LANCZOS)
        mobile_path = OUT_DIR / "library-bg-mobile.webp"
        mobile.save(mobile_path, format="WEBP", quality=80, method=6)
        print(f"  {mobile_path.name}: {mobile.size}, {mobile_path.stat().st_size // 1024} KB")

        # JPEG fallback — 1920px wide.
        jpeg = im.copy()
        jpeg.thumbnail((1920, 1920), Image.LANCZOS)
        jpeg_path = OUT_DIR / "library-bg.jpg"
        jpeg.save(jpeg_path, format="JPEG", quality=85, optimize=True, progressive=True)
        print(f"  {jpeg_path.name}: {jpeg.size}, {jpeg_path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
