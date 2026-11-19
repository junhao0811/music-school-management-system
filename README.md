# 🎵 Music School Management System

A **Streamlit** web app for running a music school day to day: student enrolments, teachers, courses, the daily lesson roster with check-ins, payments, and CSV reports, all backed by a tested business-logic layer.

---

## ✨ Features

| Area | What you can do |
|---|---|
| 🧑‍🎤 **Students** | View all students and their courses, search by student ID, register new students straight into a course, enrol, unenrol and remove (with confirmation) |
| 📆 **Daily roster** | See the day's lessons, check students in (only for courses they're enrolled in), create courses, schedule lessons, cancel lessons with a reason |
| 👩‍🏫 **Staff** | View, search, add and remove teachers. Removing a teacher unassigns their courses |
| 💰 **Finance** | Record payments with a method, view a student's payment history and total, export finance or attendance reports to CSV |
| 🛡️ **Admin** | Every important action is logged, the data is backed up automatically each session, plus a one-click **Backup Now** |

---

## 🏗️ Design

The app follows **Model–View–Controller**:

| Layer | Responsibility |
|---|---|
| **Model** | `User`, `StudentUser`, `TeacherUser` and `Course` hold the data |
| **Controller** | `ScheduleManager` owns every rule: validation, enrolment, check-ins, finance, reports and saving to JSON |
| **View** | The Streamlit pages in `gui/` only display data and collect input, then call the controller |

Because all the rules live in `ScheduleManager`, they're fully testable without the UI, and the UI can never bypass a rule.

**Robustness built in:**
- Input validation: names (2–50 characters, sensible characters only), positive payment amounts, 8-digit student IDs, no duplicate enrolments
- Data integrity: student↔course links are re-synced on load, and links to deleted records are cleaned up
- Graceful failures: rejected actions return `False`/`None` and log a warning instead of crashing; a missing data file starts the app empty
- Sequential 8-digit student IDs that carry on correctly after a restart

The app was built up in five iterations: an in-memory command-line prototype, then JSON persistence, an object-oriented refactor, the GUI, and finally finance, reporting, logging, backups and the test suite.

---

## ✅ Tests

```bash
pip install streamlit pandas pytest
pytest            # 55 tests, all passing
```

The suite covers the controller's business rules using pytest **fixtures**, `tmp_path`, `parametrize`, `monkeypatch`, `mock.patch` and `caplog`.

## 🚀 Run it

```bash
pip install streamlit pandas
streamlit run main.py
```

Data is stored in `data/msms.json`. Logs (`msms.log`), backups (`data/backups/`) and exported reports (`reports/`) are created while the app runs.

---

## 📁 Project structure

```
main.py              entry point: logging, start-up backup, launch the UI
gui/                 Streamlit pages: students, roster, staff, finance, styling
app/
  schedule.py        ScheduleManager: all business logic and persistence
  user.py, student.py, teacher.py   data models
  admin_utils.py     logging and backups
data/msms.json       saved students, teachers, courses, lessons, attendance, payments
tests/               pytest suite
assets/              background images
```

## 🛠️ Tech
Python · Streamlit · pandas · pytest · MVC architecture · JSON persistence
