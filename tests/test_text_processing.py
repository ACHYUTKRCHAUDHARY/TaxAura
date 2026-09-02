from aura.services.text_processing import split_text


def test_split_text_keeps_overlap_and_content() -> None:
    chunks = split_text("a" * 2_000, chunk_size=1_000, overlap=100)
    assert len(chunks) == 3
    assert all(len(chunk) <= 1_000 for chunk in chunks)


def test_split_text_returns_empty_for_whitespace() -> None:
    assert split_text("   \n\t") == []
