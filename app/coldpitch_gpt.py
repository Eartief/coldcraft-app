import streamlit as st
import openai
import os
import re
import time

st.set_page_config(page_title='ColdCraft', layout='centered')
st.title('🧊 ColdCraft - Cold Email Generator')
st.write('Paste your lead info below and get a personalized cold email opener.')

# Get OpenAI key from secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Input form
raw_lead = st.text_area("🔍 Paste LinkedIn bio, job post, or context about your lead:", height=200)
company = st.text_input("🏢 Company Name (optional):")
job_title = st.text_input("💼 Job Title (optional):")
style = st.selectbox("✍️ Choose a tone/style: ", ["Friendly", "Professional", "Funny", "Bold", "Casual"])
lead = re.sub(r'\s+', ' ', raw_lead).strip().lower()  # Normalize whitespace, trim, lowercase

if len(lead) > 500:
    st.warning("⚠️ Lead info is too long. Please keep it under 500 characters.")

elif st.button("✉️ Generate Cold Email"):
    if not lead:
        st.warning("Please enter some lead info first.")
    else:
        start_time = time.time()
        try:
            prompt = f"Write 3 short, {style.lower()} cold email openers based on this lead: {lead}."
            if company:
                prompt += f" The company name is {company}."
            if job_title:
                prompt += f" The job title is {job_title}."

            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert cold outreach copywriter."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=180,
                temperature=0.7
            )

            result = response.choices[0].message.content.strip()
            duration = round(time.time() - start_time, 2)
            st.success("✅ Generated cold openers:")
            st.text(result)
            st.caption(f"⏱️ Generated in {duration} seconds | 📏 {len(result)} characters")

            st.download_button("📋 Copy to Clipboard", result, "cold_openers.txt")

        except Exception as e:
            st.error(f"Failed to generate message: {str(e)}")
