# app/coldpitch_gpt.py

import streamlit as st
import openai
import os
import re
import time
from datetime import datetime
from supabase import create_client, Client, AuthApiError

# -------------------- Supabase Setup --------------------
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------- Session Auth State --------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "guest" not in st.session_state:
    st.session_state["guest"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""

# -------------------- Login Screen --------------------
if not st.session_state["authenticated"] and not st.session_state["guest"]:
    st.image("https://i.imgur.com/FYZ9NbS.png", width=140)
    st.title("🔐 Welcome to ColdCraft")
    st.subheader("Login or continue as guest to use the app.")

    email = st.text_input("📧 Email")
    password = st.text_input("🔑 Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Log In"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = result.user.email
                st.success(f"✅ Logged in as {result.user.email}")
                st.rerun()
            except AuthApiError as e:
                st.error("❌ Invalid credentials or Supabase error")

    with col2:
        if st.button("Continue as Guest"):
            st.session_state["guest"] = True
            st.success("✅ Continuing as guest")
            st.rerun()

    st.stop()

# -------------------- Main App --------------------

st.set_page_config(page_title='ColdCraft', layout='centered')

# Hard-set Light Mode
st.markdown("""
    <style>
    html, body, .stApp {
        background-color: #f8f9fa;
        color: #111;
    }
    textarea, input, select {
        background-color: #fff;
        color: #000;
    }
    </style>
""", unsafe_allow_html=True)

st.image("https://i.imgur.com/FYZ9NbS.png", width=120)
st.title("🧊 ColdCraft - Cold Email Generator")

if st.session_state["authenticated"]:
    st.caption(f"🔐 Logged in as: {st.session_state['user_email']}")
elif st.session_state["guest"]:
    st.caption("👤 Guest session")

st.info("🔌 Connecting to Supabase...")

try:
    supabase.table("coldcraft").select("*").limit(1).execute()
    st.success("✅ Supabase connection successful!")
except Exception as e:
    st.error(f"❌ Supabase error: {e}")

# -------------------- Helper Functions --------------------

def clean_lead(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip().lower()

def build_prompt(lead, company, job_title, style, length, num_openers):
    prompt = (
        f"Write exactly {num_openers} {length.lower()} {style.lower()} cold email openers, numbered 1 to {num_openers}, for a sales outreach email. "
        f"Use this lead context: {lead}."
    )
    if company:
        prompt += f" The lead works at {company}."
    if job_title:
        prompt += f" Their job title is {job_title}."
    return prompt

def parse_openers(text: str, expected_count: int = 5) -> list:
    matches = re.findall(r'\d+[.)\-]*\s*(.+?)(?=\n\d+[.)\-]|\Z)', text, re.DOTALL)
    return [op.strip() for op in matches][:expected_count]

# -------------------- UI Form --------------------

openai.api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

raw_lead = st.text_area("🔍 Paste LinkedIn bio, job post, or context about your lead:", height=200)
company = st.text_input("🏢 Lead's Company:")
job_title = st.text_input("💼 Lead's Job Title:")
notes = st.text_input("📝 Private Notes:")
tag = st.selectbox("🏷️ Tag this lead", ["None", "Hot", "Follow-up", "Cold", "Replied"], index=0)
style = st.selectbox("✍️ Tone/Style", ["Friendly", "Professional", "Funny", "Bold", "Casual"])
length = st.radio("📏 Opener length:", ["Short", "Medium", "Long"], index=1)
num_openers = st.slider("📄 Number of openers:", min_value=1, max_value=5, value=3)
view_mode = st.radio("📀 Display Mode", ["List View", "Card View"], index=1)

lead = clean_lead(raw_lead)

if st.button("✉️ Generate Cold Email"):
    if not lead:
        st.warning("Please enter some lead info first.")
    elif len(lead) > 500:
        st.warning("⚠️ Lead info is too long. Please keep it under 500 characters.")
    else:
        with st.spinner("Generating..."):
            try:
                start_time = time.time()
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a world-class B2B cold email copywriter. Only return the email content itself."},
                        {"role": "user", "content": build_prompt(lead, company, job_title, style, length, num_openers)}
                    ],
                    max_tokens=300,
                    temperature=0.7
                )
                result = response.choices[0].message.content.strip()
                duration = round(time.time() - start_time, 2)
                openers = parse_openers(result, num_openers)
                st.session_state.openers = openers

                st.success("✅ Generated cold openers:")
                combined_output = "\n\n".join(openers)

                for idx, opener in enumerate(openers):
                    st.markdown(f"### ✉️ Opener {idx+1}")
                    if view_mode == "Card View":
                        st.markdown(f"<div style='padding: 1rem; margin-bottom: 1rem; border-radius: 12px; background-color: rgba(240,240,255,0.1); border: 1px solid rgba(200,200,200,0.3); box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>{opener}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(opener)
                    st.code(opener, language='text')

                st.text_area("📋 All Openers (copy manually if needed):", combined_output, height=150)

                try:
                    supabase.table("coldcraft").insert({
                        "timestamp": datetime.now().isoformat(),
                        "lead": lead,
                        "company": company,
                        "job_title": job_title,
                        "style": style,
                        "length": length,
                        "notes": notes,
                        "tag": tag,
                        "openers": openers[:num_openers]
                    }).execute()
                    st.success("✅ Lead saved to Supabase.")
                except Exception as db_err:
                    st.error(f"❌ Failed to save to Supabase: {db_err}")

                st.caption(f"⏱️ Generated in {duration} seconds | 📏 {len(result)} characters")

            except Exception as e:
                st.error(f"❌ Error generating openers: {e}")
