import unittest
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

_path = str(Path(__file__).resolve().parent.parent / "prompter")
_loader = SourceFileLoader("prompter", _path)
prompter = module_from_spec(spec_from_loader("prompter", _loader))
_loader.exec_module(prompter)


class SplitSentences(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(prompter.split_sentences("One. Two! Three? Four"),
                         ["One.", "Two!", "Three?", "Four"])

    def test_no_split_inside_french_quotes(self):
        self.assertEqual(prompter.split_sentences("Il dit : « Non. Jamais. » Puis il part."),
                         ["Il dit : « Non. Jamais. »", "Puis il part."])

    def test_no_split_inside_double_quotes(self):
        self.assertEqual(prompter.split_sentences('He said "Stop. Now." Then he left.'),
                         ['He said "Stop. Now."', "Then he left."])

    def test_lowercase_after_period_stays(self):
        self.assertEqual(prompter.split_sentences("Version 2.5 is out. ok then"),
                         ["Version 2.5 is out. ok then"])

    def test_digit_starts_sentence(self):
        self.assertEqual(prompter.split_sentences("Line one. 3 weeks later."),
                         ["Line one.", "3 weeks later."])


class Parse(unittest.TestCase):
    def test_notes_headings_and_cues_removed(self):
        md = ("# Title\n\nNotes for me, not read aloud.\n\n---\n\n**[Intro]**\n\n"
              "Hello **there**. See [the doc](http://x).\n\n## Part 2\n\n[Cue]\n\nBye.\n")
        blocks = prompter.parse(md)
        self.assertEqual(blocks, [
            {"type": "p", "s": ["Hello there.", "See the doc."]},
            {"type": "break"},
            {"type": "p", "s": ["Bye."]},
        ])

    def test_late_rule_is_a_break_not_notes(self):
        md = "\n".join(["Line."] * 20) + "\n\n---\n\nAfter."
        blocks = prompter.parse(md)
        self.assertEqual(blocks[-2:], [{"type": "break"}, {"type": "p", "s": ["After."]}])
        self.assertEqual(prompter.count_words(blocks), 21)

    def test_lists_and_quotes_lose_markers(self):
        blocks = prompter.parse("- First item\n- Second item\n\n> Quoted line")
        self.assertEqual(blocks[0]["s"], ["First item Second item"])
        self.assertEqual(blocks[1]["s"], ["Quoted line"])


class Screens(unittest.TestCase):
    MONS = [{"conn": "eDP-1", "product": "LQ144", "primary": True},
            {"conn": "DP-1", "product": "ARZOPA", "primary": False}]

    def test_external_by_default(self):
        self.assertEqual(prompter.pick(self.MONS, None)["conn"], "DP-1")

    def test_by_model_name(self):
        self.assertEqual(prompter.pick(self.MONS, "arzopa")["conn"], "DP-1")

    def test_no_external(self):
        self.assertIsNone(prompter.pick(self.MONS[:1], None))


if __name__ == "__main__":
    unittest.main()
