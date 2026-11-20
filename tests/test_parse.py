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

    def test_initials_do_not_split(self):
        self.assertEqual(prompter.split_sentences("J. R. R. Tolkien wrote The Hobbit. It sold well."),
                         ["J. R. R. Tolkien wrote The Hobbit.", "It sold well."])

    def test_titles_do_not_split(self):
        self.assertEqual(prompter.split_sentences("Dr. Smith arrived early. He waited."),
                         ["Dr. Smith arrived early.", "He waited."])

    def test_latin_abbreviation_does_not_split(self):
        self.assertEqual(prompter.split_sentences("Bring tools, e.g. A hammer. Nails too."),
                         ["Bring tools, e.g. A hammer.", "Nails too."])

    def test_dotted_abbreviation_does_not_split(self):
        self.assertEqual(prompter.split_sentences("The U.S. Army moved. It was slow."),
                         ["The U.S. Army moved.", "It was slow."])

    def test_abbreviation_before_a_digit_does_not_split(self):
        self.assertEqual(prompter.split_sentences("Take a few, e.g. 3 hammers."),
                         ["Take a few, e.g. 3 hammers."])

    def test_closing_parenthesis_ends_sentence(self):
        self.assertEqual(prompter.split_sentences("He left (for good.) She stayed."),
                         ["He left (for good.)", "She stayed."])

    def test_closing_bracket_ends_sentence(self):
        self.assertEqual(prompter.split_sentences("He left [for good.] She stayed."),
                         ["He left [for good.]", "She stayed."])

    def test_ellipsis(self):
        self.assertEqual(prompter.split_sentences("Well... Maybe not."),
                         ["Well...", "Maybe not."])

    def test_accented_capital_starts_sentence(self):
        self.assertEqual(prompter.split_sentences("Il part. Évidemment."),
                         ["Il part.", "Évidemment."])

    def test_no_punctuation(self):
        self.assertEqual(prompter.split_sentences("Just one line without a stop"),
                         ["Just one line without a stop"])

    def test_empty(self):
        self.assertEqual(prompter.split_sentences(""), [])

    def test_strips_the_surrounding_spaces(self):
        self.assertEqual(prompter.split_sentences("  One.  "), ["One."])


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

    def test_ordered_list_markers(self):
        blocks = prompter.parse("1. First item\n2) Second item")
        self.assertEqual(blocks[0]["s"], ["First item Second item"])

    def test_html_comments_are_not_read(self):
        md = "<!-- reshoot this -->\n\nRead this.\n\nInline <!-- hidden --> text.\n"
        self.assertEqual(prompter.parse(md), [
            {"type": "p", "s": ["Read this."]},
            {"type": "p", "s": ["Inline text."]},
        ])

    def test_multiline_html_comment_is_not_read(self):
        md = "<!--\nnote to self\nsecond line\n-->\n\nRead this.\n"
        self.assertEqual(prompter.parse(md), [{"type": "p", "s": ["Read this."]}])

    def test_fenced_code_is_not_read(self):
        md = "Before.\n\n```python\nprint('x')\n```\n\nAfter.\n"
        self.assertEqual(prompter.parse(md), [
            {"type": "p", "s": ["Before."]},
            {"type": "p", "s": ["After."]},
        ])

    def test_tilde_fence_is_not_read(self):
        md = "Before.\n\n~~~\ncode\n~~~\n\nAfter.\n"
        self.assertEqual([b["s"] for b in prompter.parse(md)], [["Before."], ["After."]])

    def test_unclosed_fence_swallows_the_rest(self):
        md = "Before.\n\n```\ncode\n"
        self.assertEqual(prompter.parse(md), [{"type": "p", "s": ["Before."]}])

    def test_markdown_comment_spelling(self):
        self.assertEqual(prompter.parse("[//]: # (note)\n\nWords here.\n"),
                         [{"type": "p", "s": ["Words here."]}])

    def test_hashtag_word_is_not_a_heading(self):
        self.assertEqual(prompter.parse("#hashtag is not a heading"),
                         [{"type": "p", "s": ["#hashtag is not a heading"]}])

    def test_setext_heading_is_dropped(self):
        self.assertEqual(prompter.parse("Big Title\n=========\n\nBody."),
                         [{"type": "p", "s": ["Body."]}])

    def test_crlf_and_lf_give_the_same_blocks(self):
        md = "# T\r\n\r\nOne. Two.\r\n\r\n---\r\n\r\nThree.\r\n"
        self.assertEqual(prompter.parse(md), prompter.parse(md.replace("\r\n", "\n")))

    def test_cue_needs_the_whole_line(self):
        blocks = prompter.parse("[Intro] Some words here.")
        self.assertEqual(blocks, [{"type": "p", "s": ["[Intro] Some words here."]}])

    def test_underscored_cue(self):
        blocks = prompter.parse("One.\n\n__[B-roll]__\n\nTwo.")
        self.assertEqual(blocks, [
            {"type": "p", "s": ["One."]},
            {"type": "break"},
            {"type": "p", "s": ["Two."]},
        ])

    def test_leading_break_is_removed(self):
        self.assertEqual(prompter.parse("# Title\n\nWords."), [{"type": "p", "s": ["Words."]}])

    def test_images_links_and_code_marks_are_cleaned(self):
        md = "![shot](x.png) Read [the note](http://x) and `run this`."
        self.assertEqual(prompter.parse(md), [
            {"type": "p", "s": ["Read the note and run this."]},
        ])

    def test_empty_input(self):
        self.assertEqual(prompter.parse(""), [])
        self.assertEqual(prompter.parse("\n\n   \n"), [])

    def test_only_headings_and_cues(self):
        self.assertEqual(prompter.parse("# Title\n\n## Part\n\n[Cue]\n\n---\n"), [])

    def test_as_text_marks_sections(self):
        blocks = [{"type": "p", "s": ["One.", "Two."]}, {"type": "break"},
                  {"type": "p", "s": ["Three."]}]
        self.assertEqual(prompter.as_text(blocks), "One.\nTwo.\n\n• • •\n\nThree.\n")

    def test_count_words(self):
        blocks = [{"type": "p", "s": ["One two.", "Three."]}, {"type": "break"}]
        self.assertEqual(prompter.count_words(blocks), 3)


