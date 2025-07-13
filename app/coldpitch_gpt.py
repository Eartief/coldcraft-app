import streamlit as st
import openai
import os
import re
import time
import csv
from datetime import datetime
from supabase import create_client, Client, AuthApiError

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title='ColdCraft', layout='centered')

# --- LOGIN UI ---
st.header("🔐 Login to Save Your Leads")
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")

        if login_btn:
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if result.user:
                    st.session_state.user = result.user
                    st.success("✅ Logged in successfully!")
                else:
                    st.error("❌ Invalid login. Please try again.")
            except AuthApiError as e:
                st.error(f"❌ Auth error: {e}")

if st.session_state.user:
    st.info("🔌 Testing Supabase connection...")
    try:
        table_list = supabase.table("coldcraft").select("*").limit(1).execute()
        st.success("✅ Supabase connection successful!")
    except Exception as e:
        st.error(f"❌ Supabase error: {e}")

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

    def save_to_csv(path, headers, row):
        file_exists = os.path.exists(path)
        with open(path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(row)

    if "theme" not in st.session_state:
        st.session_state["theme"] = "Dark"

    selected_theme = st.selectbox("\U0001F303 Select Theme", ["Dark", "Light"], index=0 if st.session_state["theme"] == "Dark" else 1)
    st.session_state["theme"] = selected_theme

    if selected_theme == "Light":
        st.markdown("""
            <style>
                html, body, .stApp { background-color: #f8f9fa !important; color: #111 !important; }
                textarea, input, select { background-color: #fff !important; color: #000 !important; }
            </style>
        """, unsafe_allow_html=True)
    elif selected_theme == "Dark":
        st.markdown("""
            <style>
                html, body, .stApp { background-color: #0e1117 !important; color: #fff !important; }
                textarea, input, select { background-color: #1e1e1e !important; color: #fff !important; }
            </style>
        """, unsafe_allow_html=True)

    st.title('\U0001F9CA ColdCraft - Cold Email Generator')
    st.write('Paste your lead info below and get a personalized cold email opener.')

    openai.api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

    raw_lead = st.text_area("\U0001F50D Paste LinkedIn bio, job post, or context about your lead:", height=200)
    company = st.text_input("\U0001F3E2 Lead's Company (where they work):")
    job_title = st.text_input("\U0001F4BC Lead's Job Title:")
    notes = st.text_input("\U0001F4DD Your Private Notes (for internal use only):")
    tag = st.selectbox("\U0001F3F7️ Tag this lead", ["None", "Hot", "Follow-up", "Cold", "Replied"], index=0)
    style = st.selectbox("\u270D\ufe0f Choose a tone/style: ", ["Friendly", "Professional", "Funny", "Bold", "Casual"])
    length = st.radio("\U0001F4CF Select opener length:", ["Short", "Medium", "Long"], index=1)
    num_openers = st.slider("\U0001F4C4 Number of openers to generate:", min_value=1, max_value=5, value=3)
    view_mode = st.radio("\U0001F4C0 Display Mode", ["List View", "Card View"], index=1)

    lead = clean_lead(raw_lead)

    if st.button("\u2709\ufe0f Generate Cold Email"):
        if not lead:
            st.warning("Please enter some lead info first.")
        elif len(lead) > 500:
            st.warning("\u26A0\ufe0f Lead info is too long. Please keep it under 500 characters.")
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
                        st.markdown(f"""
                            <div style='border-left: 4px solid #ccc; padding-left: 1rem; margin-bottom: 1rem; background: rgba(255,255,255,0.05); border-radius: 8px;'>
                                {opener}
                            </div>
                        """, unsafe_allow_html=True)
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
                            "openers": openers[:num_openers],
                            "user_id": st.session_state.user.id
                        }).execute()
                        st.success("✅ Lead saved to Supabase.")
                    except Exception as db_err:
                        st.error(f"❌ Failed to save to Supabase: {db_err}")

                    st.caption(f"⏱️ Generated in {duration} seconds | 📏 {len(result)} characters")

                except Exception as e:
                    st.error(f"❌ Error generating openers: {e}")
