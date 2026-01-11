import json
import logging
from pathlib import Path

import streamlit as st

from models.questions import Question

DATA_DIR = Path("data")
QUIZ_FILE = DATA_DIR / "quizzes.jsonl"
PROGRESS_FILE = DATA_DIR / "progress.json"

logger = logging.getLogger(__name__)


def load_quizzes(progress: dict[int, bool]) -> tuple[list[Question], list[Question], list[Question]]:
    quizzes_answered_correctly: list[Question] = []
    quizzes_not_answered: list[Question] = []
    quizzes_answered_incorrectly: list[Question] = []

    if not QUIZ_FILE.exists():
        return quizzes_answered_incorrectly, quizzes_not_answered, quizzes_answered_correctly

    with QUIZ_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            try:
                question = Question.parse_raw(line)
                if question.id in progress:
                    if progress[question.id]:
                        quizzes_answered_correctly.append(question)
                    else:
                        quizzes_answered_incorrectly.append(question)
                else:
                    quizzes_not_answered.append(question)
            except Exception as e:
                logger.error(f"Failed to parse question line: {e}")
                continue
    return quizzes_answered_incorrectly, quizzes_not_answered, quizzes_answered_correctly


def load_progress() -> dict[int, bool]:
    if not PROGRESS_FILE.exists():
        return {}
    try:
        with PROGRESS_FILE.open("r", encoding="utf-8") as f:
            progress = json.load(f)
        return {int(k): v for k, v in progress.items()}
    except Exception:
        return {}


def save_progress(progress):
    DATA_DIR.mkdir(exist_ok=True)
    with PROGRESS_FILE.open("w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def compute_stats(round_progress):
    asked = len(round_progress)
    correct = sum(1 for v in round_progress.values() if v)
    wrong = sum(1 for v in round_progress.values() if not v)
    pct = (correct / asked * 100) if asked else 0.0
    return asked, correct, wrong, pct


def reset_progress():
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()


def set_css_style(css_path: Path):
    if not css_path.exists():
        return
    with css_path.open("r", encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
