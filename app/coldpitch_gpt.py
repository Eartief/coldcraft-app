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

# Handle email confirmation redirect
params = st.query_params
if 'access_token' in params and 'refresh_token' in params:
    try:
        supabase.auth.set_session({
            'access_token': params['access_token'][0],
            'refresh_token': params['refresh_token'][0]
        })
        session = supabase.auth.get_session()
        if session and session.user:
            st.session_state['authenticated'] = True
            st.session_state['user_email'] = session.user.email
            st.session_state['access_token'] = params['access_token'][0]
            st.session_state['refresh_token'] = params['refresh_token'][0]
            st.session_state['active_tab'] = 'Generator'
            components.html(
                "<script>window.history.replaceState({}, document.title, window.location.pathname);</script>",
                height=0
            )
            st.success("✅ Email confirmed and logged in!")
    except Exception as e:
        st.error(f"Error confirming email: {e}")

# Restore session tokens
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    try:
        supabase.auth.set_session({
            "access_token": st.session_state["access_token"],
            "refresh_token": st.session_state["refresh_token"]
        })
    except Exception:
        pass

session_resp = supabase.auth.get_session()
if session_resp and session_resp.user:
    st.session_state["authenticated"] = True
    st.session_state["user_email"] = session_resp.user.email
else:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user_email", "")
    st.session_state.setdefault("guest", False)

st.session_state.setdefault("active_tab", "Login")
st.session_state.setdefault("saved_num_openers", 3)
if st.session_state.get("reset_generator_form"):
    for k in ["openers", "generated_lead"]:
        st.session_state.pop(k, None)
    for k in ["raw_lead", "company", "job_title", "notes", "tag", "style", "length", "view_mode"]:
        st.session_state.pop(k, None)
    st.session_state["reset_generator_form"] = False

# Page layout & responsive CSS
st.set_page_config(page_title='ColdCraft', layout='centered')
st.markdown(
    """
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
html, body, .stApp {
  background-color: #ffffff !important;
  color: #111 !important;
  font-family: "Arial", sans-serif;
}

input, textarea, select, button {
  background-color: #ffffff !important;
  color: #000000 !important;
  border-radius: 8px;
  border: 1px solid #ccc;
}

.stTextInput > label, .stPassword > label, .stSelectbox > label, .stRadio > label {
  color: #111 !important;
  font-weight: bold;
  display: block;
  margin-bottom: 0.25rem;
}

label {
  color: #111 !important;
  font-weight: bold;
}

button {
  background-color: #eeeeee !important;
  color: #111 !important;
}

/* Mobile */
@media (max-width: 600px) {
  html, body {
    font-size: 16px !important;
  }
  input, textarea, select, button {
    width: 100% !important;
    font-size: 1rem !important;
    box-sizing: border-box;
  }
  .block-container {
    padding: 1rem !important;
  }
  .stButton > button {
    width: 100% !important;
  }
  .stTextInput, .stPassword {
    margin-bottom: 1rem;
  }
}
</style>
""",
    unsafe_allow_html=True
)

st.image("https://cdn.jsdelivr.net/gh/eartief/assets@main/coldcraft-logo.png", width=200)

