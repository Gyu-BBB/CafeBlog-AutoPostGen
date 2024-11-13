import streamlit as st

st.title("Hello, Streamlit!")
st.write("Welcome to my first Streamlit app.")

# 간단한 입력 예시
name = st.text_input("Enter your name")
st.write(f"Hello, {name}!")

# 간단한 슬라이더
age = st.slider("Select your age", 0, 100)
st.write(f"You are {age} years old.")
