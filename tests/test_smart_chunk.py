"""
RAG-03: sentence/structure-aware chunking tests for
KnowledgeBase.smart_chunk().

Every test constructs `kb = object.__new__(KnowledgeBase)` to bypass
`__init__`/model loading entirely — smart_chunk() reads no `self.*`
attributes, only its `text`/`chunk_size`/`overlap` parameters — mirroring
tests/test_engine_concurrency.py's bare-instance construction pattern.

Relies on tests/conftest.py's session-wide pypdf/docx/rank_bm25 stub
registration so `from src.core.knowledge import KnowledgeBase` succeeds on
this machine (those three packages are pinned in requirements.txt but not
installed locally).
"""

import sys
from pathlib import Path

# Add project root to sys.path (mirrors tests/test_engine_concurrency.py).
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from src.core.knowledge import KnowledgeBase  # noqa: E402
from underthesea import word_tokenize  # noqa: E402


def _kb():
    return object.__new__(KnowledgeBase)


def test_no_chunk_boundary_splits_a_sentence():
    # >=6 short Vietnamese sentences (5-8 words each) across 2 paragraphs.
    # Total word count (44) clearly exceeds chunk_size=15.
    paragraph_1_sentences = [
        "Con meo ngoi tren mai nha cao.",
        "Con cho chay theo con meo do.",
        "Troi mua rat to vao buoi chieu.",
    ]
    paragraph_2_sentences = [
        "Nguoi dan mang du ra duong pho.",
        "Cac em nho di hoc rat vui.",
        "Thay giao giang bai rat hay va de hieu.",
    ]
    all_sentences = paragraph_1_sentences + paragraph_2_sentences
    text = (
        " ".join(paragraph_1_sentences)
        + "\n\n"
        + " ".join(paragraph_2_sentences)
    )

    kb = _kb()
    chunks = kb.smart_chunk(text, chunk_size=15, overlap=4)

    assert len(chunks) >= 2, f"Expected >=2 chunks, got {len(chunks)}: {chunks}"

    for sentence in all_sentences:
        assert any(sentence in chunk for chunk in chunks), (
            f"Sentence {sentence!r} does not appear verbatim as a substring "
            f"inside any returned chunk — a chunk boundary split it. "
            f"Chunks: {chunks}"
        )


def test_short_text_returns_single_chunk():
    sentence = "Con meo rat de thuong."  # 5 words, well under default chunk_size=150

    kb = _kb()
    chunks = kb.smart_chunk(sentence)

    assert len(chunks) == 1, f"Expected exactly 1 chunk, got {len(chunks)}: {chunks}"
    assert chunks[0].strip() == sentence.strip(), (
        f"Single-sentence chunk text changed unexpectedly: {chunks[0]!r} "
        f"!= {sentence!r}"
    )


def test_overlap_carries_a_trailing_sentence_into_the_next_chunk():
    s1 = "Meo con thich choi voi bong len."  # 8 words
    s2 = "No rat de thuong."  # 5 words -- fits within overlap=5
    s3 = "Cho con lai thich chay nhay ngoai san rong."  # 8 words
    text = " ".join((s1, s2, s3))

    kb = _kb()
    chunks = kb.smart_chunk(text, chunk_size=15, overlap=5)

    assert len(chunks) >= 2, f"Expected >=2 chunks, got {len(chunks)}: {chunks}"

    tail_sentences_of_first_chunk = [
        s for s in (s1, s2, s3) if s in chunks[0]
    ]
    carried = [s for s in tail_sentences_of_first_chunk if s in chunks[1]]
    assert carried, (
        "Expected at least one sentence from chunks[0]'s tail to also "
        f"appear in chunks[1]'s head (overlap continuity). Chunks: {chunks}"
    )


def test_oversized_single_sentence_falls_back_to_word_slicing():
    # One sentence with no internal terminal punctuation, so
    # underthesea.sent_tokenize() treats the whole string as a single
    # sentence, built from >=40 space-separated placeholder word tokens.
    text = " ".join(f"tu{i}" for i in range(1, 46))  # 45 placeholder tokens

    kb = _kb()
    chunks = kb.smart_chunk(text, chunk_size=10, overlap=2)

    assert len(chunks) >= 4, f"Expected >=4 chunks, got {len(chunks)}: {chunks}"
    for chunk in chunks:
        chunk_word_count = len(word_tokenize(chunk))
        assert chunk_word_count <= 10, (
            f"Chunk {chunk!r} has {chunk_word_count} words, exceeding "
            f"chunk_size=10 -- the oversized-single-sentence fallback did "
            f"not bound its output."
        )
