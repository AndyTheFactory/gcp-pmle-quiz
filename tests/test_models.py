import json
from pathlib import Path
from models.questions import Question


def test_question_model_validation():
    q = Question(
        id=1,
        mode="single_choice",
        question="What is Vertex AI?",
        options=["A. Storage", "B. ML platform"],
        answer=1,
        explanation="Vertex AI is Google Cloud's ML platform."
    )
    assert q.id == 1
    assert q.mode == "single_choice"
    assert q.answer == 1


def test_all_quizzes_in_data_file():
    quiz_file = Path("data/quizzes.jsonl")
    assert quiz_file.exists(), "quizzes.jsonl must exist"

    count = 0
    with quiz_file.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            data = json.loads(line)
            q = Question.model_validate(data)
            assert q.id > 0
            assert len(q.options) >= 2
            if q.mode == "single_choice":
                assert isinstance(q.answer, int), f"Line {i+1} single_choice answer must be int"
                assert 0 <= q.answer < len(q.options), f"Line {i+1} answer index out of bounds"
            else:
                assert isinstance(q.answer, list), f"Line {i+1} multiple_choice answer must be list"
                assert all(0 <= a < len(q.options) for a in q.answer), f"Line {i+1} answer index out of bounds"
            count += 1

    assert count >= 800, f"Expected at least 800 questions, got {count}"


def test_question_148_is_single_choice():
    quiz_file = Path("data/quizzes.jsonl")
    found = False
    with quiz_file.open("r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            if data.get("id") == 148:
                found = True
                assert data["mode"] == "single_choice"
                assert isinstance(data["answer"], int)
                assert data["answer"] == 1
                break
    assert found, "Question 148 should exist in quizzes.jsonl"
