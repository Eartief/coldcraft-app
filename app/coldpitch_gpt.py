import streamlit as st
import openai
import os
import re
import time
import csv
from datetime import datetime
import urllib.parse

st.set_page_config(page_title='ColdCraft', layout='centered')

# ------------------------
# Helper Functions
# ------------------------
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

def render_copy_button(opener_text: str, idx: int):
    btn_id = f"copy_btn_{idx}"
    st.markdown(f"""
    <button id="{btn_id}" style="margin-top:4px;margin-bottom:8px">📋 Copy to Clipboard</button>
    <script>
    const btn = document.getElementById('{btn_id}');
    if (btn) {{
      btn.onclick = () => {{
        navigator.clipboard.writeText(`{opener_text}`).then(() => {{
          btn.innerText = '✅ Copied!';
          setTimeout(() => btn.innerText = '📋 Copy to Clipboard', 2000);
        }});
      }}
    }}
    </script>
    """, unsafe_allow_html=True)

def render_email_buttons(opener_text):
    encoded = urllib.parse.quote(opener_text)
    gmail_link = f"https://mail.google.com/mail/?view=cm&fs=1&to=&su=Quick intro&body={encoded}"
    outlook_link = f"https://outlook.office.com/mail/deeplink/compose?body={encoded}&subject=Quick%20intro"
    st.markdown(f"[📧 Gmail]({gmail_link}) &nbsp;&nbsp; | &nbsp;&nbsp; [📨 Outlook]({outlook_link})", unsafe_allow_html=True)

# ------------------------
# Theme toggle (light/dark)
# ------------------------
if "theme" not in st.session_state:
    st.session_state["theme"] = "Dark"

selected_theme = st.selectbox("🌃 Select Theme", ["Dark", "Light"], index=0 if st.session_state["theme"] == "Dark" else 1)
st.session_state["theme"] = selected_theme

if selected_theme == "Light":
    st.markdown("""
        <style>
            html, body, .stApp {{ background-color: #f8f9fa !important; color: #111 !important; }}
            textarea, input, select {{ background-color: #fff !important; color: #000 !important; }}
        </style>
    """, unsafe_allow_html=True)
elif selected_theme == "Dark":
    st.markdown("""
        <style>
            html, body, .stApp {{ background-color: #0e1117 !important; color: #fff !important; }}
            textarea, input, select {{ background-color: #1e1e1e !important; color: #fff !important; }}
        </style>
    """, unsafe_allow_html=True)

# ------------------------
# UI Inputs
# ------------------------
st.title('🧊 ColdCraft - Cold Email Generator')
st.write('Paste your lead info below and get a personalized cold email opener.')

openai.api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

raw_lead = st.text_area("🔍 Paste LinkedIn bio, job post, or context about your lead:", height=200)
company = st.text_input("🏢 Lead's Company (where they work):")
job_title = st.text_input("💼 Lead's Job Title:")
notes = st.text_input("📝 Your Private Notes (for internal use only):")
tag = st.selectbox("🏷️ Tag this lead", ["None", "Hot", "Follow-up", "Cold", "Replied"], index=0)
style = st.selectbox("✍️ Choose a tone/style: ", ["Friendly", "Professional", "Funny", "Bold", "Casual"])
length = st.radio("📏 Select opener length:", ["Short", "Medium", "Long"], index=1)
num_openers = st.slider("📄 Number of openers to generate:", min_value=1, max_value=5, value=3)
view_mode = st.radio("📀 Display Mode", ["List View", "Card View"], index=1)

lead = clean_lead(raw_lead)

# ------------------------
# Generation
# ------------------------
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
                        st.markdown(f"""
                            <div style='border-left: 4px solid #ccc; padding-left: 1rem; margin-bottom: 1rem; background: rgba(255,255,255,0.05); border-radius: 8px;'>
                                {opener}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(opener)

                    cols = st.columns([1, 1])
                    with cols[0]:
                        render_copy_button(opener, idx+1)
                    with cols[1]:
                        render_email_buttons(opener)

                st.text_area("📋 All Openers (copy manually if needed):", combined_output, height=150)

                padded_favorites = [''] * num_openers
                log_row = [datetime.now().isoformat(), lead, company, job_title, style, length, notes, tag, *openers[:5], *padded_favorites[:5]]
                headers = ["timestamp", "lead", "company", "job_title", "style", "length", "notes", "tag"] + \
                          [f"opener_{i+1}" for i in range(5)] + [f"favorite_{i+1}" for i in range(5)]
                save_to_csv("lead_log.csv", headers, log_row)

                st.caption(f"⏱️ Generated in {duration} seconds | 📏 {len(result)} characters")

            except Exception as e:
                st.error(f"❌ Error generating openers: {e}")
