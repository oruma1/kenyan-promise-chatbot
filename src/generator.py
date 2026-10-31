"""LLM response generation using Llama 3 via Ollama"""

import ollama
from src.config import Config


SYSTEM_PROMPT = """You are a neutral, factual civic assistant that answers questions about Kenyan political campaign promises.

RULES:
1. Look at the CONTEXT. If there is a 'FACT-CHECK TRACKER' entry, you MUST state its status (FULFILLED, IN PROGRESS, BROKEN, PARTIALLY FULFILLED) prominently in your answer.
2. If there is no fact-check data, just explain what was promised based on the other context chunks.
3. If the user asks about a specific party (e.g., Jubilee), only use chunks from that party.
4. Never invent facts. If the context has no information, say "I do not have sufficient evidence."
5. Be strictly neutral.
6. Cite sources inline using [Source: Title, Year, Party].
7. LANGUAGE RULE: If the user asks a question in Kiswahili, you MUST reply in Kiswahili.
"""

class Generator:
    def __init__(self):
        self.model = Config.LLM_MODEL

    def build_prompt(self, query: str, context_chunks: list) -> str:
                # Only take the top 2 chunks to speed up CPU generation
        context_chunks = context_chunks[:2]
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
                    "num_predict": Config.LLM_MAX_TOKENS,
		"num_ctx": 1024 
                }
            )
            answer = response["message"]["content"]
            return {"answer": answer, "has_evidence": True}
        except Exception as e:
            return {
                "answer": f"Error generating response: {e}",
                "has_evidence": False
            }