class Screens(unittest.TestCase):
    MONS = [{"conn": "eDP-1", "product": "LQ144", "primary": True},
            {"conn": "DP-1", "product": "ARZOPA", "primary": False}]

    def test_external_by_default(self):
        self.assertEqual(prompter.pick(self.MONS, None)["conn"], "DP-1")

    def test_by_model_name(self):
        self.assertEqual(prompter.pick(self.MONS, "arzopa")["conn"], "DP-1")

    def test_by_connector(self):
        self.assertEqual(prompter.pick(self.MONS, "DP-1")["conn"], "DP-1")

    def test_by_the_start_of_a_name(self):
        self.assertEqual(prompter.pick(self.MONS, "arz")["conn"], "DP-1")

    def test_an_internal_panel_is_still_addressable(self):
        self.assertEqual(prompter.pick(self.MONS, "eDP-1")["conn"], "eDP-1")

    def test_an_ambiguous_name_prefers_the_external_screen(self):
        # "dp" is a substring of both "edp-1" and "dp-1": the laptop panel must not win
        self.assertEqual(prompter.pick(self.MONS, "dp")["conn"], "DP-1")

    def test_unknown_screen(self):
        self.assertIsNone(prompter.pick(self.MONS, "HDMI-9"))

    def test_blank_name_falls_back_to_the_external_screen(self):
        self.assertEqual(prompter.pick(self.MONS, "  ")["conn"], "DP-1")

    def test_no_external(self):
        self.assertIsNone(prompter.pick(self.MONS[:1], None))

    def test_internal_connectors(self):
        self.assertTrue(prompter.is_internal("eDP-1"))
        self.assertTrue(prompter.is_internal("LVDS1"))
        self.assertFalse(prompter.is_internal("DP-1"))

    def test_describe_monitors(self):
        self.assertEqual(prompter.describe_monitors(self.MONS), "eDP-1 LQ144, DP-1 ARZOPA")


class Page(unittest.TestCase):
    BLOCKS = [{"type": "p", "s": ["A & B < C."]}, {"type": "break"},
              {"type": "p", "s": ["Second."]}]

    def test_escapes_the_script_text(self):
        page = prompter.build_html(self.BLOCKS, "t & t", "/x", "en", 150)
        self.assertIn("A &amp; B &lt; C.", page)
        self.assertIn("<title>Prompter · t &amp; t</title>", page)
        self.assertIn('<div class="brk">•&nbsp;•&nbsp;•</div>', page)

    def test_a_script_end_in_a_value_cannot_close_the_tag(self):
        page = prompter.build_html(self.BLOCKS, "t", "k", "en", 150,
                                   stt=['ws://x/"></script><script>alert(1)</script>'])
        self.assertNotIn("</script><script>", page)

    def test_speed_and_size_from_the_command_line_win(self):
        page = prompter.build_html(self.BLOCKS, "t", "k", "en", 140, size=64,
                                   wpm_default=130, size_default=72)
        self.assertIn("WPM0=140", page)
        self.assertIn("SIZE0=64", page)
        self.assertIn("WPMDEF=130", page)
        self.assertIn("SIZEDEF=72", page)

    def test_no_speed_set_keeps_the_javascript_default(self):
        page = prompter.build_html(self.BLOCKS, "t", "k", "en", None)
        self.assertIn("WPM0=0", page)
        self.assertIn("WPMDEF=150", page)
        self.assertIn("SIZE0=0", page)
        self.assertIn("SIZEDEF=54", page)

    def test_interface_language(self):
        page = prompter.build_html(self.BLOCKS, "t", "k", "fr", None)
        self.assertIn('<html lang="fr">', page)
        self.assertIn("mots/min", page)

    def test_stt_servers_reach_the_page(self):
        page = prompter.build_html(self.BLOCKS, "t", "k", "en", 150, stt=["ws://127.0.0.1:8097/x"])
        self.assertIn('STT=["ws://127.0.0.1:8097/x"]', page)


if __name__ == "__main__":
    unittest.main()
