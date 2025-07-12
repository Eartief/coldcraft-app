# app/coldpitch_gpt.py

import streamlit as st
import openai
import os

st.set_page_config(page_title="ColdCraft", page_icon="📬", layout="centered")

# UI: Title & Description
st.title("📬 ColdCraft - Cold Email Generator")
st.write("Paste your lead info below and get a personalized cold email opener.")

# UI: Input Text
lead_text = st.text_area("🔎 Paste LinkedIn bio, job post, or context about your lead:")

# UI: Length selector
length = st.radio("✍️ Choose opener length:", ["Short", "Medium", "Long"], horizontal=True)

# Generate button
generate_clicked = st.button("🚀 Generate Cold Email")

# Load API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Map length to prompt instruction
length_instruction = {
    "Short": "Write 1 short cold email opener.",
    "Medium": "Write 3 medium cold email openers.",
    "Long": "Write a longer, more detailed cold opener with personality."
}[length]

# Handle generation
if generate_clicked and lead_text:
    with st.spinner("Generating..."):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You're an expert B2B cold email copywriter."},
                    {"role": "user", "content": f"{length_instruction}\n\nHere’s the lead info:\n{lead_text}"}
                ]
            )
            output = response.choices[0].message.content.strip()
            st.success("✅ Generated cold openers:")
            st.markdown(output)
        except Exception as e:
            st.error(f"❌ Error: {e}")
