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

# ------------------------
# Helper Functions
# ------------------------
def clean_lead(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip().lower()

def build_prompt(lead, company, job_title, style, length, num_openers):
    prompt = (
        f"Write {num_openers} {length.lower()} {style.lower()} cold email openers for outreach. "
        f"Use this lead context: {lead}."
    )
    if company:
        prompt += f" The company name is {company}."
    if job_title:
        prompt += f" The job title is {job_title}."
    return prompt

def parse_openers(text: str) -> list:
    return [line.strip() for line in text.split("\n") if line.strip()]

def save_to_csv(path, headers, row):
    file_exists = os.path.exists(path)
    with open(path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(headers)
        writer.writerow(row)

# ------------------------
# Theme toggle (light/dark)
# ------------------------
if "theme" not in st.session_state:
    st.session_state["theme"] = "Dark"

selected_theme = st.selectbox("🌓 Select Theme", ["Dark", "Light"], index=0 if st.session_state["theme"] == "Dark" else 1)
st.session_state["theme"] = selected_theme

if selected_theme == "Light":
    st.markdown("""
        <style>
            html, body, [class*="css"]  { background-color: #fafafa !important; color: #111 !important; }
            textarea, input, select, .stTextInput, .stTextArea { background-color: #fff !important; color: #000 !important; }
        </style>
    """, unsafe_allow_html=True)

# ------------------------
# UI Inputs
# ------------------------
st.title('🧊 ColdCraft - Cold Email Generator')
st.write('Paste your lead info below and get a personalized cold email opener.')

openai.api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

raw_lead = st.text_area("🔍 Paste LinkedIn bio, job post, or context about your lead:", height=200)
company = st.text_input("🏢 Company Name (optional):")
job_title = st.text_input("💼 Job Title (optional):")
notes = st.text_input("📝 Internal Notes (optional):")
tag = st.selectbox("🏷️ Tag this lead", ["None", "Hot", "Follow-up", "Cold", "Replied"], index=0)
style = st.selectbox("✍️ Choose a tone/style: ", ["Friendly", "Professional", "Funny", "Bold", "Casual"])
length = st.radio("📏 Select opener length:", ["Short", "Medium", "Long"], index=1)
num_openers = st.slider("📝 Number of openers to generate:", min_value=1, max_value=5, value=3)
view_mode = st.radio("📐 Display Mode", ["List View", "Card View"], index=1)

lead = clean_lead(raw_lead)

# ------------------------
# Generation
# ------------------------
if len(lead) > 500:
    st.warning("⚠️ Lead info is too long. Please keep it under 500 characters.")
else:
    if 'generate_disabled' not in st.session_state:
        st.session_state.generate_disabled = False

    if st.button("✉️ Generate Cold Email", disabled=st.session_state.generate_disabled):
        if not lead:
            st.warning("Please enter some lead info first.")
        else:
            st.session_state.generate_disabled = True
            with st.spinner("Generating..."):
                try:
                    start_time = time.time()

                    response = openai.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "You are a world-class B2B cold email copywriter. Only return the email content itself. Do not preface with comments like 'Certainly!' or 'Here are...'"},
                            {"role": "user", "content": build_prompt(lead, company, job_title, style, length, num_openers)}
                        ],
                        max_tokens=300,
                        temperature=0.7
                    )

                    result = response.choices[0].message.content.strip()
                    duration = round(time.time() - start_time, 2)
                    openers = parse_openers(result)
                    combined_output = "\n\n".join(openers)
                    favorites = []

                    st.success("✅ Generated cold openers:")
                    for idx, opener in enumerate(openers):
                        st.markdown(f"### ✉️ Opener {idx+1}")
                        if view_mode == "Card View":
                            st.markdown(f"""
                                <div style='border-left: 4px solid #ccc; padding-left: 1rem; margin-bottom: 1rem; background: rgba(255,255,255,0.05); border-radius: 8px;'>
                                    {opener}
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(opener)

                        cols = st.columns([1, 1, 2])
                        with cols[0]:
                            st.download_button("📋 Copy", opener, f"opener_{idx+1}.txt", key=f"copy_{idx+1}")
                        with cols[1]:
                            st.markdown(f"[📨 Gmail](https://mail.google.com/mail/?view=cm&fs=1&to=&su=Quick intro&body={urllib.parse.quote(opener)})", unsafe_allow_html=True)
                        with cols[2]:
                            if st.button(f"⭐ Save Opener {idx+1}", key=f"fav_{idx+1}"):
                                favorites.append(opener)

                    st.download_button("📥 Copy All Openers", combined_output, file_name="all_openers.txt")

                    padded_favorites = favorites + [''] * (num_openers - len(favorites))
                    log_row = [datetime.now().isoformat(), lead, company, job_title, style, length, notes, tag, *openers[:5], *padded_favorites[:5]]
                    headers = ["timestamp", "lead", "company", "job_title", "style", "length", "notes", "tag"] + \
                              [f"opener_{i+1}" for i in range(5)] + [f"favorite_{i+1}" for i in range(5)]
                    save_to_csv("lead_log.csv", headers, log_row)

                    st.caption(f"⏱️ Generated in {duration} seconds | 📏 {len(result)} characters")

                except Exception as e:
                    st.error(f"Failed to generate message: {str(e)}")
                finally:
                    st.session_state.generate_disabled = False

# ------------------------
# History Log View
# ------------------------
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

    # ------------------------
    # Analytics Section
    # ------------------------
    st.markdown("---")
    st.subheader("📈 Insights & Stats")

    stats1, stats2 = st.columns(2)
    with stats1:
        st.metric("Total Leads", len(df))
        st.metric("Total Favorites", df[[col for col in df.columns if col.startswith("favorite_")]].notna().sum().sum())
    with stats2:
        st.bar_chart(df["style"].value_counts())
        st.bar_chart(df[[col for col in df.columns if col.startswith("favorite_")]].notna().sum(axis=1))

    tag_dist = df["tag"].value_counts()
    if not tag_dist.empty:
        st.subheader("🎯 Tag Distribution")
        st.dataframe(tag_dist.reset_index().rename(columns={"index": "Tag", "tag": "Count"}))
