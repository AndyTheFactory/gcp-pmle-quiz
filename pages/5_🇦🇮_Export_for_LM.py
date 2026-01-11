from pathlib import Path

import streamlit as st

from utils import load_progress, load_quizzes

MD_PATH = Path("export_for_lm.md")


# Read and display markdown content
if MD_PATH.exists():
    st.markdown(MD_PATH.read_text(encoding="utf-8"))
else:
    st.error(f"Markdown file '{MD_PATH.name}' not found.")


# Export questions with "False" in Progress.json
def export_false_questions():
    progress = load_progress()
    _, _, questions = load_quizzes(progress)

    # Create markdown content
    md_lines = [
        "# Questions that I lack knowledge of\n",
        "Below is a list of questions that I answered incorrectly. I should review these topics to improve my understanding.",
        "Use all these questions as starting point to create flashcards and quizzes for me to study.",
        "Use related knowledge to create additional questions to help me learn the topics better.\n",
    ]
    for q in questions:
        md_lines.append(f"## Question ID: {q.id}\n")
        md_lines.append(f"### Question: \n\n {q.question}\n")
        md_lines.append("### Answer Options:")
        md_lines.extend([f"- {answer}" for answer in q.options])
        md_lines.append("\n### Correct Answer:\n")
        if isinstance(q.answer, list):
            md_lines.extend([f"- {q.options[a]}" for a in q.answer])
        else:
            md_lines.append(f"- {q.options[q.answer]}")

        md_lines.append("---\n")

    return "\n".join(md_lines)


if st.button("Export Unanswered Questions for NotebookLM", type="primary"):
    export_md = export_false_questions()
    st.download_button(
        label="Download Markdown", data=export_md, file_name="unanswered_questions.md", mime="text/markdown"
    )
