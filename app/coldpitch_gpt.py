import streamlit as st
import openai
import os
import re
import time

st.set_page_config(page_title='ColdCraft', layout='centered')
st.title('🧊 ColdCraft - Cold Email Generator')
st.write('Paste your lead info below and get a personalized cold email opener.')

openai.api_key = st.secrets["OPENAI_API_KEY"]

raw_lead = st.text_area("🔍 Paste LinkedIn bio, job post, or context about your lead:", height=200)
company = st.text_input("🏢 Company Name (optional):")
job_title = st.text_input("💼 Job Title (optional):")
style = st.selectbox("✍️ Choose a tone/style: ", ["Friendly", "Professional", "Funny", "Bold", "Casual"])
length = st.radio("📏 Select opener length:", ["Short", "Medium", "Long"], index=1)

reset_btn = st.button("🔄 Reset Form")

if reset_btn:
    st.experimental_rerun()

lead = re.sub(r'\s+', ' ', raw_lead).strip().lower()

if len(lead) > 500:
    st.warning("⚠️ Lead info is too long. Please keep it under 500 characters.")
else:
    if 'generate_disabled' not in st.session_state:
        st.session_state.generate_disabled = False

    generate_btn = st.button("✉️ Generate Cold Email", disabled=st.session_state.generate_disabled, key="generate_btn")

    if generate_btn:
        if not lead:
            st.warning("Please enter some lead info first.")
        else:
            st.session_state.generate_disabled = True
            with st.spinner("Generating..."):
                start_time = time.time()
                try:
                    prompt = (
                        f"Write 3 {length.lower()} {style.lower()} cold email openers based on this lead: {lead}."
                    )
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
                        max_tokens=300,
                        temperature=0.7
                    )

                    result = response.choices[0].message.content.strip()
                    duration = round(time.time() - start_time, 2)

                    st.success("✅ Generated cold openers:")
                    openers = [op.strip() for op in result.split("\n") if op.strip()]

                    for idx, opener in enumerate(openers):
                        with st.container():
                            st.markdown(f"### ✉️ Opener {idx+1}")
                            st.markdown(f"<div style='border-left: 4px solid #ccc; padding-left: 1rem; margin-bottom: 1rem;'>{opener}</div>", unsafe_allow_html=True)
                            st.download_button("📋 Copy", opener, f"opener_{idx+1}.txt", key=f"copy_{idx+1}")

                    st.caption(f"⏱️ Generated in {duration} seconds | 📏 {len(result)} characters")

                except Exception as e:
                    st.error(f"Failed to generate message: {str(e)}")
                finally:
                    st.session_state.generate_disabled = False