# Sidebar menu
with st.sidebar:
    st.markdown("### 👤 Session")
    if st.session_state["authenticated"]:
        user = st.session_state["user_email"]
        st.write(f"Logged in as: {user}")
        if st.button("🚪 Log out"): supabase.auth.sign_out(); st.session_state.clear(); st.session_state["active_tab"]="Login"; st.rerun()
        if st.button("📂 Saved Leads"): st.session_state["active_tab"]="Saved Leads"; st.rerun()
        if st.button("✍️ New Email"): st.session_state["reset_generator_form"]=True; st.session_state["active_tab"]="Generator"; st.rerun()
    elif st.session_state["guest"]:
        st.write("Guest access")
        if st.button("🚪 Exit Guest"): st.session_state.clear(); st.session_state["active_tab"]="Login"; st.rerun()

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
                        if not getattr(resp, 'session', None): st.error("Invalid credentials")
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
                    except AuthApiError as e: st.error(f"Login failed: {e}")
                if st.form_submit_button("Continue as Guest"): st.session_state.update({"guest":True, "active_tab":"Generator"}); st.rerun()
        else:
            with st.form("signup_form"):
                new_email = st.text_input("Email", key="su_email")
                new_pwd = st.text_input("Password", type="password", key="su_pwd")
                cnf = st.text_input("Confirm Password", type="password", key="su_cnf")
                if st.form_submit_button("Sign Up"):
                    if new_pwd != cnf: st.error("Passwords do not match.")
                    else:
                        try:
                            resp = supabase.auth.sign_up({"email":new_email,"password":new_pwd})
                            if getattr(resp,'session',None):
                                s=resp.session
                                st.session_state.update({
                                    "access_token":s.access_token,
                                    "refresh_token":s.refresh_token,
                                    "authenticated":True,
                                    "user_email":resp.user.email,
                                    "active_tab":"Generator"
                                })
                                st.success("Account created and logged in!")
                                st.rerun()
                            else: st.info("Check your email to confirm sign-up."); st.session_state["active_tab"]="Login"; st.rerun()
                        except AuthApiError as e: st.error(f"Sign-up failed: {e}")
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
            msgs = [{"role":"system","content":"You're a cold email writer."},{"role":"user","content":f"Write {num} {length.lower()} {style.lower()} openers. Context: {raw}. Company: {comp}. Title: {title}. Notes: {notes}"}]
            try:
                resp = openai.ChatCompletion.create(model="gpt-4o", messages=msgs, max_tokens=num * 80)
                txt = resp.choices[0].message.content.strip()
                ops = re.findall(r"\d+[.)\-]*\s*(.+?)(?=\n\d+[.)\-]|\Z)", txt, re.DOTALL)
                if len(ops) < num: ops = [l for l in txt.splitlines() if l][:num]
                st.session_state.update({"openers":ops,"generated_lead":{"lead":raw,"company":comp,"job_title":title,"notes":notes,"tag":tag,"style":style,"length":length,"openers":ops,"timestamp":datetime.now(timezone.utc).isoformat()}})
            except Exception as e: st.error(f"Error: {e}")
    if "openers" in st.session_state:
        for i, op in enumerate(st.session_state["openers"], 1):
            st.markdown(f"### Opener {i}")
            if view == "Card": st.markdown(f"<div style='padding:1rem;border:1px solid #ccc;border-radius:8px'>{op}</div>",unsafe_allow_html=True)
            else: st.markdown(op)
            st.code(op, language='text')
        if st.session_state["authenticated"]:
            if st.button("Save Lead"): supabase.table("coldcraft").insert({**st.session_state["generated_lead"],"user_email":st.session_state["user_email"]}).execute(); st.success("Saved!")
        else: st.info("Login to save leads.")
        components.html("<script>window.scrollTo({top:document.body.scrollHeight});</script>", height=0)

# Saved Leads tab
if st.session_state["active_tab"] == "Saved Leads":
    st.title("📁 Saved Leads")
    try: res = supabase.table("coldcraft").select("*").eq("user_email",st.session_state["user_email"]).order("timestamp", desc=True).execute(); leads=res.data or []
    except Exception as e: st.error(f"Load failed: {e}"); leads=[]
    if not leads: st.info("No leads yet.")
    else:
        for lead in leads:
            txt=lead.get("lead","")[:120]+("..." if len(lead.get("lead",""))>120 else "")
            with st.expander(txt):
                st.markdown(
                    f"**Company:** {lead.get('company','')}  \n"
                    f"**Job Title:** {lead.get('job_title','')}  \n"
                    f"**Style/Length:** {lead.get('style','')} / {lead.get('length','')}  \n"
                    f"**Notes:** {lead.get('notes','')}  \n"
                    f"**Tag:** {lead.get('tag','')}"
                )
                for i, op in enumerate(lead.get("openers", []), 1): st.markdown(f"**Opener {i}:** {op}")
                if st.button("Delete", key=f"del{lead['id']}"): supabase.table("coldcraft").delete().eq("id",lead['id']).execute(); st.success("Deleted"); st.rerun()

if "openers" in st.session_state: components.html("<script>window.scrollTo({top:document.body.scrollHeight});</script>", height=0)
