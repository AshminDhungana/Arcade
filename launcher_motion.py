"""Tasteful, reduced-motion-aware micro-motion for the launcher.

The CustomTkinter draw engine cannot animate two containers at once without
stutter, so screen transitions are short and sequential (fade out, swap, fade in).
"""

from __future__ import annotations

import platform
import subprocess


def prefers_reduced_motion() -> bool:
    """Read the OS "reduce motion" setting once. Best-effort; never raises."""
    system = platform.system()
    if system == "Windows":
        try:
            from ctypes import windll  # type: ignore

            # SPI_GETCLIENTAREAANIMATION = 0x1042; 0 => animations off
            return windll.user32.SystemParametersInfoW(0x1042, 0, 0, 0) == 0
        except Exception:
            try:
                import winreg

                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                ) as k:
                    return winreg.QueryValueEx(k, "VisualFXSetting")[0] == 2
            except Exception:
                return False
    if system == "Darwin":
        try:
            out = subprocess.run(  # noqa: S603
                ["defaults", "read", "-g", "NSAutomaticReduceMotion"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=2,
            )
            return out.stdout.strip() == "1"
        except Exception:
            return False
    try:
        out = subprocess.run(  # noqa: S603
            ["gsettings", "get", "org.gnome.desktop.interface", "enable-animations"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=2,
        )
        return out.stdout.strip() == "false"
    except Exception:
        return False


def _ramp(root, start, end, ms, then=None):
    steps = max(1, round(ms / 20))
    delta = (end - start) / steps

    def step(i=0):
        val = max(0.0, min(1.0, start + delta * i))
        try:
            root.attributes("-alpha", val)
        except Exception:  # noqa: S110
            pass
        if i < steps:
            root.after(20, step, i + 1)
        elif then:
            then()

    step(0)


def screen_transition(root, swap, *, fade_out=180, fade_in=200, reduced=False):
    """Fade the window out, run `swap()` (which replaces content), fade back in.

    When `reduced` is True, swap instantly with no animation.
    """
    if reduced:
        swap()
        return
    _ramp(
        root, 1.0, 0.0, fade_out, then=lambda: (swap(), _ramp(root, 0.0, 1.0, fade_in))
    )


def animate_pill(pill, color, glyph, text, ms=140, reduced=False):
    """Update a status pill's glyph + label + color. Instant (the screen
    transition + toast carry the motion); reduced flag reserved for future."""
    pill.configure(text=f"{glyph}  {text}", fg_color=color)
