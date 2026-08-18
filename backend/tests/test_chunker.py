"""Chunker properties.

The tests that matter here are not "does it produce chunks" but "does it lose
anything" and "can a chunk exceed what the encoder will actually read". Both
failure modes are silent in production: an oversized chunk is truncated during
embedding without an error, and a dropped tail simply never becomes searchable.
"""

import pytest

from app.config import get_settings
from app.rag.chunker import chunk_text
from app.rag.embedder import count_tokens

SETTINGS = get_settings()

POLICY = (
    "Returns are accepted within 30 days of delivery. "
    "Items must be unworn and have their original tags attached. "
    "Sale items are final and cannot be returned or exchanged. "
    "Refunds are issued to the original payment method within 5-7 business days. "
)


def _words(text: str) -> list[str]:
    return text.split()


class TestSizing:
    def test_no_chunk_exceeds_the_encoder_ceiling(self):
        chunks = chunk_text(POLICY * 40)
        assert chunks
        oversized = [c for c in chunks if c.tokens > SETTINGS.embed_max_tokens]
        assert not oversized, f"{len(oversized)} chunk(s) would be truncated during embedding"

    def test_reported_token_count_is_accurate(self):
        for c in chunk_text(POLICY * 10):
            assert c.tokens == count_tokens(c.content)

    def test_rejects_a_budget_above_the_model_ceiling(self):
        with pytest.raises(ValueError, match="silently truncated"):
            chunk_text(POLICY, max_tokens=SETTINGS.embed_max_tokens + 1)

    def test_rejects_overlap_larger_than_the_chunk(self):
        with pytest.raises(ValueError, match="smaller than"):
            chunk_text(POLICY, max_tokens=100, overlap=100)


class TestNothingIsLost:
    def test_every_word_survives_chunking(self):
        doc = POLICY * 30
        joined = " ".join(c.content for c in chunk_text(doc))
        missing = [w for w in set(_words(doc)) if w not in joined]
        assert not missing, f"words dropped: {missing[:5]}"

    def test_a_document_longer_than_the_encoder_limit_is_fully_covered(self):
        """The regression this file exists for.

        The embedding tokenizer truncates at 512, so measuring with it capped
        every document at 512 tokens and the splitter dropped everything past
        the first chunk. A 3000-token document must produce many chunks.
        """
        doc = "word " * 3000
        assert count_tokens(doc) > 3000 * 0.9, "counting tokenizer is truncating again"
        chunks = chunk_text(doc)
        assert len(chunks) >= 7, f"expected ~8 chunks for 3000 tokens, got {len(chunks)}"

    def test_a_single_oversized_sentence_is_split_not_dropped(self):
        sentence = "alpha " * 1200  # no terminator anywhere
        chunks = chunk_text(sentence)
        assert len(chunks) > 1
        assert all(c.tokens <= SETTINGS.embed_max_tokens for c in chunks)


class TestBoundaries:
    def test_overlap_carries_context_across_a_boundary(self):
        chunks = chunk_text(POLICY * 30)
        assert len(chunks) > 1
        tail = chunks[0].content[-40:]
        assert tail in chunks[1].content, "no overlap between consecutive chunks"

    def test_chunks_start_at_a_sentence(self):
        for c in chunk_text(POLICY * 20):
            assert c.content[0].isupper() or c.content[0].isdigit()

    def test_ordinals_are_contiguous_from_zero(self):
        chunks = chunk_text(POLICY * 25)
        assert [c.ordinal for c in chunks] == list(range(len(chunks)))


class TestEdgeCases:
    @pytest.mark.parametrize("text", ["", "   ", "\n\n\t "])
    def test_blank_input_yields_nothing(self, text):
        assert chunk_text(text) == []

    def test_a_short_document_is_one_chunk(self):
        chunks = chunk_text("Returns take 30 days.")
        assert len(chunks) == 1
        assert chunks[0].content == "Returns take 30 days."
