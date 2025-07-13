import streamlit as st
import openai
import os
import re
from datetime import datetime
from supabase import create_client, Client
from gotrue.errors import AuthApiError
import streamlit.components.v1 as components

# Configuration
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]
openai.api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# Restore auth session from saved tokens
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    try:
        supabase.auth.set_session({
            "access_token": st.session_state["access_token"],
            "refresh_token": st.session_state["refresh_token"]
        })
    except Exception:
        pass

# Retrieve current session
db_session = supabase.auth.get_session()
if db_session and db_session.user:
    st.session_state["authenticated"] = True
    st.session_state["user_email"] = db_session.user.email
else:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user_email", "")
    st.session_state.setdefault("guest", False)

# Default session state
st.session_state.setdefault("active_tab", "Login")
st.session_state.setdefault("saved_num_openers", 3)
if st.session_state.get("reset_generator_form"):
    for key in ["openers", "generated_lead"]:
        st.session_state.pop(key, None)
    for key in ["raw_lead", "company", "job_title", "notes", "tag", "style", "length", "view_mode"]:
        st.session_state.pop(key, None)
    st.session_state["reset_generator_form"] = False

# Page setup
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

# Sidebar: session controls
with st.sidebar:
    st.markdown("### 👤 Session")
    uid = st.session_state.get("user_email", "guest")
    if st.session_state["authenticated"]:
        st.write(f"Logged in as: {uid}")
        if st.button("🚪 Log out", key=f"logout_btn_{uid}"):
            supabase.auth.sign_out()
            for token in ["access_token", "refresh_token"]:
                st.session_state.pop(token, None)
            st.session_state.clear()
            st.session_state["active_tab"] = "Login"
            st.rerun()
        if st.button("📂 View My Saved Leads", key=f"view_leads_btn_{uid}"):
            st.session_state["active_tab"] = "Saved Leads"
            st.rerun()
        if st.button("✍️ Generate New Email", key=f"gen_new_btn_{uid}"):
            st.session_state["reset_generator_form"] = True
            st.session_state["active_tab"] = "Generator"
            st.rerun()
    elif st.session_state["guest"]:
        st.write("Guest access")
        if st.button("🚪 Exit Guest Mode", key="exit_guest_btn"):
            st.session_state.clear()
            st.session_state["active_tab"] = "Login"
            st.rerun()

# --- LOGIN SCREEN ---
if st.session_state["active_tab"] == "Login":
    if not st.session_state["authenticated"] and not st.session_state["guest"]:
        st.subheader("🔐 Welcome to ColdCraft")
        st.write("Login or continue as guest to use the app.")
        with st.form("auth_form"):
            email = st.text_input("📧 Email")
            pwd = st.text_input("🔑 Password", type="password")
            login_btn = st.form_submit_button("Login")
            guest_btn = st.form_submit_button("Continue as Guest")

            if login_btn:
                try:
                    auth_response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": pwd
                    })
                    session = getattr(auth_response, 'session', None)
                    user = getattr(auth_response, 'user', None)
                    if not session or not user:
                        st.error("❌ Login failed: Invalid credentials.")
                    else:
                        # Persist tokens
                        st.session_state["access_token"] = session.access_token
                        st.session_state["refresh_token"] = session.refresh_token
                        st.session_state["authenticated"] = True
                        st.session_state["user_email"] = user.email
                        st.session_state["active_tab"] = "Generator"
                        st.rerun()
                except AuthApiError as e:
                    st.error(f"❌ Login failed: {e}")
            if guest_btn:
                st.session_state["guest"] = True
                st.session_state["active_tab"] = "Generator"
                st.rerun()

        st.markdown("Don't have an account? [Sign up here](https://coldcraft.supabase.co/auth/sign-up)")
        st.stop()

