import logging
import random
from pathlib import Path

import streamlit as st

from utils import compute_stats, load_progress, load_quizzes, save_progress, set_css_style
from utils.session import cache_session, clear_session_cache, load_session

load_session()

logger = logging.getLogger(__name__)

set_css_style(Path("style.css"))


def save_progress_click(progress):
    saved = load_progress()
    saved.update(progress)
    save_progress(saved)
    clear_round_data()
    st.success("Round results merged into overall progress.")


def clear_round_data():
    st.session_state.quiz_in_progress = None
    st.session_state.quizzes = []
    st.session_state.quiz_mode_pos = 0
    st.session_state.quiz_mode_round_progress = {}
    clear_session_cache()


def start_new_round(quizzes):
    random.shuffle(quizzes)
    st.session_state.quiz_in_progress = True
    st.session_state.quizzes = quizzes
    st.session_state.quiz_mode_pos = 0
    st.session_state.quiz_mode_round_progress = {}
    st.session_state.quiz_mode_answered = False
    cache_session()
    st.rerun()


def show_quiz():
    pos = st.session_state.quiz_mode_pos
    if pos >= len(st.session_state.quizzes):
        st.success("Round complete — no more questions in this shuffled round.")
        asked, correct, wrong, pct = compute_stats(st.session_state.quiz_mode_round_progress)
        st.markdown(f"Asked: {asked} — Correct: {correct} — Wrong: {wrong} — Success: {pct:.1f}%")
        progress = {st.session_state.quizzes[p].id: res for p, res in st.session_state.quiz_mode_round_progress.items()}
        if st.button(
            "Save round results to overall progress", icon="💾", on_click=save_progress_click, args=(progress,)
        ):
            st.switch_page("app.py")

        if st.button("Clear round data", icon="🗑️", on_click=clear_round_data):
            st.switch_page("app.py")

        return

    # show current question
    quizzes = st.session_state.quizzes
    q = quizzes[pos]
    st.header(f"Question (#{q.id}) {pos + 1} / {len(st.session_state.quizzes)}")

    question = q.question if "<p>" in q.question.lower() else f"<p>{q.question}</p>"
    st.markdown(question, unsafe_allow_html=True)

    # choice control keying by position to keep state per question
    choice_key = f"choice_{pos}"
    if q.mode == "single_choice":
        choice = st.radio(
            "Choose an answer:",
            q.options,
            index=None,
            key=choice_key,
        )
    else:
        choice = [0] * len(q.options)
        for i, answ in enumerate(q.options):
            choice[i] = st.checkbox(
                answ,
                value=False,
                key=f"{choice_key}_{i}",
            )
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    if col1.button("✅ Submit", key=f"submit_{pos}", type="primary", disabled=st.session_state.quiz_mode_answered):
        if not choice or (isinstance(choice, list) and not any(choice)):
            st.warning("Please select at least one answer before submitting.")
        else:
            if q.mode == "multiple_choice":
                choice_idx = set([i for i, val in enumerate(choice) if val])
                st.session_state.quiz_mode_round_progress[pos] = choice_idx == set(q.answer)
            else:
                choice_idx = q.options.index(choice)
                st.session_state.quiz_mode_round_progress[pos] = choice_idx == q.answer

            st.session_state.quiz_mode_answered = True
            cache_session()
            st.rerun()

    if st.session_state.quiz_mode_answered:
        if st.session_state.quiz_mode_round_progress[pos]:
            st.success("Correct ✅")
        else:
            st.error("Incorrect ❌")
            st.markdown("---")
            st.markdown("### Correct Answer:")
            if q.mode == "multiple_choice":
                for ans_idx in q.answer:
                    st.markdown(f"- {q.options[ans_idx]}")
            else:
                st.markdown(q.options[q.answer])
        st.markdown("### Explanation:")
        st.markdown(q.explanation, unsafe_allow_html=True)

    caption = "➡️ Next Question" if st.session_state.quiz_mode_answered else "⏭️ Skip Question"
    if col2.button(caption, key=f"next_{pos}"):
        st.session_state.quiz_mode_pos += 1
        st.session_state.quiz_mode_answered = False
        cache_session()
        st.rerun()

    st.markdown("---")
    # small live round stats
    asked, correct, wrong, pct = compute_stats(st.session_state.quiz_mode_round_progress)
    st.markdown(f"Round progress — asked: {asked}, correct: {correct}, wrong: {wrong}, success: {pct:.1f}%")

    col1, col2 = st.columns(2)
    with col1:
        with st.popover("🔄 Restart Round"):
            st.warning("Restarting will lose current round progress. Are you sure?")
            if st.button("Yes, restart", type="primary"):
                clear_round_data()
                st.session_state.message = "Starting new round..."
                start_new_round(quizzes)
                st.rerun()
    with col2:
        with st.popover("🚫 Stop Round"):
            # show stats for current round
            asked, correct, wrong, pct = compute_stats(st.session_state.quiz_mode_round_progress)
            st.info(f"Round stats — asked: {asked}, correct: {correct}, wrong: {wrong}, success: {pct:.1f}%")

            progress = {
                st.session_state.quizzes[p].id: res for p, res in st.session_state.quiz_mode_round_progress.items()
            }
            if st.button(
                "Save round results to overall progress", icon="💾", on_click=save_progress_click, args=(progress,)
            ):
                st.switch_page("app.py")

            if st.button("Clear round data", icon="🗑️", on_click=clear_round_data):
                st.switch_page("app.py")


def show_stats():
    progress = load_progress()
    answered_incorrectly, not_answered, answered_correctly = load_quizzes(progress)

    if not answered_incorrectly and not not_answered and not answered_correctly:
        st.warning("No quizzes found in data/quizzes.jsonl")
        return

    container = st.container()
    with container:
        cols = st.columns(3)
        with cols[0]:
            st.metric("Answered correctly", len(answered_correctly))
        with cols[1]:
            st.metric("Answered incorrectly", len(answered_incorrectly))
        with cols[2]:
            st.metric("Not answered", len(not_answered))

    if st.button("Start Round", type="primary"):
        if st.session_state.wrong_answered_inclusion:
            pct = st.session_state.correct_answered_percentage
            num_to_include = int(len(answered_correctly) * pct / 100)
            quizzes = not_answered + answered_incorrectly
            if num_to_include > 0:
                logger.info(f"Including {num_to_include} previously correct answered questions in the round.")
                sampled_correct = random.sample(answered_correctly, num_to_include) if num_to_include > 0 else []
                quizzes += sampled_correct
        else:
            quizzes = not_answered

        if not quizzes:
            st.warning("No quizzes left to answer for this round.")
        else:
            st.session_state.message = "Starting new round..."
            start_new_round(quizzes)

    st.info("Press 'Start Round' to begin the quiz.")

    if st.toggle("➕ Include Wrong Answered", value=False, key="wrong_answered_inclusion"):
        st.info("Previous wrong answers will be included in the quiz.")

        st.number_input(
            "Percentage of correct answered to include",
            min_value=0,
            max_value=100,
            value=0,
            step=10,
            key="correct_answered_percentage",
        )


def main():
    st.set_page_config(page_title="Quiz Mode")

    st.title("Quiz Mode")

    if st.session_state.quiz_in_progress and st.session_state.quizzes:
        show_quiz()
    else:
        st.session_state.quiz_in_progress = None
        show_stats()


if __name__ == "__main__":
    main()
