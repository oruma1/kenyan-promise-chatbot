"""Streamlit UI with role-based access control"""
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import streamlit as st
import time
import pandas as pd

from src.retriever import Retriever
from src.generator import Generator
from src.citation_manager import CitationManager
from src.config import Config
from src.auth import authenticate, register_user, list_users, delete_user, ROLES, get_user_id
from src.evaluator import bm25_baseline, precision_at_k
from src import logging_db


# ---------------------------------------------------------------------------
# Module-level evaluation queries (was hard-coded inside evaluator panel)
# ---------------------------------------------------------------------------
TEST_QUERIES = [
    {"query": "What did they promise about healthcare?",
     "keywords": ["health", "hospital", "nhif", "medical", "SHA"]},
    {"query": "What are the education promises?",
     "keywords": ["education", "school", "learning", "teacher", "laptops"]},
    {"query": "What about housing?",
     "keywords": ["housing", "home", "house", "mortgage", "affordable"]},
    {"query": "What did they promise about jobs?",
     "keywords": ["jobs", "employment", "youth"]},
    {"query": "What about agriculture?",
     "keywords": ["farmer", "agriculture", "crop", "fertilizer"]},
]


st.set_page_config(
    page_title="Kenyan Political Promise Accountability Chatbot",
    layout="wide"
)


