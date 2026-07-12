class RecursiveTextSplitter:
    """Recursively splits a text into smaller segments.

    Based on character length and overlap.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] | None = None,
    ) -> None:
        """Initializes the text splitter.

        Args:
            chunk_size: The maximum size of each chunk in characters.
            chunk_overlap: The character overlap between consecutive chunks.
            separators: Optional list of separator characters. Defaults to hierarchy.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = max(0, min(chunk_overlap, chunk_size - 1))
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def split_text(self, text: str) -> list[str]:
        """Splits the text input using the recursively applied separators list.

        Args:
            text: The raw string content.

        Returns:
            list[str]: The parsed text chunks.
        """
        return self._split(text, self.separators)

    def _split(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            # Direct character slicing fallback
            chunks = []
            start = 0
            while start < len(text):
                chunks.append(text[start : start + self.chunk_size])
                start += self.chunk_size - self.chunk_overlap
                if start >= len(text) or self.chunk_size <= self.chunk_overlap:
                    break
            return chunks

        separator = separators[0]
        next_separators = separators[1:]

        # Split using the current separator
        parts = text.split(separator) if separator else list(text)

        chunks = []
        current_parts: list[str] = []
        current_len = 0

        for part in parts:
            part_len = len(part)

            # If a single part exceeds chunk_size, split recursively
            if part_len > self.chunk_size:
                if current_parts:
                    chunks.append(separator.join(current_parts))
                    current_parts = []
                    current_len = 0
                chunks.extend(self._split(part, next_separators))
            else:
                # Calculate added length including separator if not first element
                added_len = part_len + (len(separator) if current_parts else 0)
                if current_len + added_len <= self.chunk_size:
                    current_parts.append(part)
                    current_len += added_len
                else:
                    if current_parts:
                        chunks.append(separator.join(current_parts))

                    # Assemble overlaps by walking backwards
                    overlap_parts: list[str] = []
                    overlap_len = 0
                    for p in reversed(current_parts):
                        p_len = len(p) + (len(separator) if overlap_parts else 0)
                        if overlap_len + p_len <= self.chunk_overlap:
                            overlap_parts.insert(0, p)
                            overlap_len += p_len
                        else:
                            break

                    current_parts = [*overlap_parts, part]
                    current_len = (
                        overlap_len
                        + part_len
                        + (len(separator) if overlap_parts else 0)
                    )

        if current_parts:
            chunks.append(separator.join(current_parts))

        return chunks
