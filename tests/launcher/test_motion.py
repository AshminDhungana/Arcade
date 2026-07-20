import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import launcher_motion as motion  # noqa: E402


def test_prefers_reduced_motion_returns_bool():
    import platform

    with mock.patch.object(platform, "system", return_value="Linux"):
        assert motion.prefers_reduced_motion() in (True, False)


def test_screen_transition_reduced_calls_swap_only():
    class FakeRoot:
        def attributes(self, *a, **k):
            pass

        def after(self, *a, **k):
            pass

    called = {}
    root = FakeRoot()
    motion.screen_transition(
        root, lambda: called.setdefault("swap", True), reduced=True
    )
    assert called.get("swap") is True


def test_animate_pill_sets_text_and_color():
    class FakePill:
        def __init__(self):
            self.kw = {}

        def configure(self, **kw):
            self.kw.update(kw)

    pill = FakePill()
    motion.animate_pill(pill, ("#16A34A", "#22C55E"), "●", "Running", reduced=True)
    assert "Running" in pill.kw["text"]
    assert pill.kw["fg_color"] == ("#16A34A", "#22C55E")
