"""Promise Filtering Module"""

import re
from src.config import Config


class PromiseFilter:
    def __init__(self):
        self.keywords = [k.lower() for k in Config.PROMISE_KEYWORDS]
        self.threshold = Config.PROMISE_THRESHOLD
        self.patterns = [
            re.compile(r'\b(?:we|our government|i)\s+(?:will|shall|promise|commit|pledge)\b', re.IGNORECASE),
            re.compile(r'\bensure\s+(?:that|the)\b', re.IGNORECASE),
            re.compile(r'\bguarantee\s+(?:that|the)\b', re.IGNORECASE),
            re.compile(r'\bdeliver\s+(?:on|the)\b', re.IGNORECASE),
            re.compile(r'\bintroduce\s+(?:a|the|new)\b', re.IGNORECASE),
            re.compile(r'\bcreate\s+(?:a|the|new|more)\b', re.IGNORECASE),
            re.compile(r'\bbuild\s+(?:a|the|new|more)\b', re.IGNORECASE),
            re.compile(r'\bexpand\s+(?:a|the|access)\b', re.IGNORECASE),
            re.compile(r'\bimplement\s+(?:a|the|new)\b', re.IGNORECASE),
        ]

    def score_chunk(self, text: str) -> tuple:
        text_lower = text.lower()
        matched = []
        score = 0.0

        for kw in self.keywords:
            if kw in text_lower:
                matched.append(kw)
                score += 0.15

        for pattern in self.patterns:
            if pattern.search(text):
                matched.append(pattern.pattern)
                score += 0.25

        if text_lower.count(" will ") > 2:
            score += 0.1
        if text_lower.count(" shall ") > 1:
            score += 0.1

        return min(score, 1.0), list(set(matched))

    def is_promise(self, text: str) -> tuple:
        score, matched = self.score_chunk(text)
        return score >= self.threshold, score, matched


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list:
    chunk_size = chunk_size or Config.CHUNK_SIZE
    overlap = overlap or Config.CHUNK_OVERLAP

    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk.split()) > 20:
            chunks.append(chunk)

    return chunks