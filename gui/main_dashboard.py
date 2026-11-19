# gui/main_dashboard.py
import streamlit as st
from app.schedule import ScheduleManager
from gui.student_pages import show_student_management_page
from gui.roster_pages import show_roster_page
from gui.staff_pages import show_staff_management_page
from gui.finance_pages import show_finance_page
from app.admin_utils import backup_data

def launch():
    """Sets up the main Streamlit application window and navigation."""
    st.set_page_config(layout="wide", page_title="Music School Management System")

    # Instantiate the "brain" of our app ONCE and store it in the session state.
    # This is crucial so the manager object persists as we switch pages.
    if 'manager' not in st.session_state:
        st.session_state.manager = ScheduleManager()

    st.sidebar.title("MSMS Navigation")
    # Create a radio button menu in the sidebar for page navigation.
    page = st.sidebar.radio("Go to", ["Student Management", "Daily Roster", "Staff Management", "Finance & Payments"])

    # Manual backup button, in addition to the automatic backup at startup.
    st.sidebar.divider()
    if st.sidebar.button("💾 Backup Now"):
        if backup_data(st.session_state.manager.data_path):
            st.sidebar.success("Backup created in data/backups.")
        else:
            st.sidebar.error("Backup failed. See msms.log for details.")

    # Use an if/elif block to call the correct function to render the selected page.
    if page == "Student Management":
        show_student_management_page(st.session_state.manager)
    elif page == "Daily Roster":
        show_roster_page(st.session_state.manager)
    elif page == "Staff Management":
        show_staff_management_page(st.session_state.manager)
    elif page == "Finance & Payments":
        show_finance_page(st.session_state.manager)