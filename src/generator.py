"""LLM response generation using Llama 3 via Ollama"""

import os
import ollama
from src.config import Config


SYSTEM_PROMPT = """You are a neutral, factual civic assistant that answers questions about Kenyan political campaign promises.

RULES:
1. If the context contains a 'FACT-CHECK TRACKER' entry, you MUST explicitly state the 'Status' (FULFILLED, IN PROGRESS, BROKEN, PARTIALLY FULFILLED).
2. Answer using ONLY the provided CONTEXT chunks.
3. If there is no fact-check data, explain what was promised.
4. Never invent facts. If the context has no information, say "I do not have sufficient evidence."
5. Write a COMPLETE, DETAILED answer. Cover every distinct promise or point present in the context. Do NOT abbreviate. Do NOT stop mid-thought.
6. Cite sources inline using [Source: Title, Year, Party].
7. LANGUAGE RULE: If the user asks in Kiswahili, reply in Kiswahili. If they ask in English, reply in English.
"""


def _num_threads() -> int:
    logical = os.cpu_count() or 4
    return max(2, min(6, logical // 2))


class Generator:
    def __init__(self):
        self.model = Config.LLM_MODEL
        self.options = {
            "temperature": Config.LLM_TEMPERATURE,
            "num_predict": 800,
            "num_ctx": 4096,
            "num_threads": _num_threads(),
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        }

    def build_prompt(self, query: str, context_chunks: list) -> str:
        context_chunks = context_chunks[:2]
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            meta = chunk["metadata"]
            citation = (
                f"[Source {i}: {meta.get('title', 'Unknown')}, "
                f"{meta.get('year', 'N/A')}, {meta.get('party', 'Unknown')}]"
            )
            context_parts.append(f"{citation}\n{chunk['text']}\n")
        context = "\n---\n".join(context_parts)
        return (
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {query}\n\n"
            "Provide a complete, grounded answer with inline citations. "
            "If evidence is insufficient, say so explicitly."
        )

    def generate(self, query: str, context_chunks: list) -> dict:
        if not context_chunks:
            return {
                "answer": "I do not have sufficient evidence in the corpus to answer this question.",
                "has_evidence": False,
            }
        prompt = self.build_prompt(query, context_chunks)
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                options=self.options,
                keep_alive="30m",
            )
            return {"answer": response["message"]["content"], "has_evidence": True}
        except Exception as e:
            return {"answer": f"Error generating response: {e}", "has_evidence": False}

    def generate_stream(self, query: str, context_chunks: list):
        """Yield text chunks as they're produced. Feed into st.write_stream()."""
        if not context_chunks:
            yield "I do not have sufficient evidence in the corpus to answer this question."
            return
        prompt = self.build_prompt(query, context_chunks)
        try:
            for part in ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                options=self.options,
                keep_alive="30m",
                stream=True,
            ):
                piece = part.get("message", {}).get("content", "")
                if piece:
                    yield piece
        except Exception as e:
            yield f"Error generating response: {e}"