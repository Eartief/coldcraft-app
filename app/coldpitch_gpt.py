# app/coldpitch_gpt.py

import streamlit as st
import openai
import os
import re
import time
from datetime import datetime
from supabase import create_client, Client
from gotrue.errors import AuthApiError
import streamlit.components.v1 as components

# --- Config ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]
openai.api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = get_supabase()

# --- Session state defaults ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "guest" not in st.session_state:
    st.session_state["guest"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "Login"
if "saved_num_openers" not in st.session_state:
    st.session_state["saved_num_openers"] = 3
if "reset_generator_form" in st.session_state and st.session_state.reset_generator_form:
    for key in ["openers", "generated_lead"]:
        st.session_state.pop(key, None)
    for key in ["raw_lead", "company", "job_title", "notes", "tag", "style", "length", "view_mode"]:
        st.session_state.pop(key, None)
    st.session_state.reset_generator_form = False

# --- Styling ---
st.set_page_config(page_title='ColdCraft', layout='centered')
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
st.image("https://i.imgur.com/fX4tDCb.png", width=200)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 👤 Session")
    if st.session_state["authenticated"]:
        st.write(f"Logged in as: {st.session_state['user_email']}")
        if st.button("🚪 Log out", key="logout_btn"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.session_state["active_tab"] = "Login"
            st.rerun()
        if st.button("📂 View My Saved Leads", key="view_leads_btn"):
            st.session_state["active_tab"] = "Saved Leads"
            st.rerun()
        if st.button("✍️ Generate New Email", key="gen_new_btn"):
            st.session_state["reset_generator_form"] = True
            st.session_state["active_tab"] = "Generator"
            st.rerun()
    elif st.session_state["guest"]:
        st.write("Guest access")
        if st.button("🚪 Exit Guest Mode", key="exit_guest_btn"):
            st.session_state.clear()
            st.session_state["active_tab"] = "Login"
            st.rerun()

# --- Login Tab ---
if st.session_state["active_tab"] == "Login":
    if not st.session_state["authenticated"] and not st.session_state["guest"]:
        st.subheader("🔐 Welcome to ColdCraft")
        st.write("Login or continue as guest to use the app.")
        with st.form("auth_form"):
            email = st.text_input("📧 Email")
            pwd   = st.text_input("🔑 Password", type="password")
            login_btn = st.form_submit_button("Login")
            guest_btn = st.form_submit_button("Continue as Guest")

            if login_btn:
                try:
                    supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.active_tab = "Generator"
                    st.rerun()
                except AuthApiError as e:
                    st.error(f"❌ Login failed: {e}")

            if guest_btn:
                st.session_state.guest = True
                st.session_state.active_tab = "Generator"
                st.rerun()

        st.markdown("Don't have an account? [Sign up here](https://coldcraft.supabase.co/auth/sign-up)")
        st.stop()

# --- Generator Tab ---
if st.session_state["active_tab"] == "Generator":
    st.title("🧊 ColdCraft - Cold Email Generator")
    with st.form("generator_form"):
        raw_lead  = st.text_area("🔍 Paste LinkedIn bio, job post, or context:", height=200)
        company   = st.text_input("🏢 Lead's Company")
        job_title = st.text_input("💼 Lead's Job Title")
        notes     = st.text_input("📝 Private Notes")
        tag       = st.selectbox("🏷️ Tag this lead", ["None", "Hot", "Follow-up", "Cold", "Replied"])
        style     = st.selectbox("✍️ Tone/Style", ["Friendly", "Professional", "Funny", "Bold", "Casual"])
        length    = st.radio("📏 Opener length", ["Short", "Medium", "Long"], index=1)
        num_openers = st.slider("📄 Number of openers", 1, 5, st.session_state.saved_num_openers)
        view_mode = st.radio("📀 Display Mode", ["List View", "Card View"], index=1)

        generate_btn = st.form_submit_button("Generate Openers")
        if generate_btn:
            st.session_state.saved_num_openers = num_openers
            messages = [
                {"role": "system", "content": "You’re a world-class cold email copywriter. Always return exactly the number of openers asked. Number each one like '1.', '2.', etc."},
                {"role": "user", "content":
                    f"Context: {raw_lead}\n"
                    f"Company: {company}\n"
                    f"Job Title: {job_title}\n"
                    f"Notes: {notes}\n"
                    f"Tone: {style}\n"
                    f"Length: {length}\n"
                    f"Count: {num_openers}"
                }
            ]
            client = openai.OpenAI()
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=num_openers * 80
            )
            result = resp.choices[0].message.content.strip()
            openers = re.findall(r'\d+[.)\-]*\s*(.+?)(?=\n\d+[.)\-]|$)', result, re.DOTALL)
            if len(openers) < num_openers:
                openers = [s.strip() for s in result.split("\n") if s.strip()][:num_openers]
            st.session_state.openers = openers
            st.session_state.generated_lead = {
                "lead": raw_lead,
                "company": company,
                "job_title": job_title,
                "notes": notes,
                "tag": tag,
                "style": style,
                "length": length,
                "openers": openers,
                "timestamp": datetime.utcnow().isoformat()
            }

    if "openers" in st.session_state:
        for i, op in enumerate(st.session_state.openers, 1):
            st.markdown(f"### ✉️ Opener {i}")
            if view_mode == "Card View":
                st.markdown(f"<div style='padding: 1rem; margin-bottom: 1rem; border-radius: 12px; background-color: rgba(240,240,255,0.1); border: 1px solid rgba(200,200,200,0.3); box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>{op}</div>", unsafe_allow_html=True)
            else:
                st.markdown(op)
            st.code(op, language='text')

        if st.session_state.authenticated:
            if st.button("💾 Save This Lead"):
                try:
                    supabase.table("coldcraft").insert({
                        **st.session_state.generated_lead,
                        "user_email": st.session_state.user_email
                    }).execute()
                    st.success("✅ Lead saved.")
                except Exception as e:
                    st.error(f"❌ Save failed: {e}")
        else:
            st.info("Log in to save this lead.")

        components.html("""
        <script>
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        </script>
        """, height=0)

# --- Saved Leads Tab ---
if st.session_state["active_tab"] == "Saved Leads":
    st.title("📁 Your Saved Leads")
    try:
        data = supabase.table("coldcraft").select("*").eq("user_email", st.session_state["user_email"]).order("timestamp", desc=True).execute()
        leads = data.data or []
    except Exception as e:
        st.error(f"Failed to load saved leads: {e}")
        leads = []

    if not leads:
        st.info("No leads saved yet.")
    else:
        for lead in leads:
            with st.expander(f"{lead.get('lead', '')[:40]}..."):
                st.write(f"**Company:** {lead.get('company', '')}")
                st.write(f"**Job Title:** {lead.get('job_title', '')}")
                st.write(f"**Style/Length:** {lead.get('style', '')} / {lead.get('length', '')}")
                st.write(f"**Notes:** {lead.get('notes', '')}")
                st.write(f"**Tag:** {lead.get('tag', '')}")
                for idx, opener in enumerate(lead.get("openers", []), 1):
                    st.markdown(f"**Opener {idx}:** {opener}")
                if st.button("🗑️ Delete This Lead", key=f"del_{lead['id']}"):
                    try:
                        supabase.table("coldcraft").delete().eq("id", lead["id"]).execute()
                        st.success("✅ Lead deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to delete: {e}")
