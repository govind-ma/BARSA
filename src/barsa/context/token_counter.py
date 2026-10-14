"""Token counting abstraction and implementations for the Barsa Smart Context Engine."""

import re
from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenCounter(Protocol):
    """Protocol for counting or estimating tokens in arbitrary text."""

    def count(self, text: str) -> int:
        """Count or estimate the number of tokens in the given text."""
        ...

    @property
    def name(self) -> str:
        """Name of the tokenizer."""
        ...

    @property
    def is_exact(self) -> bool:
        """Whether this tokenizer produces exact counts for the target model."""
        ...

    @property
    def estimation_method(self) -> str:
        """Explanation of the estimation method used."""
        ...


class HeuristicTokenCounter:
    """Fast, robust multilingual tokenizer estimation.

    Estimates token counts using a blend of character-length ratios,
    whitespace-delimited word counts, punctuation boundaries, and JSON structural overhead.
    Does not depend on external C-extensions.
    """

    def __init__(self, name: str = "heuristic-multilingual-v1") -> None:
        self._name = name
        # Precompiled regex for words and CJK / non-Latin characters
        self._cjk_regex = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]")

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_exact(self) -> bool:
        return False

    @property
    def estimation_method(self) -> str:
        return "heuristic_char_word_ratio_v1"

    def count(self, text: str) -> int:
        if not text:
            return 0

        # Non-ASCII / CJK characters typically consume ~1 to 2 tokens per character
        cjk_chars = len(self._cjk_regex.findall(text))
        ascii_chars = len(text) - cjk_chars

        # Standard Latin / ASCII text in code and JSON is ~3.7 - 4.0 chars per token
        # Plus word boundaries and punctuation
        words = len(text.split())
        char_est = int(ascii_chars / 3.8)
        word_est = int(words * 1.25)

        # CJK characters are roughly 1.3 tokens each on BPE tokenizers
        cjk_est = int(cjk_chars * 1.3)

        # Weighted blend provides stable approximation across both prose and JSON
        base = max(char_est, word_est) + cjk_est
        return max(1, base)


class TiktokenTokenCounter:
    """Exact BPE tokenizer using the optional tiktoken library."""

    def __init__(self, model_or_encoding: str = "cl100k_base") -> None:
        import tiktoken

        self._encoding_name = model_or_encoding
        try:
            self._enc = tiktoken.encoding_for_model(model_or_encoding)
            self._name = f"tiktoken-model-{model_or_encoding}"
        except KeyError:
            self._enc = tiktoken.get_encoding(model_or_encoding)
            self._name = f"tiktoken-enc-{model_or_encoding}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_exact(self) -> bool:
        return True

    @property
    def estimation_method(self) -> str:
        return f"exact_bpe_tiktoken_{self._encoding_name}"

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._enc.encode(text, disallowed_special=()))


class ExactMockTokenCounter:
    """Deterministic token counter for unit testing and reproducible benchmarks."""

    def __init__(self, divisor: int = 4, name: str = "mock-exact-4chars") -> None:
        self.divisor = divisor
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_exact(self) -> bool:
        return True

    @property
    def estimation_method(self) -> str:
        return f"mock_exact_every_{self.divisor}_chars"

    def count(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // self.divisor)


def get_token_counter(
    target_model: str | None = None,
    force_heuristic: bool = False,
) -> TokenCounter:
    """Factory to acquire the best available token counter.

    Tries to use TiktokenTokenCounter if tiktoken is installed and not forced heuristic,
    otherwise cleanly falls back to HeuristicTokenCounter.
    """
    if not force_heuristic:
        try:
            enc = target_model or "cl100k_base"
            return TiktokenTokenCounter(enc)
        except (ImportError, Exception):
            pass

    name = f"heuristic-{target_model}" if target_model else "heuristic-cl100k-approx"
    return HeuristicTokenCounter(name=name)
