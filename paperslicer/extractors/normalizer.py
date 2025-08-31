class TextNormalizer:
    """Very simple whitespace/Unicode normalizer placeholder."""

    def normalize(self, text: str) -> str:
        if not text:
            return ""
        # Collapse whitespace and strip
        return " ".join(text.split())