# --- Session state ---
for key, default in {
    "logged_in": False,
    "username": "",
    "role": "",
    "show_register": False,
    "feedback": {},            # response_id -> "positive"/"negative"
    "last_cache_key": None,    # (query, top_k)
    "last_response": None,
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
    st.title(" Kenyan Political Promise Accountability Chatbot")
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
# HELPERS
# =========================================================================
def _merge_retrieved(results_lists, top_k):
    """Merge multiple retrieval result lists, dedupe by text, sort by similarity."""
    seen = set()
    merged = []
    for results in results_lists:
        for r in results:
            key = r.get("text", "")
            if key and key not in seen:
                seen.add(key)
                merged.append(r)
    merged.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
    return merged[:top_k]


def _detect_parties(query_lower):
    """Return a list of matching parties (can be >1 for compound questions)."""
    matches = []
    if "azimio" in query_lower or "raila" in query_lower or "odinga" in query_lower:
        matches.append("Azimio La Umoja")
    if "kenya kwanza" in query_lower or "ruto" in query_lower or "uda" in query_lower:
        matches.append("Kenya Kwanza")
    if "jubilee" in query_lower or "uhuru" in query_lower or "kenyatta" in query_lower:
        matches.append("Jubilee Party")
    if "nasa" in query_lower:
        matches.append("NASA")
    return matches


# =========================================================================
# SHARED CHATBOT PANEL (used by all roles)
# =========================================================================
def chatbot_panel(top_k: int, show_chunks: bool):
    st.header("💬 Ask about political promises for accountability")

    try:
        retriever, generator = get_components()
        chunk_count = retriever.store.count()
    except Exception as e:
        st.error(f"Failed to initialize RAG components: {e}")
        return

    query = st.text_input(
        "Your question:",
        placeholder="Enter a question on political campaign promises made during the 2017 or 2022 presidential elections",
        key="chat_query"
    )

    if query:
        user_id = get_user_id(st.session_state.username)
        if user_id is None:
            st.error("Could not identify your user account. Please log out and log back in.")
            return

        # Explicit re-run button: clears cache so the pipeline re-executes
        # (needed because a repeated identical query would otherwise be served from cache)
        if st.button("🔄 Re-run query", key="rerun_btn"):
            st.session_state.pop("last_cache_key", None)
            st.session_state.pop("last_response", None)
            st.rerun()

        cache_key = (query, top_k)

        # ---- RUN PIPELINE only when the (query, top_k) pair has changed ----
        if st.session_state.get("last_cache_key") != cache_key:
            query_id = logging_db.log_query(user_id, query)

            with st.spinner("Searching and generating..."):
                # --- Retrieval (party-aware) ---
                query_lower = query.lower()
                party_matches = _detect_parties(query_lower)

                retrieval_start = time.time()
                if len(party_matches) > 1:
                    retrieved = _merge_retrieved(
                        [retriever.retrieve(query, top_k=top_k, party=p)
                         for p in party_matches],
                        top_k=top_k,
                    )
                elif len(party_matches) == 1:
                    retrieved = retriever.retrieve(query, top_k=top_k, party=party_matches[0])
                else:
                    retrieved = retriever.retrieve(query, top_k=top_k, party=None)
                retrieval_ms = int((time.time() - retrieval_start) * 1000)

                real_chunks = [
                    r for r in retrieved
                    if r.get("similarity", 0.0) >= Config.SIMILARITY_THRESHOLD
                ]

                # --- FACT-CHECK EVIDENCE LAYER ---
                from src.db import fetch_all
                evidence_matches = []
                seen_ev_keys = set()
                for keyword in ["health", "maternity", "housing", "home", "house",
                                "manufacturing", "fertilizer", "nhif", "afya"]:
                    if keyword in query_lower:
                        ev_data = fetch_all(
                            "SELECT * FROM promise_evidence WHERE promise_keyword LIKE ?",
                            (f"%{keyword}%",),
                        )
                        for ev in ev_data or []:
                            ev_key = (
                                ev.get("promise_keyword"),
                                ev.get("status"),
                                ev.get("party"),
                                ev.get("original_promise"),
                            )
                            if ev_key not in seen_ev_keys:
                                seen_ev_keys.add(ev_key)
                                evidence_matches.append(ev)

                evidence_chunks = [
                    {
                        "text": (
                            f"FACT-CHECK TRACKER STATUS: {ev['status']}. "
                            f"Original Promise: '{ev['original_promise']}'. "
                            f"Action Taken: '{ev['action_taken']}'."
                        ),
                        "similarity": 1.0,
                        "metadata": {"title": "Fact-Check Tracker",
                                     "party": ev["party"], "year": "2024"},
                    }
                    for ev in evidence_matches
                ]

                # Combine evidence + real chunks WITHOUT starving real retrieval.
                # Guarantee: at least 1 real chunk if any exist, at least 1 evidence
                # chunk if any exist, capped at 2 total for CPU speed.
                if evidence_chunks and real_chunks:
                    filtered = [evidence_chunks[0], real_chunks[0]]
                elif evidence_chunks:
                    filtered = evidence_chunks[:2]
                else:
                    filtered = real_chunks[:2]
                # --- END FACT-CHECK LAYER ---

                has_evidence = bool(filtered)

                            # --- Generation (streaming) ---
            generation_start = time.time()
            try:
                if filtered:
                    with st.chat_message("assistant"):
                        answer = st.write_stream(generator.generate_stream(query, filtered))
                    result = {"answer": answer, "has_evidence": True}
                else:
                    result = {
                        "answer": "I do not have sufficient evidence in the corpus "
                                  "to answer this question.",
                        "has_evidence": False,
                    }
            except Exception as e:
                st.error(f"Generation failed: {e}")
                return
            generation_ms = int((time.time() - generation_start) * 1000)

            # --- Log response + citations ---
            response_id = logging_db.log_response(
                query_id=query_id,
                response_text=result["answer"],
                retrieval_ms=retrieval_ms,
                generation_ms=generation_ms,
                model_version=Config.LLM_MODEL,
            )
            if has_evidence:
                logging_db.log_citations(response_id, filtered)
                logging_db.mark_query_answered(query_id)

            st.session_state["last_cache_key"] = cache_key
            st.session_state["last_response"] = {
                "query_id": query_id,
                "response_id": response_id,
                "answer": result["answer"],
                "has_evidence": has_evidence,
                "retrieved": filtered,
                "retrieval_ms": retrieval_ms,
                "generation_ms": generation_ms,
            }

        # ---- DISPLAY: always pull from session state ----
        cached = st.session_state.get("last_response", None)
        if not cached:
            return

        response_id = cached["response_id"]
        retrieval_ms = cached["retrieval_ms"]
        generation_ms = cached["generation_ms"]
        filtered = cached["retrieved"]
        answer = cached["answer"]

        st.markdown("### Answer")

        with st.chat_message("assistant"):
            st.write(answer)

            # Colored badge for fact-check evidence
            for c in filtered:
                if "FACT-CHECK TRACKER STATUS:" in c.get("text", ""):
                    status_str = (
                        c["text"].split("FACT-CHECK TRACKER STATUS:")[1]
                        .split(".")[0].strip()
                    )
                    if "FULFILLED" in status_str and "PARTIALLY" not in status_str:
                        st.success(f"✅ Official Status: **{status_str}**")
                    elif "PARTIALLY" in status_str:
                        st.warning(f"⚠️ Official Status: **{status_str}**")
                    elif "BROKEN" in status_str:
                        st.error(f"❌ Official Status: **{status_str}**")
                    else:
                        st.info(f"ℹ️ Official Status: **{status_str}**")

        c1, c2, c3 = st.columns(3)
        c1.metric("Retrieval", f"{retrieval_ms / 1000:.2f}s")
        c2.metric("Generation", f"{generation_ms / 1000:.2f}s")
        c3.metric("Chunks used", len(filtered))

        if filtered:
            st.markdown("### Sources")
            for src in CitationManager.format_sources(filtered):
                with st.expander(
                    f"[{src['id']}] {src['title']} "
                    f"({src['party']}, {src['year']}) — similarity {src['similarity']}"
                ):
                    st.write(src["preview"])

        if show_chunks and filtered:
            st.markdown("### Retrieved chunks (raw)")
            for i, ch in enumerate(filtered, 1):
                with st.expander(f"Chunk {i}"):
                    st.text(ch["text"])

        # ---- FEEDBACK (prevent duplicate submissions) ----
        st.markdown("### Was this answer helpful?")
        feedback_map = st.session_state.feedback
        existing = feedback_map.get(response_id)

        if existing:
            icon = "👍" if existing == "positive" else "👎"
            st.info(f"{icon} Thank you — you rated this answer **{existing}**.")
        else:
            c1, c2, _ = st.columns([1, 1, 4])
            if c1.button("👍 Yes", key=f"fb_pos_{response_id}"):
                try:
                    logging_db.log_feedback(response_id, user_id, "positive")
                    feedback_map[response_id] = "positive"
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save feedback: {e}")
            if c2.button("👎 No", key=f"fb_neg_{response_id}"):
                try:
                    logging_db.log_feedback(response_id, user_id, "negative")
                    feedback_map[response_id] = "negative"
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save feedback: {e}")

    st.divider()
    st.caption(
        f"Corpus: {chunk_count} chunks | Model: {Config.LLM_MODEL} | "
        f"Role: {st.session_state.role}"
    )


# =========================================================================
# ADMIN PANELS
# =========================================================================
def admin_ingestion_panel():
    st.header("📥 Document Ingestion")
    st.info("Upload new manifestos or speeches (PDF or TXT) to add to the corpus.")
    st.caption(f"Files will be saved to: `{Config.DATA_DIR}/`")
    if "documents" not in str(Config.DATA_DIR).lower():
        st.warning(
            f"⚠️ `Config.DATA_DIR = '{Config.DATA_DIR}'` does not look like "
            f"`data/documents/`. Verify `scripts/ingest.py` reads from the same path."
        )

    uploaded = st.file_uploader(
        "Choose file(s)",
        type=["pdf", "txt"],
        accept_multiple_files=True,
    )

    if uploaded and st.button("1. Save uploaded files"):
        dest_dir = Config.DATA_DIR
        saved = []
        for f in uploaded:
            path = f"{dest_dir}/{f.name}"
            with open(path, "wb") as out:
                out.write(f.getbuffer())
            saved.append(f.name)
        st.success(f"Saved {len(saved)} file(s) to `{Config.DATA_DIR}/`.")

    st.markdown("---")
    st.subheader("2. Rebuild Vector Database")
    st.warning(
        f"This will clear the current database and re-read all files in "
        f"`{Config.DATA_DIR}/`."
    )

    if st.button("🚀 Run Ingestion Now", type="primary"):
        import subprocess
        import sys

        with st.spinner("Ingesting documents... This may take a minute."):
            try:
                result = subprocess.run(
                    [sys.executable, "scripts/ingest.py"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                st.success("Ingestion Complete!")
                st.code(result.stdout)
                st.cache_resource.clear()
            except subprocess.CalledProcessError as e:
                st.error("Ingestion failed!")
                st.code(e.stderr)
            except Exception as e:
                st.error(f"Error: {e}")


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

    if st.button("Run evaluation (RAG vs BM25)", type="primary"):
        retriever, _ = get_components()
        all_chunks = retriever.store.collection.get()["documents"]
        user_id = get_user_id(st.session_state.username)

        if not all_chunks:
            st.error("No chunks in vector store. Ingest documents first.")
            return

        rows = []
        with st.spinner("Evaluating queries..."):
            for t in TEST_QUERIES:
                rag_results = retriever.retrieve(t["query"], top_k=5)
                rag_p = precision_at_k(rag_results, t["keywords"], k=5)

                bm25_results = bm25_baseline(t["query"], all_chunks, top_k=5)
                bm25_p = precision_at_k(
                    [{"text": txt} for txt, _ in bm25_results], t["keywords"], k=5
                )

                if user_id:
                    logging_db.log_evaluation(
                        evaluator_id=user_id,
                        test_query=t["query"],
                        precision_at_5=float(rag_p),
                        bm25_precision=float(bm25_p),
                    )

                rows.append({
                    "Query": t["query"],
                    "RAG Precision@5": round(rag_p, 3),
                    "BM25 Precision@5": round(bm25_p, 3),
                    "Delta": round(rag_p - bm25_p, 3),
                })

        df = pd.DataFrame(rows)
        st.success("Evaluation complete — results saved to database.")
        st.dataframe(df, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Avg RAG Precision", f"{df['RAG Precision@5'].mean():.3f}")
        c2.metric("Avg BM25 Precision", f"{df['BM25 Precision@5'].mean():.3f}")
        c3.metric("Avg Improvement", f"{df['Delta'].mean():.3f}")

        st.download_button(
            "📥 Download results as CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="rag_evaluation_results.csv",
            mime="text/csv",
        )

    st.markdown("---")
    st.subheader("Past Evaluations")
    past = logging_db.get_recent_evaluations(limit=20)
    if past:
        df_past = pd.DataFrame(past)[
            ["run_at", "evaluator", "test_query", "precision_at_5", "bm25_precision"]
        ]
        st.dataframe(df_past, use_container_width=True)
    else:
        st.info("No evaluations run yet.")


def evaluator_human_review_panel():
    st.header("🧑‍⚖️ Human Evaluation")

    st.markdown(
        "Score the chatbot's answer on a **1–5 Likert scale** for each dimension. "
        "Two reviewers should score independently to compute Cohen's Kappa."
    )

    with st.form("human_review_form"):
        reviewer = st.text_input("Reviewer name", placeholder="e.g., Reviewer A")
        query = st.text_area("Test query", placeholder="Paste the query you tested")
        answer = st.text_area("Chatbot answer", placeholder="Paste the answer you received")

        c1, c2, c3 = st.columns(3)
        acc = c1.slider("Accuracy (1–5)", 1, 5, 3)
        rel = c2.slider("Relevance (1–5)", 1, 5, 3)
        cit = c3.slider("Citation quality (1–5)", 1, 5, 3)

        comment = st.text_area("Comments (optional)")
        submit = st.form_submit_button("Submit review", type="primary")

        if submit:
            if not reviewer or not query:
                st.error("Please fill in reviewer name and query.")
            else:
                user_id = get_user_id(st.session_state.username)
                if user_id:
                    logging_db.log_human_review(
                        reviewer_id=user_id,
                        query_text=query,
                        answer_text=answer,
                        accuracy_score=acc,
                        relevance_score=rel,
                        citation_score=cit,
                        comments=comment,
                    )
                    st.success("Review saved to database!")
                else:
                    st.error("Could not identify your user account.")

    st.markdown("---")
    st.subheader("Past Reviews")
    past = logging_db.get_recent_reviews(limit=50)
    if past:
        df = pd.DataFrame(past)[
            ["created_at", "reviewer", "query_text",
             "accuracy_score", "relevance_score", "citation_score"]
        ]
        st.dataframe(df, use_container_width=True)

        st.download_button(
            "📥 Download Reviews (CSV for Cohen's Kappa)",
            df.to_csv(index=False).encode("utf-8"),
            file_name="human_reviews_export.csv",
            mime="text/csv",
        )
    else:
        st.info("No human reviews submitted yet.")


# =========================================================================
# MAIN ROUTER
# =========================================================================
def sidebar_common(top_k_default=5):
    with st.sidebar:
        st.markdown(f"### 👤 Logged in as: **{st.session_state.username}**")
        st.markdown(f"**Role:** `{st.session_state.role}`")
        if st.button("🚪 Log Out", use_container_width=True):
            for key in [
                "logged_in", "username", "role", "show_register",
                "chat_query", "last_cache_key", "last_response", "feedback",
            ]:
                st.session_state.pop(key, None)
            st.rerun()
        st.divider()
        st.markdown("### ⚙️")
        top_k = st.slider("Number of sources", 1, 6, top_k_default)
        show_chunks = st.checkbox("Show retrieved chunks", value=True)
        st.divider()
        st.markdown("### ℹ️ About")
        st.info(
            "This AI system retrieves promises from the 2017 and 2022 manifestos. "
            "It uses **RAG** to ground its answers and a **Fact-Check Tracker** "
            "to verify fulfillment."
        )
        st.warning(
            "**Disclaimer:** This is an academic prototype. AI-generated answers "
            "should be verified against the cited sources."
        )
        st.caption("Kenyan Political Promise Accountability Chatbot - Project, 150216")
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