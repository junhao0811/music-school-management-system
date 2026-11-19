# gui/finance_pages.py
import os
import streamlit as st
import pandas as pd
from app.schedule import ScheduleManager
from gui.style import set_bg

PAYMENT_METHODS = ["Cash", "Credit Card", "Debit Card", "Bank Transfer", "E-Wallet"]

def show_finance_page(manager: ScheduleManager):
    """Renders the UI for all financial operations."""
    set_bg("assets/money.jpg")
    st.header("💰 Finance & Payments")

    # Stop here if there are no students, otherwise the selectboxes below are empty.
    if not manager.students:
        st.info("No students found. Register a student before recording payments.")
        return

    # --- Section 1: Record a Payment ---
    st.subheader("Record New Payment")
    with st.form("payment_form"):
        # Create a selectbox to choose a student (e.g., from a list of names).
        student_list = {s.name: s.id for s in manager.students}
        selected_student_name = st.selectbox("Select Student", student_list.keys())

        # Create a number_input for amount and a selectbox for method.
        amount = st.number_input("Payment Amount ($)", min_value=0.01, format="%.2f")
        method = st.selectbox("Payment Method", PAYMENT_METHODS)

        submitted = st.form_submit_button("Record Payment")
        if submitted:
            student_id = student_list[selected_student_name]
            # Call manager.record_payment() and show a success message.
            # record_payment() returns None if validation fails.
            # Round to 2 decimal places so money is stored as dollars and cents.
            if manager.record_payment(student_id, round(amount, 2), method):
                st.success(f"Payment of ${amount:.2f} for {selected_student_name} recorded.")
            else:
                st.error("Payment could not be recorded. Please check the details.")

    # --- Section 2: View Payment History ---
    st.subheader("View Student Payment History")
    # Create a selectbox to choose a student.
    history_student_name = st.selectbox("Select Student to View History", student_list.keys())
    if history_student_name:
        history_student_id = student_list[history_student_name]
        # Call manager.get_payment_history().
        history = manager.get_payment_history(history_student_id)
        if history:
            # Convert the list of dictionaries to a pandas DataFrame and display it.
            df = pd.DataFrame(history)
            # Display amounts as money, e.g. $250.00.
            df["amount"] = df["amount"].map(lambda a: f"${a:.2f}")
            st.dataframe(df)
            st.metric("Total Paid", f"${sum(p['amount'] for p in history):.2f}")
        else:
            st.info("This student has no payment history.")

    # --- Section 3: Export Reports ---
    st.subheader("Export Reports")
    with st.form("export_form"):
        # Values stay lowercase for export_report(); format_func shows them capitalised.
        report_kind = st.selectbox("Report Type", ["finance", "attendance"], format_func=str.title)
        export_submitted = st.form_submit_button("Export to CSV")

    if export_submitted:
        out_path = os.path.join("reports", f"{report_kind}_report.csv")
        if manager.export_report(report_kind, out_path):
            st.success(f"{report_kind.title()} report saved to {out_path}.")
            with open(out_path, "rb") as f:
                st.download_button(
                    "Download CSV",
                    data=f.read(),
                    file_name=os.path.basename(out_path),
                    mime="text/csv",
                    on_click="ignore",
                )
        else:
            st.error("Report could not be exported.")
