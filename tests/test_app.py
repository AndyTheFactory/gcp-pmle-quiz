import json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest


from utils.session import clear_session_cache


@pytest.fixture(autouse=True)
def clean_environment(tmp_path, monkeypatch):
    """Ensure cache and progress do not leak across tests."""
    prog_file = Path("data/progress.json")
    if prog_file.exists():
        prog_file.unlink()
    clear_session_cache()
    yield
    if prog_file.exists():
        prog_file.unlink()
    clear_session_cache()


def test_dashboard_page_no_progress():
    at = AppTest.from_file("🏠_Dashboard.py")
    at.run()
    assert not at.exception
    # Check start button exists
    assert any("Start" in b.label for b in at.button)


def test_dashboard_page_with_empty_progress():
    # Empty JSON object {} previously caused KeyError: "['answer_correct'] not in index"
    prog_file = Path("data/progress.json")
    prog_file.write_text("{}", encoding="utf-8")

    at = AppTest.from_file("🏠_Dashboard.py")
    at.run()
    assert not at.exception


def test_dashboard_page_with_single_attempt():
    # Single attempt previously caused slider min==max crash
    prog_file = Path("data/progress.json")
    prog_file.write_text(json.dumps({"104": True}), encoding="utf-8")

    at = AppTest.from_file("🏠_Dashboard.py")
    at.run()
    assert not at.exception


def test_gcp_products_page():
    at = AppTest.from_file("pages/2_☁️_GCP_Products.py")
    at.run()
    assert not at.exception


def test_export_for_lm_page():
    at = AppTest.from_file("pages/5_🇦🇮_Export_for_LM.py")
    at.run()
    assert not at.exception
    # Click export button
    export_btn = [b for b in at.button if "Export" in b.label][0]
    export_btn.click().run()
    assert not at.exception


def test_edit_questions_page():
    at = AppTest.from_file("pages/4_📝_Edit_Questions.py")
    at.run()
    assert not at.exception


def test_quiz_mode_full_flow():
    # Test taking a quiz in Quiz Mode
    at = AppTest.from_file("pages/3_🤔_Quiz_Mode.py")
    at.run()
    assert not at.exception

    # Click Start Round
    start_btn = [b for b in at.button if b.label == "Start Round"][0]
    start_btn.click().run()
    assert not at.exception
    assert at.session_state.quiz_in_progress is True
    assert len(at.session_state.quizzes) > 0

    # Answer current question
    q = at.session_state.quizzes[0]
    if q.mode == "single_choice":
        at.radio[0].set_value(q.options[0]).run()
    else:
        at.checkbox[0].check().run()

    # Submit answer
    submit_btn = [b for b in at.button if "Submit" in b.label][0]
    submit_btn.click().run()
    assert not at.exception
    assert at.session_state.quiz_mode_answered is True

    # Next question
    next_btn = [b for b in at.button if "Next Question" in b.label or "Skip" in b.label][0]
    next_btn.click().run()
    assert not at.exception
    assert at.session_state.quiz_mode_pos == 1
    assert at.session_state.quiz_mode_answered is False


def test_dashboard_start_button_switches_page():
    at = AppTest.from_file("🏠_Dashboard.py")
    at.run()
    assert not at.exception
    start_btn = [b for b in at.button if "Start" in b.label][0]
    start_btn.click().run()
    assert not at.exception
    # Verify navigation landed on Quiz Mode showing the "Start Round" button
    assert any("Start Round" in b.label for b in at.button)


def test_quiz_mode_round_completion_save():
    from models.questions import Question
    q = Question(id=9999, mode="single_choice", question="Test?", options=["A", "B"], answer=0)

    at = AppTest.from_file("pages/3_🤔_Quiz_Mode.py")
    at.session_state.quiz_in_progress = True
    at.session_state.quizzes = [q]
    at.session_state.quiz_mode_pos = 1  # pos >= len(quizzes), round complete
    at.session_state.quiz_mode_round_progress = {0: True}
    at.run()
    assert not at.exception

    save_btn = [b for b in at.button if "Save round results" in b.label][0]
    save_btn.click().run()
    assert not at.exception

    # Check progress was saved to progress.json
    prog_file = Path("data/progress.json")
    assert prog_file.exists()
    prog_data = json.loads(prog_file.read_text(encoding="utf-8"))
    assert prog_data.get("9999") is True
