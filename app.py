"""Streamlit UI with role-based access control"""

import streamlit as st
import time
import pandas as pd

from src.retriever import Retriever
from src.generator import Generator
from src.citation_manager import CitationManager
from src.config import Config
from src.auth import authenticate, register_user, list_users, delete_user, ROLES
from src.evaluator import bm25_baseline, precision_at_k


st.set_page_config(
    page_title="Kenyan Political Promise Chatbot",
    page_icon="🇰🇪",
    layout="wide"
)


# --- Session state ---
for key, default in {
    "logged_in": False,
    "username": "",
    "role": "",
    "show_register": False,
    "feedback": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


@st.cache_resource
def get_components():
    return Retriever(), Generator()


# =========================================================================
# LOGIN / REGISTER SCREEN
# =========================================================================
def login_screen():
    st.title("🇰🇪 Kenyan Political Promise Chatbot")
    st.caption("Log in to continue")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if not st.session_state.show_register:
            st.subheader("Login")
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Log In", use_container_width=True)

                if submit:
                    ok, role = authenticate(username, password)
                    if ok:
                        st.session_state.logged_in = True
                        st.session_state.username = username.strip().lower()
                        st.session_state.role = role
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

            st.markdown("---")
            if st.button("Create New Account", use_container_width=True):
                st.session_state.show_register = True
                st.rerun()

            with st.expander("Default demo credentials"):
                st.code(
                    "admin     / admin123      → full access\n"
                    "evaluator / evaluator123  → chat + evaluation\n"
                    "citizen   / citizen123    → chat only"
                )

        else:
            st.subheader("Create Account")
            with st.form("register_form"):
                new_user = st.text_input("Username (min 3 chars)")
                new_pass = st.text_input("Password (min 6 chars)", type="password")
                confirm = st.text_input("Confirm password", type="password")
                role = st.selectbox(
                    "Account type",
                    options=["citizen", "evaluator"],
                    help="Admin accounts can only be created by an existing admin."
                )
                submit = st.form_submit_button("Register", use_container_width=True)

                if submit:
                    if new_pass != confirm:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg = register_user(new_user, new_pass, role)
                        if ok:
                            st.success(msg)
                            time.sleep(1)
                            st.session_state.show_register = False
                            st.rerun()
                        else:
                            st.error(msg)

            st.markdown("---")
            if st.button("Back to Login", use_container_width=True):
                st.session_state.show_register = False
                st.rerun()


# =========================================================================
# SHARED CHATBOT PANEL (used by all roles)
# =========================================================================
def chatbot_panel(top_k: int, show_chunks: bool):
    st.header("💬 Ask about political promises")

    try:
        retriever, generator = get_components()
        chunk_count = retriever.store.count()
    except Exception as e:
        st.error(f"Failed to initialize RAG components: {e}")
        return

    query = st.text_input(
        "Your question:",
        placeholder="e.g., What did the 2022 manifestos promise about healthcare?",
        key="chat_query"
    )

    if query:
        with st.spinner("Searching and generating..."):
            start = time.time()
            retrieved = retriever.retrieve(query, top_k=top_k)
            retrieval_time = time.time() - start

            has_evidence = retriever.has_sufficient_evidence(retrieved)
            filtered = [r for r in retrieved if r["similarity"] >= Config.SIMILARITY_THRESHOLD]

            start = time.time()
            result = generator.generate(query, filtered) if has_evidence else {
                "answer": "I do not have sufficient evidence in the corpus to answer this question.",
                "has_evidence": False
            }
            gen_time = time.time() - start

        st.markdown("### Answer")
        if result["has_evidence"]:
            st.success(result["answer"])
        else:
            st.warning(result["answer"])

        c1, c2, c3 = st.columns(3)
        c1.metric("Retrieval", f"{retrieval_time:.2f}s")
        c2.metric("Generation", f"{gen_time:.2f}s")
        c3.metric("Chunks used", len(filtered))

        if filtered:
            st.markdown("### Sources")
            for src in CitationManager.format_sources(filtered):
                with st.expander(f"[{src['id']}] {src['title']} ({src['party']}, {src['year']}) — similarity {src['similarity']}"):
                    st.write(src["preview"])

        if show_chunks and filtered:
            st.markdown("### Retrieved chunks (raw)")
            for i, ch in enumerate(filtered, 1):
                with st.expander(f"Chunk {i}"):
                    st.text(ch["text"])

        # Feedback
        st.markdown("### Was this answer helpful?")
        c1, c2, _ = st.columns([1, 1, 4])
        if c1.button("👍 Yes", key=f"yes_{hash(query)}"):
            st.session_state.feedback[query] = "positive"
            st.success("Thank you!")
        if c2.button("👎 No", key=f"no_{hash(query)}"):
            st.session_state.feedback[query] = "negative"
            st.info("Thank you — recorded for evaluation.")

    st.divider()
    st.caption(f"Corpus: {chunk_count} chunks | Model: {Config.LLM_MODEL} | Role: {st.session_state.role}")


# =========================================================================
# ADMIN PANELS
# =========================================================================
def admin_ingestion_panel():
    st.header("📥 Document Ingestion")
    st.info("Upload new manifestos or speeches (PDF or TXT) to add to the corpus.")

    uploaded = st.file_uploader(
        "Choose file(s)",
        type=["pdf", "txt"],
        accept_multiple_files=True
    )
    if uploaded and st.button("Ingest uploaded files"):
        dest_dir = Config.DATA_DIR
        saved = []
        for f in uploaded:
            path = f"{dest_dir}/{f.name}"
            with open(path, "wb") as out:
                out.write(f.getbuffer())
            saved.append(f.name)
        st.success(f"Saved {len(saved)} file(s) to data/documents/. Run the ingestion script to index them.")
        st.code("python scripts\\ingest.py")

    st.markdown("---")
    st.subheader("Ingestion Log")
    docs_dir = Config.DATA_DIR
    import os
    if os.path.isdir(docs_dir):
        files = os.listdir(docs_dir)
        if files:
            df = pd.DataFrame({
                "File": files,
                "Size (bytes)": [os.path.getsize(f"{docs_dir}/{f}") for f in files],
            })
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No documents in the corpus folder yet.")
    st.caption("After adding files, run `python scripts\\ingest.py` to re-index.")


def admin_users_panel():
    st.header("👥 User Management")
    users = list_users()
    if users:
        df = pd.DataFrame(
            [{"Username": u, "Role": r["role"]} for u, r in users.items()]
        )
        st.dataframe(df, use_container_width=True)

        st.markdown("#### Delete a user")
        target = st.selectbox("Select user to delete", options=[""] + list(users.keys()))
        if target and st.button(f"Delete '{target}'", type="secondary"):
            ok, msg = delete_user(target)
            if ok:
                st.success(msg)
                time.sleep(0.7)
                st.rerun()
            else:
                st.error(msg)


def admin_config_panel():
    st.header("⚙️ System Configuration")
    st.markdown("Read-only view of the current RAG configuration.")

    cfg = {
        "Embedding model": Config.EMBEDDING_MODEL,
        "Embedding dimension": Config.EMBEDDING_DIMENSION,
        "LLM model": Config.LLM_MODEL,
        "Temperature": Config.LLM_TEMPERATURE,
        "Max tokens": Config.LLM_MAX_TOKENS,
        "Chunk size": Config.CHUNK_SIZE,
        "Chunk overlap": Config.CHUNK_OVERLAP,
        "Top-K retrieval": Config.TOP_K,
        "Similarity threshold": Config.SIMILARITY_THRESHOLD,
        "Promise threshold": Config.PROMISE_THRESHOLD,
        "Data directory": Config.DATA_DIR,
        "ChromaDB directory": Config.CHROMA_DIR,
    }
    st.table(pd.DataFrame(list(cfg.items()), columns=["Parameter", "Value"]))


# =========================================================================
# EVALUATOR PANELS
# =========================================================================
def evaluator_metrics_panel():
    st.header("📊 Automated Evaluation")

    TEST_QUERIES = [
        {"query": "What did they promise about healthcare?", "keywords": ["health", "hospital", "nhif", "medical"]},
        {"query": "What are the education promises?", "keywords": ["education", "school", "learning", "teacher"]},
        {"query": "What about housing?", "keywords": ["housing", "home", "house", "mortgage"]},
        {"query": "What did they promise about jobs?", "keywords": ["jobs", "employment", "youth"]},
        {"query": "What about agriculture?", "keywords": ["farmer", "agriculture", "crop", "fertilizer"]},
    ]

    if st.button("Run evaluation (RAG vs BM25)", type="primary"):
        retriever, _ = get_components()
        all_chunks = retriever.store.collection.get()["documents"]

        if not all_chunks:
            st.error("No chunks in vector store. Ingest documents first.")
            return

        rows = []
        with st.spinner("Evaluating queries..."):
            for t in TEST_QUERIES:
                rag_results = retriever.retrieve(t["query"], top_k=5)
                rag_p = precision_at_k(rag_results, t["keywords"], k=5)

                bm25_results = bm25_baseline(t["query"], all_chunks, top_k=5)
                bm25_p = precision_at_k([{"text": txt} for txt, _ in bm25_results], t["keywords"], k=5)

                rows.append({
                    "Query": t["query"],
                    "RAG Precision@5": round(rag_p, 3),
                    "BM25 Precision@5": round(bm25_p, 3),
                    "Delta": round(rag_p - bm25_p, 3),
                })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        st.metric("Average RAG Precision", f"{df['RAG Precision@5'].mean():.3f}")
        st.metric("Average BM25 Precision", f"{df['BM25 Precision@5'].mean():.3f}")
        st.metric("Average Improvement", f"{df['Delta'].mean():.3f}")

        st.download_button(
            "📥 Download results as CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="rag_evaluation_results.csv",
            mime="text/csv"
        )


def evaluator_human_review_panel():
    st.header("🧑‍⚖️ Human Evaluation")

    st.markdown(
        "Score the chatbot's answer on a **1–5 Likert scale** for each dimension. "
        "Two reviewers should score independently to compute Cohen's Kappa."
    )

    reviewer = st.text_input("Reviewer name", placeholder="e.g., Reviewer A")
    query = st.text_area("Test query", placeholder="Paste the query you tested")
    answer = st.text_area("Chatbot answer", placeholder="Paste the answer you received")

    c1, c2, c3 = st.columns(3)
    acc = c1.slider("Accuracy (1–5)", 1, 5, 3)
    rel = c2.slider("Relevance (1–5)", 1, 5, 3)
    cit = c3.slider("Citation quality (1–5)", 1, 5, 3)

    comment = st.text_area("Comments (optional)")

    if st.button("Submit review", type="primary"):
        if not reviewer or not query:
            st.error("Please fill in reviewer name and query.")
        else:
            st.success("Review recorded!")
            st.json({
                "reviewer": reviewer,
                "query": query,
                "accuracy": acc,
                "relevance": rel,
                "citation": cit,
                "comment": comment,
            })

    st.markdown("---")
    st.caption(
        "Tip: For your project report, collect reviews from 2 reviewers on the same "
        "set of queries, then compute Cohen's Kappa using scikit-learn's "
        "`cohen_kappa_score`."
    )


# =========================================================================
# MAIN ROUTER
# =========================================================================
def sidebar_common(top_k_default=5):
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"**Role:** `{st.session_state.role}`")
        if st.button("🚪 Log Out", use_container_width=True):
            for key in ["logged_in", "username", "role", "chat_query"]:
                st.session_state[key] = "" if key != "logged_in" else False
            st.rerun()
        st.divider()
        top_k = st.slider("Number of sources", 3, 10, top_k_default)
        show_chunks = st.checkbox("Show retrieved chunks", value=True)
        st.divider()
        st.caption("Kenyan Political Promise Chatbot v1.0")
    return top_k, show_chunks


