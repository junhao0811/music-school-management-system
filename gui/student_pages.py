# gui/student_pages.py
import streamlit as st
import pandas as pd
from app.schedule import ScheduleManager
from app.student import StudentUser
from gui.style import set_bg

def show_student_management_page(manager: ScheduleManager):
    """Renders all components for the student management page."""
    set_bg("assets/music_instruments.jpg")
    st.header("🧑🏼‍🎤 Student Management")

    # --- 1. Student Overview Section ---
    st.subheader("All Students")
    if manager.students:
        student_rows = []
        for s in manager.students:
            enrolled_names = [c.name for c in manager.courses if c.id in s.enrolled_course_ids]
            student_rows.append({
                "Student ID": s.id,
                "Name": s.name,
                "Enrolled Courses": ", ".join(enrolled_names) if enrolled_names else "None",
                "Total Courses": len(s.enrolled_course_ids),
            })
        df_students = pd.DataFrame(student_rows)
        st.dataframe(df_students, use_container_width=True, hide_index=True)
    else:
        st.info("No students found in the system.")

    # --- 2. Search Section ---
    st.subheader("Find a Student")
    student_id_text = st.text_input("Student ID")

    if st.button("Search Student"):
        # Validate the 8-digit format before searching.
        entered = student_id_text.strip()
        student_id = int(entered) if entered.isdigit() else None
        student: StudentUser = manager.find_student_by_id(student_id)
        if not manager.is_valid_student_id(student_id):
            st.error("Please enter a valid 8-digit student ID.")
        elif student:
            st.success(f"Student found: {student.name}")
            st.write(f"**Student ID:** {student.id}")
            st.write(f"**Name:** {student.name}")

            if student.enrolled_course_ids:
                enrolled_courses = [
                    f"{c.name} (ID: {c.id})"
                    for c in manager.courses
                    if c.id in student.enrolled_course_ids
                ]
                st.write(f"**Enrolled Courses:** {', '.join(enrolled_courses)}")
            else:
                st.write("**Enrolled Courses:** None")
        else:
            st.error(f"No student found with ID {student_id}.")

    # --- 3. Registration Section ---
    st.subheader("Register New Student")
    if manager.courses:
        with st.form("registration_form"):
            reg_name = st.text_input("New Student Name")
            # Registration is linked to a specific course instead of a free-text instrument.
            reg_course_options = {f"{c.name} ({c.instrument})": c.id for c in manager.courses}
            reg_course_label = st.selectbox("First Course", list(reg_course_options.keys()))
            submitted = st.form_submit_button("Register Student")

            if submitted:
                if not reg_name.strip():
                    st.warning("Please enter the student's name.")
                elif not manager.is_valid_name(reg_name.strip()):
                    st.error("Invalid name.")
                else:
                    new_student = manager.register_new_student(
                        reg_name.strip(), reg_course_options[reg_course_label]
                    )
                    if new_student:
                        st.success(
                            f"Successfully registered {new_student.name} "
                            f"(ID: {new_student.id}) in {reg_course_label}!"
                        )
                        st.balloons()
                    else:
                        st.error("Could not register student. Please check the details.")
    else:
        st.info("Please create a course before registering students.")

    # --- 4. Enrol Existing Student Section ---
    st.subheader("Enrol Existing Student in Course")
    if manager.students and manager.courses:
        with st.form("enrol_student_form"):
            student_options = {f"{s.name} (ID: {s.id})": s.id for s in manager.students}
            course_options = {f"{c.name} ({c.instrument})": c.id for c in manager.courses}

            selected_student_label = st.selectbox("Select Student", list(student_options.keys()))
            selected_course_label = st.selectbox("Select Course", list(course_options.keys()))
            confirm_enrol = st.checkbox("Confirm enrolment")
            enrol_submitted = st.form_submit_button("Enrol Student")

            if enrol_submitted:
                if not confirm_enrol:
                    st.info("Please check the confirmation box.")
                else:
                    sid = student_options[selected_student_label]
                    cid = course_options[selected_course_label]
                    success = manager.enrol_student(sid, cid)
                    if success:
                        st.success(f"Successfully enrolled {selected_student_label} in {selected_course_label}!")
                    else:
                        st.warning("Student is already enrolled in this course.")
    else:
        st.info("Need at least one student and one course to enrol.")

    # --- 5. Unenrol Student Section ---
    st.subheader("Unenrol Student from Course")
    if manager.courses:
        course_options = {f"{c.name} ({c.instrument})": c for c in manager.courses}
        selected_course_label = st.selectbox(
            "Select Course to Manage",
            list(course_options.keys()),
            key="unenrol_course_select"
        )
        selected_course = course_options[selected_course_label]

        # Find all students currently enrolled in this course
        enrolled_students = [
            s for s in manager.students
            if s.id in selected_course.enrolled_student_ids
        ]

        if enrolled_students:
            with st.form("unenrol_student_form"):
                student_remove_options = {
                    f"{s.name} (ID: {s.id})": s.id for s in enrolled_students
                }
                selected_remove_student = st.selectbox(
                    "Select Student to Remove",
                    list(student_remove_options.keys())
                )
                unenrol_submitted = st.form_submit_button("Unenrol Student")

                if unenrol_submitted:
                    sid_to_remove = student_remove_options[selected_remove_student]
                    manager.unenrol_student(sid_to_remove, selected_course.id)
                    st.success(f"Successfully unenrolled {selected_remove_student} from {selected_course.name}!")
        else:
            st.info(f"No students currently enrolled in {selected_course.name}.")
    else:
        st.info("No courses available.")

    # --- 6. Remove a Student Section ---
    st.subheader("Remove a Student")
    if manager.students:
        with st.form("remove_student_form"):
            student_remove_options = {f"{s.name} (ID: {s.id})": s.id for s in manager.students}
            selected_student_to_delete = st.selectbox(
                "Select Student to Delete",
                list(student_remove_options.keys())
            )
            confirm_deletion = st.checkbox("Confirm deletion")
            delete_submitted = st.form_submit_button("Delete Student")

            if delete_submitted:
                if confirm_deletion:
                    sid_to_delete = student_remove_options[selected_student_to_delete]
                    manager.remove_student(sid_to_delete)
                    st.success(f"Deleted {selected_student_to_delete} and cleaned course enrolments.")
                else:
                    st.warning("Please check the confirmation box to delete.")
    else:
        st.info("No students available to remove.")