from pathlib import Path

import streamlit as st

from dashboard import show_dashboard
from utils import reset_progress, save_progress, set_css_style

st.set_page_config(page_title="Quiz Learner", initial_sidebar_state="collapsed", layout="wide")


def main():
    st.set_page_config(page_title="Quiz Learner", initial_sidebar_state="collapsed", layout="wide")

    set_css_style(Path("style.css"))

    st.title("Quiz Learner — Dashboard")

    stats = show_dashboard()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start", type="primary"):
            if stats["total"] == 0:
                st.warning("⚠️ No quizzes found in data/quizzes.jsonl")
                return
            # initialize a flag and navigate to the Quiz Mode page
            st.session_state.quiz_in_progress = False
            st.session_state.quizzes = None
            st.session_state.quiz_mode_pos = 0
            st.session_state.quiz_mode_round_progress = {}
            st.session_state.quiz_mode_answered = False

            st.switch_page("pages/3_🤔_Quiz_Mode.py")

    with col2:
        if st.button("‼️ Reset progress"):
            st.warning("This will clear all your progress and cannot be undone.", icon="⚠️")
            if st.button(
                "Yes",
                icon="🚨",
            ):
                reset_progress()
                progress = {}
                save_progress(progress)
                st.rerun()


if __name__ == "__main__":
    main()
