"""LLM response generation using Llama 3 via Ollama"""

import ollama
from src.config import Config


SYSTEM_PROMPT = """You are a neutral, factual assistant that answers questions about Kenyan political campaign promises.

RULES:
1. Answer ONLY using the provided context chunks.
2. If the context does not contain enough information, respond with: "I do not have sufficient evidence in the corpus to answer this question."
3. NEVER invent facts, promises, or statistics.
4. Cite sources inline using the format [Source: Title, Year, Party].
5. Be neutral - do not express opinions about any party or politician.
6. Keep answers concise (2-4 sentences).
"""


class Generator:
    def __init__(self):
        self.model = Config.LLM_MODEL

    def build_prompt(self, query: str, context_chunks: list) -> str:
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            meta = chunk["metadata"]
            citation = f"[Source {i}: {meta.get('title', 'Unknown')}, {meta.get('year', 'N/A')}, {meta.get('party', 'Unknown')}]"
            context_parts.append(f"{citation}\n{chunk['text']}\n")

        context = "\n---\n".join(context_parts)

        prompt = f"""CONTEXT:
{context}

QUESTION: {query}

Provide a grounded answer with inline citations. If evidence is insufficient, say so explicitly."""

        return prompt

    def generate(self, query: str, context_chunks: list) -> dict:
        if not context_chunks:
            return {
                "answer": "I do not have sufficient evidence in the corpus to answer this question.",
                "has_evidence": False
            }

        prompt = self.build_prompt(query, context_chunks)

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": Config.LLM_TEMPERATURE,
                    "num_predict": Config.LLM_MAX_TOKENS
                }
            )
            answer = response["message"]["content"]
            return {"answer": answer, "has_evidence": True}
        except Exception as e:
            return {
                "answer": f"Error generating response: {e}",
                "has_evidence": False
            }