import re


COMMON_ABBREVIATIONS = {
    "dr",
    "mr",
    "mrs",
    "ms",
    "prof",
    "sr",
    "jr",
    "st",
    "vs",
    "etc",
    "e.g",
    "i.e",
}
TRAILING_CLOSERS = "\"')]}"
LEADING_OPENERS = "\"'("

TARGET_CHUNK_WORDS = 180
MIN_CHUNK_WORDS = 120
MAX_CHUNK_WORDS = 260
HARD_MAX_CHUNK_WORDS = 320


def chunk_paragraphs(text: str) -> list[str]:
    chunks: list[str] = []
    current_parts: list[str] = []
    current_word_count = 0

    for paragraph in re.split(r"\n\s*\n", text):
        normalized_paragraph = paragraph.strip()
        if not normalized_paragraph:
            continue

        sentences = _split_sentences(normalized_paragraph) or [normalized_paragraph]

        for sentence in sentences:
            sentence_word_count = _count_words(sentence)

            if sentence_word_count >= HARD_MAX_CHUNK_WORDS:
                if current_parts:
                    chunks.append(_join_chunk_parts(current_parts))
                    current_parts = []
                    current_word_count = 0

                chunks.extend(_split_long_sentence(sentence))
                continue

            projected_word_count = current_word_count + sentence_word_count
            should_flush_before_append = (
                current_parts
                and projected_word_count > MAX_CHUNK_WORDS
                and current_word_count >= MIN_CHUNK_WORDS
            )

            if should_flush_before_append:
                chunks.append(_join_chunk_parts(current_parts))
                current_parts = []
                current_word_count = 0

            current_parts.append(sentence)
            current_word_count += sentence_word_count

            if current_word_count >= TARGET_CHUNK_WORDS:
                chunks.append(_join_chunk_parts(current_parts))
                current_parts = []
                current_word_count = 0

    if current_parts:
        chunks.append(_join_chunk_parts(current_parts))

    return chunks


def _split_sentences(paragraph: str) -> list[str]:
    sentences: list[str] = []
    start = 0
    index = 0

    while index < len(paragraph):
        if paragraph[index] not in ".!?":
            index += 1
            continue

        end = index + 1
        while end < len(paragraph) and paragraph[end] in TRAILING_CLOSERS:
            end += 1

        if not _is_sentence_boundary(paragraph, index, end):
            index += 1
            continue

        sentence = paragraph[start:end].strip()
        if sentence:
            sentences.append(sentence)
        start = _skip_whitespace(paragraph, end)
        index = start

    remainder = paragraph[start:].strip()
    if remainder:
        sentences.append(remainder)

    return sentences


def _split_long_sentence(sentence: str) -> list[str]:
    words = sentence.split()
    if len(words) <= HARD_MAX_CHUNK_WORDS:
        return [sentence.strip()]

    chunks: list[str] = []
    start_index = 0

    while start_index < len(words):
        end_index = min(start_index + MAX_CHUNK_WORDS, len(words))
        chunk_words = words[start_index:end_index]
        chunk_text = " ".join(chunk_words).strip()
        if chunk_text:
            chunks.append(chunk_text)
        start_index = end_index

    return chunks


def _join_chunk_parts(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part.strip()).strip()


def _count_words(text: str) -> int:
    return len(text.split())


def _is_sentence_boundary(paragraph: str, punctuation_index: int, end: int) -> bool:
    if _previous_token(paragraph, punctuation_index).lower() in COMMON_ABBREVIATIONS:
        return False

    if end >= len(paragraph):
        return True

    if not paragraph[end].isspace():
        return False

    next_index = _skip_whitespace(paragraph, end)
    if next_index >= len(paragraph):
        return True

    next_character = paragraph[next_index]
    return next_character.isupper() or next_character in LEADING_OPENERS


def _previous_token(paragraph: str, punctuation_index: int) -> str:
    start = punctuation_index - 1
    while start >= 0 and (
        paragraph[start].isalpha() or paragraph[start] in ".'"
    ):
        start -= 1
    return paragraph[start + 1 : punctuation_index]


def _skip_whitespace(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index
