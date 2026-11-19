# tests/test_schedule_manager.py
import datetime
import json
import logging
import os
from unittest.mock import patch

import pytest

from app.schedule import ScheduleManager
from app.admin_utils import backup_data


# A pytest fixture creates a clean environment for each test function.
@pytest.fixture
def fresh_manager(tmp_path):
    """Creates a fresh ScheduleManager instance using a temporary test data file."""
    # ARRANGE: tmp_path is a new empty folder for every test, so no old test file exists.
    test_file = tmp_path / "test_data.json"
    return ScheduleManager(data_path=str(test_file))


@pytest.fixture
def seeded_manager(fresh_manager):
    """A manager with one teacher, two courses and one student enrolled in course 1."""
    fresh_manager.add_teacher("Evelyn Keys", "Piano")
    fresh_manager.create_course("Beginner Piano", "Piano", 1)
    fresh_manager.create_course("Jazz Guitar", "Guitar", 1)
    fresh_manager.register_new_student("Jun Hao", 1)
    return fresh_manager


def test_create_course(fresh_manager):
    # ARRANGE: A course needs an existing teacher.
    fresh_manager.add_teacher("Evelyn Keys", "Piano")
    # ACT: Call the method we want to test.
    fresh_manager.create_course("Beginner Piano", "Piano", 1)
    # ASSERT: Check if the outcome is what we expect.
    assert len(fresh_manager.courses) == 1
    assert fresh_manager.courses[0].name == "Beginner Piano"


def test_record_payment_and_history(seeded_manager):
    # ARRANGE: The seeded manager already has a student registered.
    # This test verifies the core financial logic you added in Fragment 5.1.
    student_id_to_test = seeded_manager.students[0].id

    # ACT: Record a payment for that student.
    seeded_manager.record_payment(student_id_to_test, 100.00, "Credit Card")

    # ACT 2: Get the payment history.
    history = seeded_manager.get_payment_history(student_id_to_test)

    # ASSERT: Check the results.
    assert len(history) == 1
    assert history[0]['amount'] == 100.00
    assert history[0]['method'] == "Credit Card"


def test_get_payment_history_no_results(seeded_manager):
    # ARRANGE: A student who has never paid.
    student_id = seeded_manager.students[0].id
    # ACT
    history = seeded_manager.get_payment_history(student_id)
    # ASSERT: An empty list, not None or an error.
    assert history == []


# --- Student IDs ---

def test_first_student_id_is_10000000(seeded_manager):
    # ARRANGE / ACT: done by the fixture.
    # ASSERT
    assert seeded_manager.students[0].id == 10000000


def test_student_ids_go_up_by_one(seeded_manager):
    # ACT
    second = seeded_manager.register_new_student("Alice Johnson", 1)
    # ASSERT
    assert second.id == 10000001


def test_student_ids_continue_after_reload(seeded_manager):
    # ARRANGE: Reload the same data file in a new manager.
    reloaded = ScheduleManager(data_path=seeded_manager.data_path)
    # ACT
    student = reloaded.register_new_student("Alice Johnson", 1)
    # ASSERT: Carries on from the highest saved ID.
    assert student.id == 10000001


@pytest.mark.parametrize("student_id, expected", [
    (10000000, True),
    (12345678, True),
    (99999999, True),
    (9999999, False),     # only 7 digits
    (100000000, False),   # 9 digits
    ("12345678", False),  # a string, not an int
    (True, False),        # bool is a subclass of int
])
def test_is_valid_student_id(student_id, expected):
    # ACT / ASSERT
    assert ScheduleManager.is_valid_student_id(student_id) == expected


# --- Names and registration ---

@pytest.mark.parametrize("name, expected", [
    ("Jun Hao", True),
    ("Mary-Jane O'Neil", True),
    ("Dr. Smith", True),
    ("", False),
    ("   ", False),
    ("A", False),
    ("John123", False),
    ("A" * 51, False),
])
def test_is_valid_name(name, expected):
    # ACT / ASSERT
    assert ScheduleManager.is_valid_name(name) == expected


def test_register_links_student_and_course(seeded_manager):
    # ARRANGE
    student = seeded_manager.students[0]
    course = seeded_manager.find_course_by_id(1)
    # ASSERT: The link is stored on both sides.
    assert student.enrolled_course_ids == [1]
    assert course.enrolled_student_ids == [student.id]


def test_register_rejects_unknown_course(seeded_manager):
    # ACT
    student = seeded_manager.register_new_student("Alice Johnson", 999)
    # ASSERT: Nothing is created.
    assert student is None
    assert len(seeded_manager.students) == 1


def test_register_rejects_invalid_name(seeded_manager):
    # ACT
    student = seeded_manager.register_new_student("123", 1)
    # ASSERT
    assert student is None
    assert len(seeded_manager.students) == 1


# --- Check-in ---

def test_check_in_enrolled_student(seeded_manager):
    # ARRANGE
    student_id = seeded_manager.students[0].id
    # ACT
    result = seeded_manager.check_in(student_id, 1)
    # ASSERT
    assert result is True
    assert len(seeded_manager.attendance_log) == 1
    assert seeded_manager.attendance_log[0]["course_id"] == 1


