from bot.config import WormholeConfig
import re

class ContentFiltering:
    def __init__(self, config: WormholeConfig):
        self.config = config

    def is_content_allowed(self, content: str) -> bool:
        if not self.config.content_filter.enabled:
            return True

        content_lower = content.lower()
        for word in self.config.banned_words:
            if re.search(r'\b' + re.escape(word.lower()) + r'\b', content_lower):
                return False

        # TODO: LLM filtering

        return True

    def add_banned_word(self, word: str) -> None:
        if word not in self.config.banned_words:
            self.config.banned_words.append(word)

    def remove_banned_word(self, word: str) -> bool:
        if word in self.config.banned_words:
            self.config.banned_words.remove(word)
            return True
        return False

    def get_banned_words(self) -> list:
        return self.config.banned_words

    def set_filter_sensitivity(self, sensitivity: float) -> None:
        self.config.content_filter.sensitivity = max(0.0, min(1.0, sensitivity))