# --- GENERATOR TAB ---
if st.session_state["active_tab"] == "Generator":
    st.title("🧊 ColdCraft - Cold Email Generator")
    with st.form("generator_form"):
        raw_lead = st.text_area("🔍 Paste LinkedIn bio, job post, or context:", height=200)
        company = st.text_input("🏢 Lead's Company")
        job_title = st.text_input("💼 Lead's Job Title")
        notes = st.text_input("📝 Private Notes")
        tag = st.selectbox("🏷️ Tag this lead", ["None", "Hot", "Follow-up", "Cold", "Replied"])
        style = st.selectbox("✍️ Tone/Style", ["Friendly", "Professional", "Funny", "Bold", "Casual"])
        length = st.radio("📏 Opener length", ["Short", "Medium", "Long"], index=1)
        num_openers = st.slider("📄 Number of openers", 1, 5, st.session_state["saved_num_openers"])
        view_mode = st.radio("📀 Display Mode", ["List View", "Card View"], index=1)
        if st.form_submit_button("✉️ Generate Cold Email"):
            st.session_state["saved_num_openers"] = num_openers
            messages = [
                {"role": "system", "content": "You're a professional B2B cold email writer. Return exactly the number of openers requested, numbered 1-N."},
                {"role": "user", "content": f"Write {num_openers} {length.lower()} {style.lower()} cold email openers for a sales outreach.\nContext: {raw_lead}\nCompany: {company}\nJob Title: {job_title}\nNotes: {notes}"}
            ]
            try:
                with st.spinner("🛠️ Generating your openers..."):
                    client = openai.OpenAI()
                    resp = client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        max_tokens=num_openers * 80
                    )
                    result = resp.choices[0].message.content.strip()
                    openers = re.findall(r"\d+[.)\-]*\s*(.+?)(?=\n\d+[.)\-]|\Z)", result, re.DOTALL)
                    if len(openers) < num_openers:
                        openers = [line.strip() for line in result.splitlines() if line.strip()][:num_openers]
                    st.session_state["openers"] = openers
                    st.session_state["generated_lead"] = {
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
            except Exception as e:
                st.error(f"❌ Error from OpenAI: {e}")
    if "openers" in st.session_state:
        for idx, opener in enumerate(st.session_state["openers"], start=1):
            st.markdown(f"### ✉️ Opener {idx}")
            if st.session_state.get("view_mode") == "Card View":
                st.markdown(
                    f"<div style='padding:1rem;margin-bottom:1rem;border-radius:12px;"
                    "background-color:rgba(240,240,255,0.1);border:1px solid rgba(200,200,200,0.3);"
                    "box-shadow:0 2px 5px rgba(0,0,0,0.1);'>{opener}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(opener)
            st.code(opener, language='text')
        if st.session_state["authenticated"]:
            if st.button("💾 Save This Lead"):
                try:
                    supabase.table("coldcraft").insert({**st.session_state["generated_lead"], "user_email": st.session_state["user_email"]}).execute()
                    st.success("✅ Lead saved.")
                except Exception as e:
                    st.error(f"❌ Save failed: {e}")
        else:
            st.info("🔒 Log in to save this lead.")
        components.html("<script>window.scrollTo({ top: document.body.scrollHeight });</script>", height=0)

# --- SAVED LEADS TAB ---
if st.session_state["active_tab"] == "Saved Leads":
    st.title("📁 Your Saved Leads")
    try:
        data = supabase.table("coldcraft").select("*").eq("user_email", st.session_state["user_email"]).order("timestamp", desc=True).execute()
        leads = data.data or []
    except Exception as e:
        st.error(f"❌ Failed to load leads: {e}")
        leads = []
    if not leads:
        st.info("No saved leads yet.")
    else:
        for lead in leads:
            snippet = lead.get("lead", "")[0:120] + ("..." if len(lead.get("lead", "")) > 120 else "")
            with st.expander(snippet):
                st.write(
                    f"**Company:** {lead.get('company','')}  \n"
                    f"**Job Title:** {lead.get('job_title','')}  \n"
                    f"**Style/Length:** {lead.get('style','')} / {lead.get('length','')}  \n"
                    f"**Notes:** {lead.get('notes','')}  \n"
                    f"**Tag:** {lead.get('tag','')}"
                )
                for idx, op in enumerate(lead.get("openers", []), start=1):
                    st.markdown(f"**Opener {idx}:** {op}")
                if st.button("🗑️ Delete This Lead", key=f"del_{lead['id']}"):
                    try:
                        supabase.table("coldcraft").delete().eq("id", lead["id"]).execute()
                        st.success("✅ Lead deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to delete: {e}")

# Auto-scroll
if "openers" in st.session_state:
    components.html("<script>window.scrollTo({ top: document.body.scrollHeight });</script>", height=0)