def test_check_in_rejects_student_not_enrolled(seeded_manager):
    # ARRANGE: The student is only enrolled in course 1.
    student_id = seeded_manager.students[0].id
    # ACT
    result = seeded_manager.check_in(student_id, 2)
    # ASSERT: Rejected and nothing is logged.
    assert result is False
    assert seeded_manager.attendance_log == []


def test_check_in_rejects_unknown_ids(seeded_manager):
    # ACT / ASSERT
    assert seeded_manager.check_in(99999999, 1) is False
    assert seeded_manager.check_in(seeded_manager.students[0].id, 999) is False


# --- Enrolment and switching ---

def test_enrol_twice_is_rejected(seeded_manager):
    # ARRANGE
    student_id = seeded_manager.students[0].id
    # ACT
    result = seeded_manager.enrol_student(student_id, 1)
    # ASSERT: No duplicate on either side.
    assert result is False
    assert seeded_manager.students[0].enrolled_course_ids == [1]
    assert seeded_manager.find_course_by_id(1).enrolled_student_ids == [student_id]


def test_unenrol_student(seeded_manager):
    # ARRANGE
    student_id = seeded_manager.students[0].id
    # ACT
    result = seeded_manager.unenrol_student(student_id, 1)
    # ASSERT
    assert result is True
    assert seeded_manager.students[0].enrolled_course_ids == []
    assert seeded_manager.find_course_by_id(1).enrolled_student_ids == []


def test_switch_student_course(seeded_manager):
    # ARRANGE
    student_id = seeded_manager.students[0].id
    # ACT
    result = seeded_manager.switch_student_course(student_id, 1, 2)
    # ASSERT: Moved on both sides.
    assert result is True
    assert seeded_manager.students[0].enrolled_course_ids == [2]
    assert seeded_manager.find_course_by_id(1).enrolled_student_ids == []
    assert seeded_manager.find_course_by_id(2).enrolled_student_ids == [student_id]


def test_switch_course_with_inconsistent_data(seeded_manager):
    # ARRANGE: Course 1 has "lost" the student, but the student still lists course 1.
    student_id = seeded_manager.students[0].id
    seeded_manager.find_course_by_id(1).enrolled_student_ids.clear()
    # ACT: Should not crash with a ValueError from list.remove().
    result = seeded_manager.switch_student_course(student_id, 1, 2)
    # ASSERT
    assert result is True
    assert seeded_manager.students[0].enrolled_course_ids == [2]
    assert seeded_manager.find_course_by_id(2).enrolled_student_ids == [student_id]


def test_switch_rejected_when_not_in_from_course(seeded_manager):
    # ARRANGE
    student_id = seeded_manager.students[0].id
    # ACT: The student is not in course 2, so they can't switch out of it.
    result = seeded_manager.switch_student_course(student_id, 2, 1)
    # ASSERT: Nothing changed.
    assert result is False
    assert seeded_manager.students[0].enrolled_course_ids == [1]


def test_load_repairs_one_sided_links(tmp_path):
    # ARRANGE: A JSON file where only the student side has the link.
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps({
        "students": [{"id": 10000000, "name": "Jun Hao", "enrolled_course_ids": [1]}],
        "teachers": [{"id": 1, "name": "Evelyn Keys", "speciality": "Piano"}],
        "courses": [{"id": 1, "name": "Beginner Piano", "instrument": "Piano",
                     "teacher_id": 1, "enrolled_student_ids": [], "lessons": []}],
    }))
    # ACT
    manager = ScheduleManager(data_path=str(data_file))
    # ASSERT: The missing course side is filled in.
    assert manager.find_course_by_id(1).enrolled_student_ids == [10000000]


# --- Removing ---

def test_remove_student_cleans_up_courses(seeded_manager):
    # ARRANGE
    student_id = seeded_manager.students[0].id
    # ACT
    seeded_manager.remove_student(student_id)
    # ASSERT
    assert seeded_manager.find_student_by_id(student_id) is None
    assert seeded_manager.find_course_by_id(1).enrolled_student_ids == []


# --- Lessons ---

def test_add_and_cancel_lesson(seeded_manager):
    # ARRANGE
    lesson = seeded_manager.add_lesson(1, "Monday", "16:00", "Room A")
    # ACT
    result = seeded_manager.cancel_lesson(lesson["lesson_id"], "Teacher unavailable")
    # ASSERT
    assert result is True
    assert seeded_manager.get_lessons_for_day("Monday") == []


def test_cancel_unknown_lesson(seeded_manager):
    # ACT / ASSERT
    assert seeded_manager.cancel_lesson(999, "No reason") is False


# --- Finance ---

@pytest.mark.parametrize("amount", [0, -50, "100", None, True])
def test_record_payment_rejects_invalid_amount(seeded_manager, amount):
    # ARRANGE
    student_id = seeded_manager.students[0].id
    # ACT
    result = seeded_manager.record_payment(student_id, amount, "Cash")
    # ASSERT
    assert result is None
    assert seeded_manager.finance_log == []


