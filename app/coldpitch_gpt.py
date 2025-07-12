import streamlit as st
import openai
import os
import re

st.set_page_config(page_title='ColdCraft', layout='centered')
st.title('🧊 ColdCraft - Cold Email Generator')
st.write('Paste your lead info below and get a personalized cold email opener.')

# Get OpenAI key from secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Input form
raw_lead = st.text_area("🔍 Paste LinkedIn bio, job post, or context about your lead:", height=200)
lead = re.sub(r'\s+', ' ', raw_lead).strip().lower()  # Normalize whitespace, trim, lowercase

if st.button("✉️ Generate Cold Email"):
    if not lead:
        st.warning("Please enter some lead info first.")
    else:
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert cold outreach copywriter."},
                    {"role": "user", "content": f"Write a short, friendly cold email opener based on this lead: {lead}"}
                ],
                max_tokens=80,
                temperature=0.7
            )

            result = response.choices[0].message.content.strip()
            st.success("✅ Generated cold opener:")
            st.text(result)

        except Exception as e:
            st.error(f"Failed to generate message: {str(e)}")
