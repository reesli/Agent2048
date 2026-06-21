"""Token counting utilities."""

import tiktoken


ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Return the number of tokens for a text string."""
    if not text:
        return 0
    return len(ENCODING.encode(text))
