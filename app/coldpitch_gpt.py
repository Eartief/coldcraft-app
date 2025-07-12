import streamlit as st
import openai
import os
import re
import time
import csv
import pandas as pd
from datetime import datetime
from io import StringIO
import urllib.parse

st.set_page_config(page_title='ColdCraft', layout='centered')
st.title('🧊 ColdCraft - Cold Email Generator')
st.write('Paste your lead info below and get a personalized cold email opener.')

openai.api_key = st.secrets["OPENAI_API_KEY"]

raw_lead = st.text_area("🔍 Paste LinkedIn bio, job post, or context about your lead:", height=200)
company = st.text_input("🏢 Company Name (optional):")
job_title = st.text_input("💼 Job Title (optional):")
notes = st.text_input("📝 Internal Notes (optional):")
tag = st.selectbox("🏷️ Tag this lead", ["None", "Hot", "Follow-up", "Cold", "Replied"], index=0)
style = st.selectbox("✍️ Choose a tone/style: ", ["Friendly", "Professional", "Funny", "Bold", "Casual"])
length = st.radio("📏 Select opener length:", ["Short", "Medium", "Long"], index=1)
view_mode = st.radio("📐 Display Mode", ["List View", "Card View"], index=1)

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
                    system_prompt = (
                        "You are a world-class B2B cold email copywriter. Only return the email content itself. "
                        "Do not preface with comments like 'Certainly!' or 'Here are...'"
                    )

                    user_prompt = (
                        f"Write 3 {length.lower()} {style.lower()} cold email openers for outreach. "
                        f"Use this lead context: {lead}."
                    )
                    if company:
                        user_prompt += f" The company name is {company}."
                    if job_title:
                        user_prompt += f" The job title is {job_title}."

                    response = openai.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=300,
                        temperature=0.7
                    )

                    result = response.choices[0].message.content.strip()
                    duration = round(time.time() - start_time, 2)

                    st.success("✅ Generated cold openers:")

                    openers = []
                    for line in result.split("\n"):
                        line = line.strip()
                        if re.match(r'^(\d+\.|[-*])\s', line):
                            openers.append(re.sub(r'^(\d+\.|[-*])\s*', '', line))

                    combined_output = "\n\n".join(openers)
                    favorites = []

                    for idx, opener in enumerate(openers):
                        with st.container():
                            st.markdown(f"### ✉️ Opener {idx+1}")
                            if view_mode == "Card View":
                                st.markdown(f"<div style='border-left: 4px solid #ccc; padding-left: 1rem; margin-bottom: 1rem;'>{opener}</div>", unsafe_allow_html=True)
                            else:
                                st.markdown(opener)

                            st.download_button("📋 Copy", opener, f"opener_{idx+1}.txt", key=f"copy_{idx+1}")

                            gmail_link = f"https://mail.google.com/mail/?view=cm&fs=1&to=&su=Quick intro&body={urllib.parse.quote(opener)}"
                            st.markdown(f"[📨 Send with Gmail]({gmail_link})", unsafe_allow_html=True)

                            if st.button(f"⭐ Save Opener {idx+1} as Favorite", key=f"fav_{idx+1}"):
                                favorites.append(opener)

                    st.download_button("📥 Copy All Openers", combined_output, file_name="all_openers.txt")

                    log_row = [datetime.now().isoformat(), lead, company, job_title, style, length, notes, tag, *openers, *favorites]
                    log_path = "lead_log.csv"
                    header = ["timestamp", "lead", "company", "job_title", "style", "length", "notes", "tag", "opener_1", "opener_2", "opener_3", "favorite_1", "favorite_2", "favorite_3"]
                    file_exists = os.path.exists(log_path)
                    with open(log_path, mode='a', newline='', encoding='utf-8') as file:
                        writer = csv.writer(file)
                        if not file_exists:
                            writer.writerow(header)
                        writer.writerow(log_row)

                    st.caption(f"⏱️ Generated in {duration} seconds | 📏 {len(result)} characters")

                except Exception as e:
                    st.error(f"Failed to generate message: {str(e)}")
                finally:
                    st.session_state.generate_disabled = False

if os.path.exists("lead_log.csv"):
    st.markdown("---")
    st.subheader("📊 Lead History")

    df = pd.read_csv("lead_log.csv")

    with st.expander("🔍 Filter History"):
        tone_filter = st.multiselect("Tone", df["style"].unique(), default=list(df["style"].unique()))
        length_filter = st.multiselect("Length", df["length"].unique(), default=list(df["length"].unique()))
        tag_filter = st.multiselect("Tag", df["tag"].dropna().unique(), default=list(df["tag"].dropna().unique()))
        keyword = st.text_input("Search keyword in lead, notes, or openers:")

    filtered_df = df[df["style"].isin(tone_filter) & df["length"].isin(length_filter) & df["tag"].isin(tag_filter)]
    if keyword:
        keyword = keyword.lower()
        filtered_df = filtered_df[filtered_df.apply(lambda row: keyword in str(row).lower(), axis=1)]

    st.dataframe(filtered_df)

    csv_buffer = StringIO()
    filtered_df.to_csv(csv_buffer, index=False)
    st.download_button("📥 Download Filtered History", csv_buffer.getvalue(), "filtered_leads.csv")
