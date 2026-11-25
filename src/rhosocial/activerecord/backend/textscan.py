# src/rhosocial/activerecord/backend/textscan.py
"""Character scanning for the short grammars the backend reads and validates.

Several layers here validate or read a small, closed piece of text: an
identifier, a declared type name, a precision group, WKT text, an ISO
duration, or the name Python puts between quotes in a ``TypeError`` message.
Each of those used to be a regular expression. This module answers the same
questions with explicit character scans, so the source tree carries no
``re`` dependency and the accepted grammar is readable as code rather than
reconstructed from a pattern.

Every predicate here describes a *character set* or a *whole-word* test and
nothing more. Callers that need a compound grammar (a qualified name, a type
name with a precision and array markers) compose these primitives in their
own module: the shape belongs to the caller, the character test lives here.
"""

from typing import List, Optional

#: The ASCII letters SQL identifiers are built from.
_LETTERS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")

#: The ASCII digits an explicit ``[0-9]`` class admits.
_DIGITS = frozenset("0123456789")

#: Letters, digits and underscore: the ``\w``-minus-quotes backbone of a name.
_NAME_CHARS = _LETTERS | _DIGITS | frozenset("_")


def _is_word_char(char: str) -> bool:
    r"""Whether *char* is a word character in the ``\b`` sense.

    ``\b`` is defined against ``\w``, which is Unicode alphanumerics plus
    underscore -- not the narrower ASCII set the character classes above use.
    """
    return char.isalnum() or char == "_"


def is_simple_name(text: str, extra: str = "", *, spaces: bool = False) -> bool:
    r"""Whether *text* is a non-empty run of name characters.

    The grammar is ``^[A-Za-z0-9_<extra>]+$``; when *spaces* is true any
    whitespace character is accepted as well, which is the
    ``[A-Za-z0-9_+\-.\s]`` spelling PRAGMA values and column type lists use.

    Args:
        text: The candidate.
        extra: Additional characters admitted anywhere in the run.
        spaces: Whether any whitespace character is admitted.

    Returns:
        True when every character of *text* is admitted and the text is
        non-empty.

    Raises:
        TypeError: *text* is not iterable as characters.
    """
    if not text:
        return False
    allowed = _NAME_CHARS | frozenset(extra)
    for char in text:
        if char not in allowed and not (spaces and char.isspace()):
            return False
    return True


def is_identifier(text: str, extra: str = "", *, spaces: bool = False) -> bool:
    """Whether *text* is a non-empty name that does not start with a digit.

    The grammar is ``^[A-Za-z_][A-Za-z0-9_<extra>]*$`` (whitespace admitted
    after the first character when *spaces* is true) -- the identifier shape
    collation, XML and extension names are checked against.

    Args:
        text: The candidate.
        extra: Additional characters admitted after the first character.
        spaces: Whether any whitespace character is admitted after the first
            character.

    Returns:
        True when *text* is a non-empty identifier under that grammar.
    """
    if not text:
        return False
    if text[0] not in _LETTERS and text[0] != "_":
        return False
    return is_simple_name(text, extra, spaces=spaces)


def leading_word(
    text: str,
    start: int = 0,
    *,
    digits: bool = True,
    extra: str = "",
) -> str:
    r"""The word beginning at *start*, or ``""`` when no word begins there.

    A word starts with a letter or an underscore and continues with letters,
    an underscore, digits (when *digits*), and any characters in *extra*. It
    is the run a ``^([A-Za-z_][A-Za-z0-9_]*)\b``-style anchored match reads,
    returned as text rather than as a match object.

    Args:
        text: Text to read from.
        start: Index the word must begin at; leading whitespace is not
            skipped, so ``start`` is where the first character must lie.
        digits: Whether digits continue the word.
        extra: Additional characters that continue the word.

    Returns:
        The word, or ``""`` when *start* is out of range or does not start
        one.
    """
    if start < 0 or start >= len(text):
        return ""
    first = text[start]
    if first not in _LETTERS and first != "_":
        return ""
    allowed = _LETTERS | frozenset("_") | frozenset(extra)
    if digits:
        allowed = allowed | _DIGITS
    index = start + 1
    while index < len(text) and text[index] in allowed:
        index += 1
    return text[start:index]


def split_dotted(text: str) -> List[str]:
    """Split a dotted path into its parts, stripping each part's whitespace.

    ``schema.name`` and ``a.b.c`` both read as one separator per dot; an
    empty part therefore means the path had a leading, trailing or doubled
    dot, which callers reject by checking each part.

    Args:
        text: The dotted path.

    Returns:
        One entry per dot-separated part.
    """
    return [part.strip() for part in text.split(".")]


