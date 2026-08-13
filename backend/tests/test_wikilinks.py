from app.services.wikilinks import (
    Link,
    extract_links,
    is_linkable_title,
    normalize_title,
    rewrite_links,
    strip_code,
)


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


class TestRewriteLinks:
    def test_plain_link_retargeted(self) -> None:
        assert rewrite_links("See [[Old]] here", "old", "New") == "See [[New]] here"

    def test_alias_preserved(self) -> None:
        assert rewrite_links("[[Old|the alias]]", "old", "New") == "[[New|the alias]]"

    def test_anchor_preserved(self) -> None:
        assert rewrite_links("[[Old#Some Heading]]", "old", "New") == "[[New#Some Heading]]"

    def test_anchor_and_alias_preserved(self) -> None:
        assert rewrite_links("[[Old#H|a]]", "old", "New") == "[[New#H|a]]"

    def test_matches_via_normalized_title(self) -> None:
        assert rewrite_links("[[  old   title.md ]]", "old title", "New") == "[[New]]"

    def test_other_links_untouched(self) -> None:
        text = "[[Old]] and [[Unrelated]]"
        assert rewrite_links(text, "old", "New") == "[[New]] and [[Unrelated]]"

    def test_fenced_code_not_rewritten(self) -> None:
        text = "[[Old]]\n```\n[[Old]]\n```\n"
        assert rewrite_links(text, "old", "New") == "[[New]]\n```\n[[Old]]\n```\n"

    def test_inline_code_not_rewritten(self) -> None:
        text = "write `[[Old]]` to link [[Old]]"
        assert rewrite_links(text, "old", "New") == "write `[[Old]]` to link [[New]]"

    def test_no_match_returns_original(self) -> None:
        text = "nothing to see [[Other]]"
        assert rewrite_links(text, "old", "New") is text

    def test_repeated_links_all_rewritten(self) -> None:
        assert rewrite_links("[[Old]] [[Old]]", "old", "New") == "[[New]] [[New]]"

    def test_inline_code_inside_an_alias_survives(self) -> None:
        text = "[[Old Title|the `code` alias]]"
        assert rewrite_links(text, "old title", "New") == "[[New|the `code` alias]]"

    def test_inline_code_inside_an_anchor_survives(self) -> None:
        text = "[[Old#the `code` heading]]"
        assert rewrite_links(text, "old", "New") == "[[New#the `code` heading]]"

    def test_unlinkable_new_title_leaves_the_text_alone(self) -> None:
        text = "see [[Old]] here"
        for unsafe in ("C# notes", "foo]] bar", "a|b", "x[y", "  "):
            assert rewrite_links(text, "old", unsafe) is text


class TestIsLinkableTitle:
    def test_ordinary_titles_are_linkable(self) -> None:
        assert is_linkable_title("Nvidia AI capex")
        assert is_linkable_title("Café ÜBER 2024")

    def test_wikilink_syntax_characters_are_rejected(self) -> None:
        for unsafe in ("C# notes", "foo]] bar", "x[y", "a|b", "two\nlines", "crlf\r"):
            assert not is_linkable_title(unsafe)

    def test_blank_is_rejected(self) -> None:
        assert not is_linkable_title("   ")


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
