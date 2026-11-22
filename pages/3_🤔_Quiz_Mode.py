import logging
import random
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Quiz Mode", layout="wide")

from utils import compute_stats, fix_image_src, load_progress, load_quizzes, save_progress, set_css_style
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
            st.switch_page("🏠_Dashboard.py")

        if st.button("Clear round data", icon="🗑️", on_click=clear_round_data):
            st.switch_page("🏠_Dashboard.py")

        return

    # show current question
    quizzes = st.session_state.quizzes
    q = quizzes[pos]
    st.header(f"Question (#{q.id}) {pos + 1} / {len(st.session_state.quizzes)}")

    tags = []
    if q.gcp_products:
        tags.append(f"☁️ **Products:** {', '.join(q.gcp_products)}")
    if q.gcp_topics or q.ml_topics:
        tags.append(f"📚 **Topics:** {', '.join(q.gcp_topics or q.ml_topics)}")
    if tags:
        st.caption(" • ".join(tags))

    question = q.question if "<p>" in q.question.lower() else f"<p>{q.question}</p>"
    st.markdown(fix_image_src(question), unsafe_allow_html=True)

    # choice control keying by position to keep state per question
    choice_key = f"choice_{pos}"
    if q.mode == "single_choice":
        choice = st.radio(
            "Choose an answer:",
            q.options,
            index=None,
            key=choice_key,
            disabled=st.session_state.quiz_mode_answered,
        )
    else:
        choice = [0] * len(q.options)
        for i, answ in enumerate(q.options):
            choice[i] = st.checkbox(
                answ,
                value=False,
                key=f"{choice_key}_{i}",
                disabled=st.session_state.quiz_mode_answered,
            )
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    if col1.button("✅ Submit", key=f"submit_{pos}", type="primary", disabled=st.session_state.quiz_mode_answered):
        if not choice or (isinstance(choice, list) and not any(choice)):
            st.warning("Please select at least one answer before submitting.")
        else:
            correct_answer_set = set(q.answer) if isinstance(q.answer, list) else {q.answer}
            if q.mode == "multiple_choice":
                choice_idx = set([i for i, val in enumerate(choice) if val])
                st.session_state.quiz_mode_round_progress[pos] = choice_idx == correct_answer_set
            else:
                choice_idx = q.options.index(choice)
                st.session_state.quiz_mode_round_progress[pos] = choice_idx in correct_answer_set

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
            if isinstance(q.answer, list):
                for ans_idx in q.answer:
                    st.markdown(f"- {q.options[ans_idx]}")
            else:
                st.markdown(q.options[q.answer])
        st.markdown("### Explanation:")
        if q.explanation:
            st.markdown(fix_image_src(q.explanation), unsafe_allow_html=True)

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
                st.switch_page("🏠_Dashboard.py")

            if st.button("Clear round data", icon="🗑️", on_click=clear_round_data):
                st.switch_page("🏠_Dashboard.py")


def show_stats():
    progress = load_progress()
    answered_incorrectly, not_answered, answered_correctly = load_quizzes(progress)

    all_quizzes = answered_incorrectly + not_answered + answered_correctly
    if not all_quizzes:
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

    with st.container(border=True):
        st.subheader("🎯 Round Settings")
        all_products = sorted(list(set(p for q in all_quizzes for p in q.gcp_products if p)))
        c_prod, c_size = st.columns([2, 1])
        selected_product = c_prod.selectbox(
            "Filter by GCP Product / Domain:",
            ["All Products / Domains"] + all_products,
            key="selected_product_filter",
        )
        round_size = c_size.selectbox(
            "Round size:",
            [10, 20, 30, 50, "All"],
            index=1,
            key="round_size_selection",
        )

        include_wrong = st.toggle("➕ Include Previously Wrong Questions", value=True, key="wrong_answered_inclusion")
        if include_wrong:
            st.caption("Previously wrong answers will be prioritized so you can reinforce weak areas.")
            st.number_input(
                "Percentage of previously correct answers to include for review",
                min_value=0,
                max_value=100,
                value=0,
                step=10,
                key="correct_answered_percentage",
            )

    if st.button("▶️ Start Round", type="primary"):
        if st.session_state.wrong_answered_inclusion:
            pct = st.session_state.get("correct_answered_percentage", 0)
            num_to_include = int(len(answered_correctly) * pct / 100)
            candidate_quizzes = not_answered + answered_incorrectly
            if num_to_include > 0:
                logger.info(f"Including {num_to_include} previously correct answered questions in the round.")
                sampled_correct = random.sample(answered_correctly, num_to_include) if num_to_include > 0 else []
                candidate_quizzes += sampled_correct
        else:
            candidate_quizzes = not_answered

        if selected_product != "All Products / Domains":
            candidate_quizzes = [q for q in candidate_quizzes if selected_product in q.gcp_products]

        if not candidate_quizzes:
            st.warning("No quizzes match the selected filters for this round.")
        else:
            if round_size != "All" and isinstance(round_size, int):
                random.shuffle(candidate_quizzes)
                candidate_quizzes = candidate_quizzes[:round_size]
            st.session_state.message = f"Starting new round with {len(candidate_quizzes)} questions..."
            start_new_round(candidate_quizzes)


def main():
    st.title("Quiz Mode")

    if st.session_state.quiz_in_progress and st.session_state.quizzes:
        show_quiz()
    else:
        st.session_state.quiz_in_progress = None
        show_stats()


if __name__ == "__main__":
    main()
