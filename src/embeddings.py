"""SBERT embedding generator"""

from sentence_transformers import SentenceTransformer
from src.config import Config


class EmbeddingGenerator:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            print("Loading SBERT model...")
            cls._model = SentenceTransformer(Config.EMBEDDING_MODEL)
        return cls._model

    @classmethod
    def embed(cls, texts):
        model = cls.get_model()
        if isinstance(texts, str):
            return model.encode([texts])[0].tolist()
        return model.encode(texts).tolist()