def citizen_view():
    top_k, show_chunks = sidebar_common()
    st.title("🇰🇪 Kenyan Political Promise Chatbot")
    st.caption("Citizen access — ask questions, get answers with citations")
    chatbot_panel(top_k, show_chunks)


def evaluator_view():
    top_k, show_chunks = sidebar_common()
    st.title("🇰🇪 Kenyan Political Promise Chatbot")
    st.caption(f"Evaluator access — logged in as **{st.session_state.username}**")

    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Automated Metrics", "🧑‍⚖️ Human Review"])
    with tab1:
        chatbot_panel(top_k, show_chunks)
    with tab2:
        evaluator_metrics_panel()
    with tab3:
        evaluator_human_review_panel()


def admin_view():
    top_k, show_chunks = sidebar_common()
    st.title("🇰🇪 Kenyan Political Promise Chatbot")
    st.caption(f"Administrator access — logged in as **{st.session_state.username}**")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 Chat",
        "📥 Ingestion",
        "📊 Evaluation",
        "👥 Users",
        "⚙️ Config",
    ])
    with tab1:
        chatbot_panel(top_k, show_chunks)
    with tab2:
        admin_ingestion_panel()
    with tab3:
        evaluator_metrics_panel()
    with tab4:
        admin_users_panel()
    with tab5:
        admin_config_panel()


if not st.session_state.logged_in:
    login_screen()
else:
    role = st.session_state.role
    if role == "admin":
        admin_view()
    elif role == "evaluator":
        evaluator_view()
    else:
        citizen_view()