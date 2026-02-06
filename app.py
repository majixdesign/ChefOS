import streamlit as st
import google.generativeai as genai
import sys

st.title("👨‍⚕️ ChefOS Diagnostic")

# 1. Check Python & Library Version
st.subheader("1. System Vitals")
st.write(f"**Python Version:** {sys.version.split()[0]}")
try:
    st.write(f"**GenAI Library Version:** {genai.__version__}")
except:
    st.error("GenAI Library version not found (Library is too old!)")

# 2. Check Connection & Models
st.subheader("2. Available Models")
api_key = st.secrets["GOOGLE_API_KEY"]

if api_key:
    genai.configure(api_key=api_key)
    try:
        models = [m.name for m in genai.list_models()]
        st.success(f"Connection Successful! Found {len(models)} models.")
        st.code(models)
    except Exception as e:
        st.error(f"Connection Failed: {e}")
else:
    st.error("API Key not found in Secrets.")