def test_record_payment_rejects_unknown_student(seeded_manager):
    # ACT / ASSERT
    assert seeded_manager.record_payment(99999999, 100, "Cash") is None
    assert seeded_manager.finance_log == []


def test_record_payment_rejects_blank_method(seeded_manager):
    # ACT / ASSERT
    assert seeded_manager.record_payment(seeded_manager.students[0].id, 100, "  ") is None
    assert seeded_manager.finance_log == []


def test_record_payment_timestamp(seeded_manager, monkeypatch):
    # ARRANGE: Freeze the clock with monkeypatch so the timestamp is predictable.
    class FixedDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 1, 9, 30, 0)

    monkeypatch.setattr(datetime, "datetime", FixedDatetime)
    # ACT
    record = seeded_manager.record_payment(seeded_manager.students[0].id, 50, "Cash")
    # ASSERT
    assert record["timestamp"] == "2026-10-01T09:30:00"


def test_payments_are_saved(seeded_manager):
    # ARRANGE
    student_id = seeded_manager.students[0].id
    seeded_manager.record_payment(student_id, 80.5, "Bank Transfer")
    # ACT: Load the same file in a new manager.
    reloaded = ScheduleManager(data_path=seeded_manager.data_path)
    # ASSERT
    assert reloaded.get_payment_history(student_id)[0]["amount"] == 80.5


# --- CSV reports ---

def test_export_finance_report(seeded_manager, tmp_path):
    # ARRANGE
    seeded_manager.record_payment(seeded_manager.students[0].id, 100, "Cash")
    out_path = tmp_path / "reports" / "finance.csv"
    # ACT
    result = seeded_manager.export_report("finance", str(out_path))
    # ASSERT: The folder is created and the CSV has a header plus one row.
    assert result is True
    lines = out_path.read_text().splitlines()
    assert lines[0] == "student_id,amount,method,timestamp"
    assert len(lines) == 2


def test_export_attendance_report(seeded_manager, tmp_path):
    # ARRANGE
    seeded_manager.check_in(seeded_manager.students[0].id, 1)
    out_path = tmp_path / "attendance.csv"
    # ACT
    result = seeded_manager.export_report("attendance", str(out_path))
    # ASSERT
    assert result is True
    assert out_path.read_text().splitlines()[0] == "student_id,course_id,timestamp"


def test_export_unknown_report_kind(seeded_manager, tmp_path):
    # ARRANGE
    out_path = tmp_path / "unknown.csv"
    # ACT
    result = seeded_manager.export_report("salary", str(out_path))
    # ASSERT: No file is written.
    assert result is False
    assert not out_path.exists()


# --- Persistence ---

def test_missing_data_file_starts_clean(fresh_manager):
    # ASSERT: No crash, just empty lists.
    assert fresh_manager.students == []
    assert fresh_manager.courses == []
    assert fresh_manager.finance_log == []


def test_save_and_load_round_trip(seeded_manager):
    # ACT
    reloaded = ScheduleManager(data_path=seeded_manager.data_path)
    # ASSERT
    assert [s.name for s in reloaded.students] == ["Jun Hao"]
    assert [c.name for c in reloaded.courses] == ["Beginner Piano", "Jazz Guitar"]
    assert reloaded.students[0].enrolled_course_ids == [1]


# --- Backups and logging ---

def test_backup_data_creates_copy(seeded_manager, tmp_path):
    # ARRANGE
    backup_dir = tmp_path / "backups"
    # ACT
    result = backup_data(seeded_manager.data_path, str(backup_dir))
    # ASSERT
    assert result is True
    assert len(os.listdir(backup_dir)) == 1


def test_backup_data_missing_file(tmp_path):
    # ACT
    result = backup_data(str(tmp_path / "missing.json"), str(tmp_path / "backups"))
    # ASSERT
    assert result is False


def test_backup_data_copy_failure_is_logged(seeded_manager, tmp_path, caplog):
    # ARRANGE: Use mock to make shutil.copy fail.
    with patch("app.admin_utils.shutil.copy", side_effect=OSError("disk full")):
        # ACT
        with caplog.at_level(logging.ERROR):
            result = backup_data(seeded_manager.data_path, str(tmp_path / "backups"))
    # ASSERT: Returns False instead of crashing, and the error is logged.
    assert result is False
    assert "disk full" in caplog.text


def test_payment_is_logged(seeded_manager, caplog):
    # ACT
    with caplog.at_level(logging.INFO):
        seeded_manager.record_payment(seeded_manager.students[0].id, 100, "Cash")
    # ASSERT
    assert "Payment of 100 recorded" in caplog.text


def test_rejected_check_in_is_logged(seeded_manager, caplog):
    # ACT
    with caplog.at_level(logging.WARNING):
        seeded_manager.check_in(seeded_manager.students[0].id, 2)
    # ASSERT
    assert "not enrolled" in caplog.text
