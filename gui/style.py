import base64
import streamlit as st


def set_bg(image_file: str):
    with open(image_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <style> 
        .stApp {{
            background: linear-gradient(
                rgba(255, 255, 255, 0.5),
                rgba(255, 255, 255, 0.5)
            ), url("data:image/png;base64,{b64}") center center / cover no-repeat fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
