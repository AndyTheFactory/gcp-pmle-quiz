import json
from pathlib import Path
from utils import compute_stats, fix_image_src, load_progress, load_quizzes, reset_progress, save_progress


def test_compute_stats():
    progress = {1: True, 2: False, 3: True}
    asked, correct, wrong, pct = compute_stats(progress)
    assert asked == 3
    assert correct == 2
    assert wrong == 1
    assert abs(pct - 66.666) < 0.01

    asked, correct, wrong, pct = compute_stats({})
    assert asked == 0
    assert correct == 0
    assert wrong == 0
    assert pct == 0.0


def test_fix_image_src():
    raw_html = '<p><img src="app/static/images/image_exp_107_0.png"/></p>'
    fixed = fix_image_src(raw_html)
    assert 'src="/app/static/images/image_exp_107_0.png"' in fixed

    already_fixed = '<p><img src="/app/static/images/image_exp_107_0.png"/></p>'
    assert fix_image_src(already_fixed) == already_fixed

    assert fix_image_src("") == ""
    assert fix_image_src(None) is None


def test_load_save_reset_progress(tmp_path, monkeypatch):
    test_prog_file = tmp_path / "progress.json"
    monkeypatch.setattr("utils.PROGRESS_FILE", test_prog_file)

    # Missing file
    assert load_progress() == {}

    # Save
    data = {103: True, 104: False}
    save_progress(data)
    assert test_prog_file.exists()

    # Load
    loaded = load_progress()
    assert loaded == {103: True, 104: False}

    # Reset
    reset_progress()
    assert not test_prog_file.exists()
    assert load_progress() == {}


def test_load_quizzes():
    incorrect, unanswered, correct = load_quizzes({103: True, 104: False})
    assert any(q.id == 103 for q in correct)
    assert any(q.id == 104 for q in incorrect)
    assert all(q.id not in (103, 104) for q in unanswered)
