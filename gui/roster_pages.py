# gui/roster_pages.py
import streamlit as st
import pandas as pd
from app.schedule import ScheduleManager
from gui.style import set_bg

def show_roster_page(manager: ScheduleManager):
    """Renders the daily roster, check-in, course management, and lesson scheduling."""
    set_bg("assets/campus.jpg")
    st.header("📆 Daily Roster")

    # --- 1. View Daily Roster Section ---
    st.subheader("Daily Roster")
    day = st.selectbox("Select a day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])

    lessons = manager.get_lessons_for_day(day)
    
    # Display the lessons in a table format using pandas DataFrame
    if lessons:
        roster_data = []
        for course, lesson in lessons:
            roster_data.append({
                "Lesson ID": lesson["lesson_id"],
                "Course Name": course.name,
                "Day": lesson["day"],
                "Start Time": lesson["start_time"],
                "Room": lesson["room"]
            })
        df_roster = pd.DataFrame(roster_data)
        st.dataframe(df_roster, use_container_width=True, hide_index=True)
    else:
        st.info(f"No lessons scheduled for {day}.")
    
    # --- 2. Student Check-in Section ---
    st.subheader("Student Check-in")
    if manager.students:
        # The student is chosen outside the form so the course list below
        # refreshes immediately to show only that student's enrolled courses.
        student_list = {f"{s.name} (ID: {s.id})": s for s in manager.students}
        selected_student_label = st.selectbox(
            "Select Student", list(student_list.keys()), key="check_in_student"
        )
        selected_student = student_list[selected_student_label]

        course_list = {
            c.name: c.id for c in manager.courses
            if c.id in selected_student.enrolled_course_ids
        }

        if course_list:
            with st.form("check_in_form"):
                selected_course_name = st.selectbox("Select Course", list(course_list.keys()))
                submitted = st.form_submit_button("Check-in Student")

                if submitted:
                    course_id = course_list[selected_course_name]
                    # check_in() also validates enrolment on the backend.
                    success = manager.check_in(selected_student.id, course_id)
                    if success:
                        st.success(f"Checked in {selected_student.name} for {selected_course_name}!")
                    else:
                        st.error("Check-in failed. The student is not enrolled in this course.")
        else:
            st.info(f"{selected_student.name} is not enrolled in any courses yet.")
    else:
        st.info("No students available for check-in.")

    # --- 3. Courses Overview Table ---
    st.subheader("Courses Overview")
    if manager.courses:
        course_rows = []
        for c in manager.courses:
            teacher = manager.find_teacher_by_id(c.teacher_id)
            course_rows.append({
                "Course ID": c.id,
                "Title": c.name,
                "Instrument": c.instrument,
                "Teacher": teacher.name if teacher else "N/A",
                "Enrolled": len(c.enrolled_student_ids),
                "Lessons Count": len(c.lessons),
            })
        df_courses = pd.DataFrame(course_rows)
        st.dataframe(df_courses, use_container_width=True, hide_index=True)
    else:
        st.info("No courses currently registered.")

    # --- 4. Add New Course Section ---
    st.subheader("Add New Course")
    if manager.teachers:
        with st.form("add_course_form"):
            new_course_name = st.text_input("Course Title (e.g., Jazz Improvisation)")
            new_course_instrument = st.text_input("Instrument (e.g., Piano, Guitar)")
            teacher_mapping = {f"{t.name} ({t.speciality})": t.id for t in manager.teachers}
            assigned_teacher_label = st.selectbox("Assign Teacher", list(teacher_mapping.keys()))
            course_submitted = st.form_submit_button("Add Course")

            if course_submitted:
                if new_course_name.strip() and new_course_instrument.strip():
                    teacher_id = teacher_mapping[assigned_teacher_label]
                    new_course = manager.create_course(
                        new_course_name.strip(),
                        new_course_instrument.strip(),
                        teacher_id
                    )
                    st.success(f"Successfully created course '{new_course_name}'!")
                    st.balloons()
                else:
                    st.warning("Please provide both a course title and an instrument.")
    else:
        st.warning("Please add at least one teacher in Staff Management before creating a course.")

    # --- 5. Add / Schedule Lesson Section ---
    st.subheader("Schedule a Lesson")
    if manager.courses:
        with st.form("add_lesson_form"):
            course_selection_map = {f"{c.name} (ID: {c.id})": c.id for c in manager.courses}
            selected_course_for_lesson = st.selectbox("Select Course", list(course_selection_map.keys()))
            lesson_day = st.selectbox("Day of Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
            start_time = st.text_input("Start Time (e.g., 16:00)", value="16:00")
            room_name = st.text_input("Room (e.g., Room A)", value="Room A")
            lesson_submitted = st.form_submit_button("Schedule Lesson")

            if lesson_submitted:
                if start_time.strip() and room_name.strip():
                    target_course_id = course_selection_map[selected_course_for_lesson]
                    manager.add_lesson(
                        target_course_id,
                        lesson_day,
                        start_time.strip(),
                        room_name.strip()
                    )
                    st.success(f"Scheduled lesson for {selected_course_for_lesson} on {lesson_day} at {start_time} in {room_name}!")
                else:
                    st.warning("Please enter both a start time and room.")
    else:
        st.info("No courses available to schedule lessons for.")

    # --- 6. Cancel Lesson Section ---
    st.subheader("Cancel a Lesson")
    lesson_options = {
        f"{course.name} - {lesson['day']} {lesson['start_time']} in {lesson['room']} (Lesson ID: {lesson['lesson_id']})": lesson["lesson_id"]
        for course in manager.courses
        for lesson in course.lessons
    }
    if lesson_options:
        with st.form("cancel_lesson_form"):
            selected_lesson_label = st.selectbox("Select Lesson", list(lesson_options.keys()))
            cancel_reason = st.text_input("Reason for Cancellation (e.g., Teacher unavailable)")
            cancel_submitted = st.form_submit_button("Cancel Lesson")

            if cancel_submitted:
                if cancel_reason.strip():
                    if manager.cancel_lesson(lesson_options[selected_lesson_label], cancel_reason.strip()):
                        st.success(f"Cancelled {selected_lesson_label}.")
                    else:
                        st.error("Lesson could not be cancelled.")
                else:
                    st.warning("Please enter a reason for cancelling the lesson.")
    else:
        st.info("No lessons scheduled to cancel.")