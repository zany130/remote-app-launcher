"""Unit tests for launcher helper functions."""

import sys
import os
from unittest.mock import MagicMock, patch

# Ensure the project root is on the path when running tests from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from launcher import FzfError, parse_fzf_selection, run_fzf, FZF_DISPLAY_DELIM
from models import App


DELIM = FZF_DISPLAY_DELIM  # " | "


class TestParseFzfSelection:
    """Tests for parse_fzf_selection."""

    def test_normal_line(self):
        """Standard three-part line returns the last field (desktop_id)."""
        line = f"VLC media player{DELIM}Video;AudioVideo{DELIM}vlc.desktop"
        assert parse_fzf_selection(line) == "vlc.desktop"

    def test_strips_whitespace(self):
        """Trailing/leading whitespace around the desktop_id is stripped."""
        line = f"App{DELIM}Cat{DELIM}  my.desktop  "
        assert parse_fzf_selection(line) == "my.desktop"

    def test_empty_categories(self):
        """Category field may be empty; desktop_id is still the last part."""
        line = f"App{DELIM}{DELIM}nocat.desktop"
        assert parse_fzf_selection(line) == "nocat.desktop"

    def test_none_on_empty_string(self):
        assert parse_fzf_selection("") is None

    def test_none_on_whitespace_only(self):
        assert parse_fzf_selection("   ") is None

    def test_none_on_empty_desktop_id(self):
        """An empty desktop_id field should return None."""
        assert parse_fzf_selection(f"App{DELIM}Cat{DELIM}   ") is None

    def test_none_when_fewer_than_three_parts(self):
        """A line without enough delimiters should return None."""
        assert parse_fzf_selection(f"App{DELIM}only-two-parts") is None

    def test_exactly_three_parts(self):
        line = f"Firefox{DELIM}Network{DELIM}firefox.desktop"
        assert parse_fzf_selection(line) == "firefox.desktop"

    def test_desktop_id_with_dots_and_hyphens(self):
        """Desktop IDs can contain dots, hyphens, underscores."""
        line = f"GIMP{DELIM}Graphics{DELIM}org.gnome.gimp-2.10.desktop"
        assert parse_fzf_selection(line) == "org.gnome.gimp-2.10.desktop"


class TestRunFzfErrors:
    """Tests that run_fzf raises FzfError on hard failures."""

    _APP = App(name="Foo", desktop_id="foo.desktop", desktop_path="/foo.desktop")

    def test_raises_on_no_tty(self):
        """FzfError is raised when /dev/tty cannot be opened."""
        with patch("builtins.open", side_effect=OSError("No such file")):
            try:
                run_fzf([self._APP])
                assert False, "Expected FzfError"
            except FzfError as exc:
                assert "/dev/tty" in str(exc)

    def test_raises_when_fzf_not_found(self):
        """FzfError is raised when the fzf binary is missing."""
        fake_tty = MagicMock()
        with patch("builtins.open", return_value=fake_tty), \
             patch("subprocess.Popen", side_effect=FileNotFoundError):
            try:
                run_fzf([self._APP])
                assert False, "Expected FzfError"
            except FzfError as exc:
                assert "fzf not found" in str(exc)

    def test_raises_on_timeout(self):
        """FzfError is raised when fzf times out."""
        import subprocess as _sp
        fake_tty = MagicMock()
        fake_proc = MagicMock()
        fake_proc.communicate.side_effect = [
            _sp.TimeoutExpired(cmd="fzf", timeout=300),
            ("", ""),
        ]
        with patch("builtins.open", return_value=fake_tty), \
             patch("subprocess.Popen", return_value=fake_proc):
            try:
                run_fzf([self._APP])
                assert False, "Expected FzfError"
            except FzfError as exc:
                assert "timed out" in str(exc)

    def test_returns_none_on_cancellation(self):
        """None (not FzfError) is returned when the user cancels (empty output)."""
        fake_tty = MagicMock()
        fake_proc = MagicMock()
        fake_proc.communicate.return_value = ("", "")
        with patch("builtins.open", return_value=fake_tty), \
             patch("subprocess.Popen", return_value=fake_proc):
            result = run_fzf([self._APP])
        assert result is None

