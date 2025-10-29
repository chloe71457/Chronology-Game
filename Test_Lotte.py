import streamlit as st

st.set_page_config(page_title="My Website", page_icon="🌐", layout="centered")

st.title("Welcome to My Website!")
st.write("This is a simple frontend for my Python code.")

name = st.text_input("Enter your name:")
if st.button("Say Hello"):
    st.success(f"Hello, {name}!")

st.write("You can add charts, tables, or other widgets below.")