def split_top_level(text: str, sep: str) -> List[str]:
    """Split *text* on *sep*, ignoring separators inside brackets.

    Parentheses, square brackets and braces nest; a separator at depth zero
    divides the text. Quotes are not tracked -- this serves the type and
    precision grammar, where a quoted separator cannot occur.

    Args:
        text: The text to split.
        sep: The single-character separator.

    Returns:
        The pieces, in order, trimmed neither of whitespace nor brackets.
    """
    parts: List[str] = []
    depth = 0
    piece_start = 0
    for index, char in enumerate(text):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            if depth:
                depth -= 1
        elif char == sep and depth == 0:
            parts.append(text[piece_start:index])
            piece_start = index + 1
    parts.append(text[piece_start:])
    return parts


def parenthesised(text: str) -> Optional[str]:
    """The contents of the first balanced ``(...)`` group in *text*.

    Scanning begins at the first ``(``; the returned text ends where the
    group that opened there closes. ``None`` means there is no such group,
    including a group that never closes.

    Args:
        text: Text to read from.

    Returns:
        The text between the first opening parenthesis and its matching
        closing one, or ``None``.
    """
    start = text.find("(")
    if start == -1:
        return None
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start + 1 : index]
    return None


def integer_runs(text: str) -> List[str]:
    r"""Every maximal run of decimal digits in *text*, in order.

    ``\d`` in a Unicode pattern matches decimal digits (Unicode category
    Nd), which is exactly what :meth:`str.isdecimal` recognises -- so a
    ``(10, 2)`` group yields ``["10", "2"]`` and ``VARCHAR(255)`` yields
    ``["255"]``.

    Args:
        text: Text to read from.

    Returns:
        One entry per run of digits, as written.
    """
    runs: List[str] = []
    run_start: Optional[int] = None
    for index, char in enumerate(text):
        if char.isdecimal():
            if run_start is None:
                run_start = index
        elif run_start is not None:
            runs.append(text[run_start:index])
            run_start = None
    if run_start is not None:
        runs.append(text[run_start:])
    return runs


def find_word(
    text: str,
    word: str,
    *,
    ignore_case: bool = False,
    start: int = 0,
) -> int:
    r"""Index of *word* in *text* where it stands as a whole word, else ``-1``.

    "Whole word" is the ``\bword\b`` test: the character before and after
    the occurrence must be absent or a non-word character. Occurrences that
    fail the boundary test are skipped, so a later valid one is still found.

    Args:
        text: Text to search.
        word: The word to look for.
        ignore_case: Whether case is folded before comparing.
        start: Index to begin searching at.

    Returns:
        The index of the first whole-word occurrence, or ``-1``.
    """
    if not word:
        return -1
    haystack = text.casefold() if ignore_case else text
    needle = word.casefold() if ignore_case else word
    index = haystack.find(needle, start)
    while index != -1:
        before_ok = index == 0 or not _is_word_char(haystack[index - 1])
        end = index + len(needle)
        after_ok = end == len(haystack) or not _is_word_char(haystack[end])
        if before_ok and after_ok:
            return index
        index = haystack.find(needle, index + 1)
    return -1


def has_word(text: str, word: str, *, ignore_case: bool = False) -> bool:
    """Whether *word* occurs in *text* as a whole word.

    Args:
        text: Text to search.
        word: The word to look for.
        ignore_case: Whether case is folded before comparing.

    Returns:
        True when at least one whole-word occurrence exists.
    """
    return find_word(text, word, ignore_case=ignore_case) != -1


def quoted_word_after(text: str, marker: str) -> Optional[str]:
    """The single quoted word following *marker*, or ``None``.

    Python spells an unexpected keyword argument as
    ``unexpected keyword argument 'name'``; this reads the ``name``. The
    word must be non-empty, made of word characters, and immediately closed
    by a single quote, as a ``word`` pattern followed by a quote requires.

    Args:
        text: Text to search.
        marker: The literal text that precedes the quoted word.

    Returns:
        The word between the quotes, or ``None`` when no occurrence of
        *marker* is followed by one.
    """
    search_from = 0
    while True:
        index = text.find(marker, search_from)
        if index == -1:
            return None
        word_start = index + len(marker)
        word_end = word_start
        while word_end < len(text) and _is_word_char(text[word_end]):
            word_end += 1
        if word_end > word_start and word_end < len(text) and text[word_end] == "'":
            return text[word_start:word_end]
        search_from = index + 1


__all__ = [
    "find_word",
    "has_word",
    "integer_runs",
    "is_identifier",
    "is_simple_name",
    "leading_word",
    "parenthesised",
    "quoted_word_after",
    "split_dotted",
    "split_top_level",
]
