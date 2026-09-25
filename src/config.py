"""Configuration for the RAG chatbot"""

class Config:
    # Embedding model
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION = 384

    # LLM
    LLM_MODEL = "llama3:8b"
    LLM_TEMPERATURE = 0.1
    LLM_MAX_TOKENS = 512

    # Chunking
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50

    # Retrieval
    TOP_K = 5
    SIMILARITY_THRESHOLD = 0.5

    # Promise Filtering
    PROMISE_THRESHOLD = 0.3
    PROMISE_KEYWORDS = [
        "promise", "commit", "ensure", "guarantee", "pledge",
        "will", "shall", "we will", "our government will",
        "we commit to", "we shall", "we promise",
        "ensure that", "guarantee that", "deliver", "provide",
        "introduce", "create", "build", "expand", "implement"
    ]

    # Paths (Windows-specific)
    DATA_DIR = r"D:\Kenyan RAG Chatbot\data\documents"
    CHROMA_DIR = r"D:\Kenyan RAG Chatbot\data\chroma_db"
    COLLECTION_NAME = "kenyan_promises"