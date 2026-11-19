# gui/staff_pages.py
import streamlit as st
import pandas as pd
from app.schedule import ScheduleManager
from gui.style import set_bg


def show_staff_management_page(manager: ScheduleManager):
    """Renders all components for the staff management page."""
    set_bg("assets/staff.jpg")
    st.header("👩‍🏫 Staff Management")

    # --- Our Teachers Section ---
    st.subheader("Our Teachers")
    if manager.teachers:
        staff_data = []
        for teacher in manager.teachers:
            # Find courses linked to this teacher ID
            taught_courses = [
                c.name for c in manager.courses if c.teacher_id == teacher.id
            ]
            staff_data.append(
                {
                    "Teacher ID": teacher.id,
                    "Name": teacher.name,
                    "Speciality": teacher.speciality,
                    "Courses Taught": (
                        ", ".join(taught_courses) if taught_courses else "None"
                    ),
                }
            )
        df = pd.DataFrame(staff_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No teachers found in the system.")

    # --- 2. Search Teacher Section ---
    st.subheader("Find a Teacher")
    search_teacher_id = st.number_input("Teacher ID", min_value=1, step=1)
    if st.button("Search Teacher"):
        teacher = manager.find_teacher_by_id(search_teacher_id)
        if teacher:
            st.success(f"Teacher found: {teacher.name}")
            st.write(f"**Teacher ID:** {teacher.id}")
            st.write(f"**Name:** {teacher.name}")
            st.write(f"**Speciality:** {teacher.speciality}")
            taught = [c.name for c in manager.courses if c.teacher_id == teacher.id]
            st.write(f"**Courses Taught:** {', '.join(taught) if taught else 'None'}")
        else:
            st.error(f"No teacher found with ID {search_teacher_id}.")

    # --- 3. Add New Teacher Section ---
    st.subheader("Add New Teacher")
    with st.form("add_teacher_form"):
        new_teacher_name = st.text_input("Teacher Name")
        new_teacher_speciality = st.text_input("Speciality (e.g., Piano, Guitar)")
        submitted = st.form_submit_button("Add Teacher")

        if submitted:
            if new_teacher_name.strip() and not manager.is_valid_name(new_teacher_name.strip()):
                st.error("Invalid name.")
            elif new_teacher_name.strip() and new_teacher_speciality.strip():
                # Calls add_teacher from ScheduleManager
                manager.add_teacher(
                    new_teacher_name.strip(), new_teacher_speciality.strip()
                )
                st.success(f"Successfully added teacher {new_teacher_name}!")
                st.rerun()
            else:
                st.warning("Please enter both a name and a speciality.")

    # --- 4. Remove a Teacher Section ---
    st.subheader("Remove a Teacher")
    if manager.teachers:
        with st.form("remove_teacher_form"):
            teacher_options = {f"{t.name} (ID: {t.id})": t.id for t in manager.teachers}
            selected_teacher_label = st.selectbox(
                "Select Teacher to Remove", options=list(teacher_options.keys())
            )
            remove_submitted = st.form_submit_button("Remove Teacher")

            if remove_submitted:
                teacher_id = teacher_options[selected_teacher_label]
                manager.remove_teacher(teacher_id)
                st.rerun()  # Refresh the page to show the updated list of teachers
    else:
        st.info("No teachers available to remove.")
