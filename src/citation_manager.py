"""Citation formatting and validation"""

import re


class CitationManager:
    @staticmethod
    def format_sources(retrieved_chunks: list) -> list:
        sources = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            meta = chunk["metadata"]
            sources.append({
                "id": i,
                "title": meta.get("title", "Unknown"),
                "party": meta.get("party", "Unknown"),
                "year": meta.get("year", "N/A"),
                "similarity": round(chunk["similarity"], 3),
                "preview": chunk["text"][:300] + "..."
            })
        return sources

    @staticmethod
    def extract_citations(answer: str) -> list:
        pattern = r'\[Source:\s*([^\]]+)\]'
        return re.findall(pattern, answer)