"""Generate committed PNG fallbacks for the launcher logo from the brand SVG.

Run once (developer machine) after changing the SVG.
Prefers cairosvg (portable path for Linux/macOS build machines);
falls back to Playwright Chromium when cairosvg is unavailable (Windows dev box).

Produces:
    arcade_logo_light.png (blue gradient square + white controller glyph)
    arcade_logo_white.png (white controller glyph on transparent background)
Both at 256×256 RGBA, placed beside launcher.py (repo root).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _dark_svg(svg: str) -> str:
    """Drop the gradient-filled background square to transparent, leaving only
    the white controller glyph — used for the dark-mode logo variant."""
    return re.sub(
        r'<rect[^>]*fill="url\(#brandGradient\)"[^>]*/>',
        '<rect width="24" height="24" rx="5" ry="5" fill="none"/>',
        svg,
    )


def _generate_with_cairosvg(
    svg_path: Path, out_light: Path, out_white: Path, size: int
) -> bool:
    """Try generating PNGs with cairosvg. Returns True on success."""
    try:
        import cairosvg
    except ImportError:
        return False

    try:
        svg_text = svg_path.read_text(encoding="utf-8")
        # Light variant: SVG as-is
        cairosvg.svg2png(
            bytestring=svg_text.encode("utf-8"),
            write_to=str(out_light),
            output_width=size,
            output_height=size,
        )
        # Dark/white variant: transform SVG
        dark_svg = _dark_svg(svg_text)
        cairosvg.svg2png(
            bytestring=dark_svg.encode("utf-8"),
            write_to=str(out_white),
            output_width=size,
            output_height=size,
        )
        print(f"Generated {out_light.name} and {out_white.name} via cairosvg")
        return True
    except Exception as e:
        print(f"cairosvg generation failed: {e}", file=sys.stderr)
        return False


def _generate_with_playwright(
    svg_path: Path, out_light: Path, out_white: Path, size: int
) -> bool:
    """Generate PNGs using Playwright Chromium. Returns True on success."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    try:
        svg_text = svg_path.read_text(encoding="utf-8")
        dark_svg_text = _dark_svg(svg_text)

        def svg_to_html(svg_content: str) -> str:
            # Make the SVG explicitly 256x256 and remove any viewBox scaling issues
            target = f'width="{size}" height="{size}"'
            svg_sized = svg_content.replace('width="24" height="24"', target)
            return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        * {{ margin: 0; padding: 0; }}
        html, body {{ width: {size}px; height: {size}px; background: transparent; }}
        svg {{ display: block; }}
    </style>
</head>
<body>
{svg_sized}
</body>
</html>"""

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": size, "height": size})

            # Light variant
            page.set_content(svg_to_html(svg_text), wait_until="load")
            page.screenshot(path=str(out_light), omit_background=True)

            # White/dark variant
            page.set_content(svg_to_html(dark_svg_text), wait_until="load")
            page.screenshot(path=str(out_white), omit_background=True)

            browser.close()

        print(f"Generated {out_light.name} and {out_white.name} via Playwright")
        return True
    except Exception as e:
        print(f"Playwright generation failed: {e}", file=sys.stderr)
        return False


def main() -> int:
    launcher_dir = Path(__file__).resolve().parent.parent.parent
    svg_path = launcher_dir / "frontend" / "public" / "arcade_icon.svg"
    out_light = launcher_dir / "arcade_logo_light.png"
    out_white = launcher_dir / "arcade_logo_white.png"
    SIZE = 256

    if not svg_path.is_file():
        print(f"SVG not found: {svg_path}", file=sys.stderr)
        return 1

    # Try cairosvg first (preferred for CI/Linux/macOS)
    if _generate_with_cairosvg(svg_path, out_light, out_white, SIZE):
        return 0

    # Fall back to Playwright (Windows dev box)
    print("Falling back to Playwright...")
    if _generate_with_playwright(svg_path, out_light, out_white, SIZE):
        return 0

    print(
        "Both cairosvg and Playwright failed. Install one of them to generate logos.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
