import logging
from pathlib import Path

import streamlit as st
from diskcache import Cache

from models.questions import Question

logger = logging.getLogger(__name__)

CACHE_DIR = Path("./cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
cache = Cache(str(CACHE_DIR))


def load_session():
    if "message" in st.session_state:
        st.info(st.session_state.message)
        del st.session_state.message
    st.session_state.setdefault("quiz_in_progress", None)
    st.session_state.setdefault("quiz_mode_pos", 0)
    st.session_state.setdefault("quiz_mode_round_progress", {})
    st.session_state.setdefault("quiz_mode_answered", False)
    st.session_state.setdefault("wrong_answered_inclusion", False)
    st.session_state.setdefault("correct_answered_percentage", 0)
    st.session_state.setdefault("quizzes", [])

    try:
        if cache.get("quiz_in_progress", False):
            st.session_state.quiz_in_progress = cache.get("quiz_in_progress", False)
            st.session_state.quizzes = [Question.model_validate(d) for d in cache.get("quizzes", [])]
            st.session_state.quiz_mode_pos = cache.get("quiz_mode_pos", 0)
            st.session_state.quiz_mode_round_progress = cache.get("quiz_mode_round_progress", {})
    except Exception as e:
        logger.warning(f"Failed to load session from cache: {e}")


def cache_session():
    try:
        cache.set("quiz_in_progress", st.session_state.quiz_in_progress)
        if st.session_state.quiz_in_progress:
            cache.set("quizzes", [q.model_dump() for q in st.session_state.quizzes])
            cache.set("quiz_mode_pos", st.session_state.quiz_mode_pos)
            cache.set("quiz_mode_round_progress", st.session_state.quiz_mode_round_progress)
        else:
            cache.delete("quizzes")
            cache.delete("quiz_mode_pos")
            cache.delete("quiz_mode_round_progress")
    except Exception as e:
        logger.warning(f"Failed to update session cache: {e}")


def clear_session_cache():
    try:
        cache.delete("quiz_in_progress")
        cache.delete("quizzes")
        cache.delete("quiz_mode_pos")
        cache.delete("quiz_mode_round_progress")
    except Exception as e:
        logger.warning(f"Failed to clear session cache: {e}")
