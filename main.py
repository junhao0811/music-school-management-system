# main.py
import streamlit as st
from gui.main_dashboard import launch
# Import the new admin utilities.
from app.admin_utils import init_logger, backup_data

if __name__ == "__main__":
    # Initialize the logger as the very first step.
    init_logger()

    # Perform a data backup before starting the application session.
    # Streamlit reruns this file on every click, so session_state makes sure
    # the backup only happens once per session instead of on every rerun.
    if "backup_done" not in st.session_state:
        backup_data()
        st.session_state.backup_done = True

    # Launch the GUI as before.
    launch()
