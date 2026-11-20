"""The command line, exercised as the reader runs it: one test per promise the README makes."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "prompter"
SCRIPT_TEXT = "# Episode\n\nHello **there**. Second sentence.\n"


class Cli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("PROMPTER_")}
        self.env.update(HOME=str(self.dir), XDG_DATA_HOME=str(self.dir / "data"),
                        XDG_CONFIG_HOME=str(self.dir / "config"))
        self.config_dir = self.dir / "config" / "prompter"
        self.config_dir.mkdir(parents=True)
        self.script = self.write(SCRIPT_TEXT)

    def tearDown(self):
        self._tmp.cleanup()

    # helpers

    def write(self, text: str, name: str = "episode.md") -> Path:
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def config(self, cfg) -> None:
        (self.config_dir / "config.json").write_text(
            cfg if isinstance(cfg, str) else json.dumps(cfg), encoding="utf-8")

    def run_cli(self, *args: str, env: dict | None = None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                              env={**self.env, **(env or {})}, timeout=60, check=False)

    def page(self, name: str = "episode.html") -> str:
        return (self.dir / "data" / "prompter" / name).read_text(encoding="utf-8")

    def assert_clean_failure(self, result, message: str) -> None:
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    # building the page

    def test_builds_the_page_and_reports_the_duration(self):
        result = self.run_cli(str(self.script), "--no-open")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Page:", result.stdout)
        self.assertIn("4 words", result.stdout)
        self.assertIn(">Hello there.</span>", self.page())
        self.assertIn(">Second sentence.</span>", self.page())

    def test_no_arguments_asks_for_a_script(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("a script is required", result.stderr)

    def test_text_writes_the_cleaned_script_next_to_it(self):
        result = self.run_cli(str(self.script), "--no-open", "--text")
        self.assertEqual(result.returncode, 0, result.stderr)
        cleaned = (self.dir / "episode.prompter.txt").read_text(encoding="utf-8")
        self.assertEqual(cleaned, "Hello there.\nSecond sentence.\n")

    def test_extra_browser_flags_after_a_double_dash_are_not_parsed(self):
        result = self.run_cli(str(self.script), "--no-open", "--", "--kiosk", "--mute-audio")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_script_says_so(self):
        self.write("# Title\n\n## Part\n\n[Cue]\n")
        result = self.run_cli(str(self.script), "--no-open")
        self.assert_clean_failure(result, "Nothing to read in")

    # a readable error instead of a traceback

    def test_missing_file(self):
        result = self.run_cli(str(self.dir / "nope.md"), "--no-open")
        self.assert_clean_failure(result, "no such file")

    def test_directory(self):
        result = self.run_cli(str(self.dir), "--no-open")
        self.assert_clean_failure(result, "is a directory")

    def test_not_utf8(self):
        (self.dir / "latin.md").write_bytes(b"caf\xe9 au lait")
        result = self.run_cli(str(self.dir / "latin.md"), "--no-open")
        self.assert_clean_failure(result, "is not UTF-8 text")

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ignores file permissions")
    def test_unwritable_text_output(self):
        folder = self.dir / "ro"
        folder.mkdir()
        script = folder / "read.md"
        script.write_text("Words.\n", encoding="utf-8")
        folder.chmod(0o555)
        try:
            result = self.run_cli(str(script), "--no-open", "--text")
        finally:
            folder.chmod(0o755)
        self.assert_clean_failure(result, "cannot write")

    # numbers are validated by name

    def test_speed_zero_is_rejected_not_silently_ignored(self):
        result = self.run_cli(str(self.script), "--no-open", "--wpm", "0")
        self.assert_clean_failure(result, "between 20 and 600")

    def test_negative_speed_is_rejected(self):
        result = self.run_cli(str(self.script), "--no-open", "--wpm", "-50")
        self.assert_clean_failure(result, "between 20 and 600")

    def test_non_numeric_speed_is_rejected(self):
        result = self.run_cli(str(self.script), "--no-open", "--wpm", "fast")
        self.assert_clean_failure(result, "must be an integer")

    def test_text_size_out_of_range_is_rejected(self):
        result = self.run_cli(str(self.script), "--no-open", "--size", "999")
        self.assert_clean_failure(result, "between 28 and 140")

    def test_speed_and_size_reach_the_page(self):
        result = self.run_cli(str(self.script), "--no-open", "--wpm", "200", "--size", "64")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("200 words/min", result.stdout)
        page = self.page()
        self.assertIn("WPM0=200", page)
        self.assertIn("SIZE0=64", page)

    # transcription servers

    def test_transcription_url_without_a_scheme_is_rejected(self):
        result = self.run_cli(str(self.script), "--no-open", "--stt", "localhost:8097")
        self.assert_clean_failure(result, "not a ws:// or wss:// URL")

    def test_transcription_url_reaches_the_page(self):
        result = self.run_cli(str(self.script), "--no-open", "--stt", "ws://127.0.0.1:9/live")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ws://127.0.0.1:9/live", self.page())

    # configuration

    def test_config_sets_speed_size_language_and_narrow(self):
        self.config({"wpm": 130, "size": 72, "lang": "fr", "narrow": True})
        result = self.run_cli(str(self.script), "--no-open")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Page :", result.stdout)
        page = self.page()
        self.assertIn('<html lang="fr">', page)
        self.assertIn("WPMDEF=130", page)
        self.assertIn("SIZEDEF=72", page)
        self.assertIn("NARROW0=true", page)

    def test_the_command_line_still_wins_over_the_config(self):
        self.config({"wpm": 130, "size": 72})
        result = self.run_cli(str(self.script), "--no-open", "--wpm", "180")
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.page()
        self.assertIn("WPM0=180", page)
        self.assertIn("WPMDEF=130", page)

    def test_wrong_config_values_are_reported_and_ignored(self):
        self.config({"wpm": "fast", "size": True, "narrow": "yes"})
        result = self.run_cli(str(self.script), "--no-open")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("wpm='fast' ignored", result.stderr)
        self.assertIn("size=True ignored", result.stderr)
        self.assertIn("narrow='yes' ignored", result.stderr)
        self.assertIn("WPMDEF=150", self.page())

    def test_broken_config_file_is_reported_and_ignored(self):
        self.config("{oops")
        result = self.run_cli(str(self.script), "--no-open")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ignored", result.stderr)

    def test_bad_transcription_entry_in_the_config_is_skipped(self):
        self.config({"stt": ["http://nope:1/x", "ws://127.0.0.1:9/live"]})
        result = self.run_cli(str(self.script), "--no-open")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ignored", result.stderr)
        self.assertIn('STT=["ws://127.0.0.1:9/live"]', self.page())

    def test_unknown_language_in_the_environment_falls_back_to_english(self):
        result = self.run_cli(str(self.script), "--no-open", env={"PROMPTER_LANG": "de"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not supported", result.stderr)
        self.assertIn('<html lang="en">', self.page())

    # the small commands

    def test_version(self):
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertRegex(result.stdout.strip(), r"^prompter \d+\.\d+\.\d+$")

    def test_list_screens_does_not_need_a_script(self):
        result = self.run_cli("--list-screens")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip(), "expected a report or the no-monitor message")


if __name__ == "__main__":
    unittest.main()
