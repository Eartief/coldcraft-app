import streamlit as st
import openai
import os
import re
from datetime import datetime, timezone
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

# Restore session tokens
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    try:
        supabase.auth.set_session({
            "access_token": st.session_state["access_token"],
            "refresh_token": st.session_state["refresh_token"]
        })
    except Exception:
        pass

# Check current session
session_resp = supabase.auth.get_session()
if session_resp and session_resp.user:
    st.session_state["authenticated"] = True
    st.session_state["user_email"] = session_resp.user.email
else:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user_email", "")
    st.session_state.setdefault("guest", False)

# Default UI state
st.session_state.setdefault("active_tab", "Login")
st.session_state.setdefault("saved_num_openers", 3)
if st.session_state.get("reset_generator_form"):
    for key in ["openers", "generated_lead"]:
        st.session_state.pop(key, None)
    for key in ["raw_lead", "company", "job_title", "notes", "tag", "style", "length", "view_mode"]:
        st.session_state.pop(key, None)
    st.session_state["reset_generator_form"] = False

# Page layout
st.set_page_config(page_title='ColdCraft', layout='centered')
st.markdown(
    """
<style>
html, body, .stApp { background-color: #f8f9fa; color: #111; }
textarea, input, select { background-color: #fff; color: #000; }
</style>
""", unsafe_allow_html=True
)
st.image("https://i.imgur.com/fX4tDCb.png", width=200)

