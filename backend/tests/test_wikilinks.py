from app.services.wikilinks import Link, extract_links, normalize_title, strip_code


class TestStripCode:
    def test_fenced_block_blanks_content(self) -> None:
        text = "before\n```python\ncode [[here]]\n```\nafter"
        result = strip_code(text)
        assert "[[here]]" not in result
        assert len(result) == len(text)
        assert result.count("\n") == text.count("\n")

    def test_inline_code_blanks_content(self) -> None:
        text = "before `inline [[code]]` after"
        result = strip_code(text)
        assert "[[code]]" not in result
        assert len(result) == len(text)

    def test_text_outside_code_untouched(self) -> None:
        text = "prefix\n```\nblanked [[link]]\n```\nsuffix"
        result = strip_code(text)
        assert result.startswith("prefix\n")
        assert result.endswith("\nsuffix")

    def test_fenced_block_then_inline_code_both_stripped(self) -> None:
        text = "```\nfenced [[one]]\n```\nsome text `inline [[two]]` end"
        result = strip_code(text)
        assert "[[one]]" not in result
        assert "[[two]]" not in result
        assert len(result) == len(text)


class TestExtractLinks:
    def test_simple_link(self) -> None:
        links = extract_links("[[A]]")
        assert links == [Link(raw="A", anchor=None, alias=None, norm="a")]

    def test_link_with_alias(self) -> None:
        links = extract_links("[[A|alias text]]")
        assert links[0].raw == "A"
        assert links[0].alias == "alias text"
        assert links[0].anchor is None

    def test_link_with_anchor(self) -> None:
        links = extract_links("[[A#heading]]")
        assert links[0].raw == "A"
        assert links[0].anchor == "heading"
        assert links[0].alias is None

    def test_link_with_anchor_and_alias(self) -> None:
        links = extract_links("[[A#heading|alias]]")
        assert links[0].raw == "A"
        assert links[0].anchor == "heading"
        assert links[0].alias == "alias"

    def test_link_with_spaces_in_target(self) -> None:
        links = extract_links("[[a b c]]")
        assert links[0].raw == "a b c"

    def test_two_links_in_order(self) -> None:
        links = extract_links("See [[First]] and also [[Second|second one]].")
        assert len(links) == 2
        assert links[0].raw == "First"
        assert links[1].raw == "Second"
        assert links[1].alias == "second one"

    def test_fenced_code_link_excluded(self) -> None:
        body = "```\n[[Not A Link]]\n```\nReal text [[Real Link]] here"
        links = extract_links(body)
        assert len(links) == 1
        assert links[0].raw == "Real Link"

    def test_inline_code_link_excluded(self) -> None:
        body = "some `[[Also Not A Link]]` text and [[Real Link]]"
        links = extract_links(body)
        assert len(links) == 1
        assert links[0].raw == "Real Link"

    def test_no_links(self) -> None:
        assert extract_links("no links here") == []

    def test_empty_target_not_extracted(self) -> None:
        assert extract_links("[[]]") == []

    def test_malformed_unclosed_link(self) -> None:
        assert extract_links("[[Foo") == []


class TestNormalizeTitle:
    def test_extension_and_whitespace_normalize_equal(self) -> None:
        a = normalize_title("Foo Bar.md")
        b = normalize_title("  foo   bar  ")
        assert a == b
        assert a == "foo bar"

    def test_case_insensitive(self) -> None:
        assert (
            normalize_title("MixedCase")
            == normalize_title("mixedcase")
            == normalize_title("MIXEDCASE")
        )

    def test_extension_case_insensitive(self) -> None:
        assert normalize_title("Trailing.MD") == "trailing"
