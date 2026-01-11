import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from utils import set_css_style
from utils.session import load_session

load_session()


st.session_state.setdefault("pos", 0)
st.session_state.setdefault("is_editing", False)

quizzies = pd.read_json("data/quizzes.jsonl", lines=True, orient="records")

logger = logging.getLogger(__name__)

set_css_style(Path("style.css"))


def main():
    st.set_page_config(page_title="Edit Questions Mode")

    st.title("View Gemini Results")

    pos = st.session_state.pos

    if pos < 0:
        st.session_state.pos = 0
        pos = 0
    if pos >= len(quizzies):
        st.session_state.pos = len(quizzies) - 1
        pos = len(quizzies) - 1

    quizzy = quizzies.iloc[pos]

    col1, col2, col3 = st.columns([1, 2, 1])
    if col1.button("Previous", disabled=pos <= 0, type="primary", icon="⬅️"):
        st.session_state.pos -= 1
        st.rerun()
    if col2.button("Edit Current Question", type="secondary", icon="✏️"):
        st.session_state.is_editing = True
        st.rerun()
    if (
        new_id := col2.number_input(
            "Go to Question id:", min_value=1, max_value=quizzies.id.max(), value=quizzy.id, width=150
        )
    ) != quizzy.id:
        if new_id not in quizzies.id.values:
            st.warning(f"Question id {new_id} does not exist.")
        else:
            st.session_state.pos = quizzies[quizzies.id == new_id].index[0]
            st.rerun()
    if col3.button("Next", disabled=pos >= len(quizzies) - 1, type="primary", icon="➡️"):
        st.session_state.pos += 1
        st.rerun()

    st.markdown(f"### Question (Id: {quizzy.id})  {pos + 1} / {len(quizzies)}")
    question = quizzy.question if "<p>" in quizzy.question.lower() else f"<p>{quizzy.question}</p>"
    st.markdown(question, unsafe_allow_html=True)

    if st.session_state.is_editing:
        answers = []
        answ_list = quizzy.answer if isinstance(quizzy.answer, list) else [quizzy.answer]
        for idx, option in enumerate(quizzy.options):
            answers.append(
                st.checkbox(
                    option,
                    value=(idx in answ_list),
                    key=f"option_{pos}_{idx}",
                )
            )

    else:
        for option in quizzy.options:
            st.markdown(f"-  {option}\n")

    st.markdown("**Current Answer:**")
    if isinstance(quizzy.answer, list):
        for ans_idx in quizzy.answer:
            st.markdown(f"- {quizzy.options[ans_idx]}")
    else:
        st.markdown(quizzy.options[quizzy.answer])

    st.markdown("---")

    st.markdown("## Explanation:")
    if st.session_state.is_editing:
        explanation = st.text_area(
            "Edit Explanation:",
            value=quizzy.explanation,
            height=400,
            key=f"explanation_{pos}",
        )
    else:
        st.markdown(quizzy.explanation, unsafe_allow_html=True)

    if st.session_state.is_editing:
        col_save, col_cancel = st.columns(2)
        if col_save.button("💾 Save Changes", type="primary", key=f"save_{pos}"):
            new_answer = [i for i, val in enumerate(answers) if val]
            quizzies.at[quizzy.name, "answer"] = new_answer if len(new_answer) > 1 else new_answer[0]
            quizzies.at[quizzy.name, "explanation"] = explanation
            quizzies.to_json("data/quizzes.jsonl", lines=True, orient="records")
            st.session_state.is_editing = False
            st.success("Changes saved successfully!")
            st.rerun()
        if col_cancel.button("❌ Cancel", type="secondary", key=f"cancel_{pos}"):
            st.session_state.is_editing = False
            st.rerun()


if __name__ == "__main__":
    main()
