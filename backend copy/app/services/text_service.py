class TextService:
    def textify(self, transcript: list) -> str:
        """Convert transcript list to a single text string."""
        return " ".join(entry["text"] for entry in transcript if "text" in entry)