# Sidebar menu
with st.sidebar:
    st.markdown("### 👤 Session")
    if st.session_state["authenticated"]:
        user = st.session_state["user_email"]
        st.write(f"Logged in as: {user}")
        if st.button("🚪 Log out"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.session_state["active_tab"] = "Login"
            st.rerun()
        if st.button("📂 Saved Leads"):
            st.session_state["active_tab"] = "Saved Leads"
            st.rerun()
        if st.button("✍️ New Email"):
            st.session_state["reset_generator_form"] = True
            st.session_state["active_tab"] = "Generator"
            st.rerun()
    elif st.session_state["guest"]:
        st.write("Guest access")
        if st.button("🚪 Exit Guest"):
            st.session_state.clear()
            st.session_state["active_tab"] = "Login"
            st.rerun()

# Login/Signup tab
if st.session_state["active_tab"] == "Login":
    if not st.session_state["authenticated"] and not st.session_state["guest"]:
        st.subheader("🔐 Welcome to ColdCraft")
        choice = st.radio("Action:", ["Login", "Sign up"], horizontal=True)
        if choice == "Login":
            with st.form("login_form"):
                email = st.text_input("Email")
                pwd = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    try:
                        resp = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                        if not getattr(resp, 'session', None):
                            st.error("Invalid credentials")
                        else:
                            s = resp.session
                            st.session_state.update({
                                "access_token": s.access_token,
                                "refresh_token": s.refresh_token,
                                "authenticated": True,
                                "user_email": resp.user.email,
                                "active_tab": "Generator"
                            })
                            st.rerun()
                    except AuthApiError as e:
                        st.error(f"Login failed: {e}")
                if st.form_submit_button("Continue as Guest"):
                    st.session_state["guest"] = True
                    st.session_state["active_tab"] = "Generator"
                    st.rerun()
        else:
            with st.form("signup_form"):
                new_email = st.text_input("Email", key="su_email")
                new_pwd = st.text_input("Password", type="password", key="su_pwd")
                cnf = st.text_input("Confirm Password", type="password", key="su_cnf")
                if st.form_submit_button("Sign Up"):
                    if new_pwd != cnf:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            resp = supabase.auth.sign_up({"email": new_email, "password": new_pwd})
                            if getattr(resp, 'session', None):
                                s = resp.session
                                st.session_state.update({
                                    "access_token": s.access_token,
                                    "refresh_token": s.refresh_token,
                                    "authenticated": True,
                                    "user_email": resp.user.email,
                                    "active_tab": "Generator"
                                })
                                st.success("Account created and logged in!")
                                st.rerun()
                            else:
                                st.info("Check your email to confirm sign-up.")
                                st.session_state["active_tab"] = "Login"
                                st.rerun()
                        except AuthApiError as e:
                            st.error(f"Sign-up failed: {e}")
        st.stop()

# Generator tab
if st.session_state["active_tab"] == "Generator":
    st.title("🧊 ColdCraft")
    with st.form("gen"): 
        raw = st.text_area("Context", height=200)
        comp = st.text_input("Company")
        title = st.text_input("Job Title")
        notes = st.text_input("Notes")
        tag = st.selectbox("Tag", ["None", "Hot", "Follow-up", "Cold", "Replied"])
        style = st.selectbox("Style", ["Friendly", "Professional", "Funny", "Bold", "Casual"])
        length = st.radio("Length", ["Short", "Medium", "Long"], index=1)
        num = st.slider("# Openers", 1, 5, st.session_state["saved_num_openers"])
        view = st.radio("View Mode", ["List", "Card"], index=1)
        if st.form_submit_button("Generate"):
            st.session_state["saved_num_openers"] = num
            msgs = [
                {"role": "system", "content": "You're a cold email writer."},
                {"role": "user", "content": f"Write {num} {length.lower()} {style.lower()} openers. Context: {raw}. Company: {comp}. Title: {title}. Notes: {notes}"}
            ]
            try:
                resp = openai.ChatCompletion.create(model="gpt-4o", messages=msgs, max_tokens=num * 80)
                txt = resp.choices[0].message.content.strip()
                ops = re.findall(r"\d+[.)\-]*\s*(.+?)(?=\n\d+[.)\-]|\Z)", txt, re.DOTALL)
                if len(ops) < num:
                    ops = [l for l in txt.splitlines() if l][:num]
                st.session_state.update({
                    "openers": ops,
                    "generated_lead": {
                        "lead": raw,
                        "company": comp,
                        "job_title": title,
                        "notes": notes,
                        "tag": tag,
                        "style": style,
                        "length": length,
                        "openers": ops,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                })
            except Exception as e:
                st.error(f"Error: {e}")
    if "openers" in st.session_state:
        for i, op in enumerate(st.session_state["openers"], 1):
            st.markdown(f"### Opener {i}")
            if view == "Card":
                st.markdown(f"<div style='padding:1rem;border:1px solid #ccc;border-radius:8px'>{op}</div>", unsafe_allow_html=True)
            else:
                st.markdown(op)
            st.code(op, language='text')
        if st.session_state["authenticated"]:
            if st.button("Save Lead"):
                try:
                    supabase.table("coldcraft").insert({**st.session_state["generated_lead"], "user_email": st.session_state["user_email"]}).execute()
                    st.success("Saved!")
                except Exception as e:
                    st.error(f"Save failed: {e}")
        else:
            st.info("Login to save leads.")
        components.html("<script>window.scrollTo({top:document.body.scrollHeight});</script>", height=0)

# Saved Leads tab
if st.session_state["active_tab"] == "Saved Leads":
    st.title("📁 Saved Leads")
    try:
        res = supabase.table("coldcraft").select("*").eq("user_email", st.session_state["user_email"]).order("timestamp", desc=True).execute()
        leads = res.data or []
    except Exception as e:
        st.error(f"Load failed: {e}")
        leads = []
    if not leads:
        st.info("No leads yet.")
    else:
        for lead in leads:
            txt = lead.get("lead", "")[:120] + ("..." if len(lead.get("lead", "")) > 120 else "")
            with st.expander(txt):
                st.markdown(
                    f"**Company:** {lead.get('company','')}  \n"
                    f"**Job Title:** {lead.get('job_title','')}  \n"
                    f"**Style/Length:** {lead.get('style','')} / {lead.get('length','')}  \n"
                    f"**Notes:** {lead.get('notes','')}  \n"
                    f"**Tag:** {lead.get('tag','')}"
                )
                for i, op in enumerate(lead.get("openers", []), 1):
                    st.markdown(f"**Opener {i}:** {op}")
                if st.button("Delete", key=f"del{lead['id']}"):
                    try:
                        supabase.table("coldcraft").delete().eq("id", lead['id']).execute()
                        st.success("Deleted")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")

# Auto-scroll
if "openers" in st.session_state:
    components.html("<script>window.scrollTo({top:document.body.scrollHeight});</script>", height=0)
