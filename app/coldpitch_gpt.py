import streamlit as st
import openai
import os
import re
from datetime import datetime
from supabase import create_client, Client
from gotrue.errors import AuthApiError
import streamlit.components.v1 as components

# Configuration\SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]
CONFIRMATION_REDIRECT_URL = st.secrets.get(
    "confirmation_redirect_url",
    os.getenv("CONFIRMATION_REDIRECT_URL")
)
openai.api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# Restore auth session
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    try:
        supabase.auth.set_session({
            "access_token": st.session_state["access_token"],
            "refresh_token": st.session_state["refresh_token"]
        })
    except Exception:
        pass

# Get current session
db_session = supabase.auth.get_session()
if db_session and db_session.user:
    st.session_state["authenticated"] = True
    st.session_state["user_email"] = db_session.user.email
else:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user_email", "")
    st.session_state.setdefault("guest", False)

# Initialize state defaults
st.session_state.setdefault("active_tab", "Login")
st.session_state.setdefault("saved_num_openers", 3)
if st.session_state.get("reset_generator_form"):
    for key in ["openers", "generated_lead"]:
        st.session_state.pop(key, None)
    for key in ["raw_lead", "company", "job_title", "notes", "tag", "style", "length", "view_mode"]:
        st.session_state.pop(key, None)
    st.session_state["reset_generator_form"] = False

# Page config
st.set_page_config(page_title='ColdCraft', layout='centered')
st.markdown(
    """
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
""", unsafe_allow_html=True
)
st.image("https://i.imgur.com/fX4tDCb.png", width=200)

# Sidebar
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

# Login/Signup
if st.session_state["active_tab"] == "Login":
    if not st.session_state["authenticated"] and not st.session_state["guest"]:
        st.subheader("🔐 Welcome to ColdCraft")
        mode = st.radio(
            "Choose action:", ["Login", "Sign up"], horizontal=True
        )
        if mode == "Login":
            with st.form("auth_form"):
                email = st.text_input("📧 Email")
                pwd = st.text_input("🔑 Password", type="password")
                login_btn = st.form_submit_button("Login")
                guest_btn = st.form_submit_button("Continue as Guest")
                if login_btn:
                    try:
                        resp = supabase.auth.sign_in_with_password({
                            "email": email,
                            "password": pwd
                        })
                        session = getattr(resp, 'session', None)
                        user = getattr(resp, 'user', None)
                        if not session or not user:
                            st.error("❌ Invalid credentials")
                        else:
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
        else:
            with st.form("signup_form"):
                new_email = st.text_input(
                    "📧 Email", key="su_email"
                )
                new_pwd = st.text_input(
                    "🔑 Password",
                    type="password",
                    key="su_pwd"
                )
                confirm_pwd = st.text_input(
                    "🔑 Confirm Password",
                    type="password",
                    key="su_confirm"
                )
                signup_btn = st.form_submit_button("Sign Up")
                if signup_btn:
                    if new_pwd != confirm_pwd:
                        st.error("❌ Passwords do not match.")
                    else:
                        try:
                            resp = supabase.auth.sign_up(
                                email=new_email,
                                password=new_pwd,
                                redirect_to=CONFIRMATION_REDIRECT_URL
                            )
                            session = getattr(resp, 'session', None)
                            user = getattr(resp, 'user', None)
                            if session and user:
                                st.session_state["access_token"] = session.access_token
                                st.session_state["refresh_token"] = session.refresh_token
                                st.session_state["authenticated"] = True
                                st.session_state["user_email"] = user.email
                                st.session_state["active_tab"] = "Generator"
                                st.success("✅ Account created and logged in!")
                                st.rerun()
                            else:
                                st.info("✅ Check email for confirmation link.")
                                st.session_state["active_tab"] = "Login"
                                st.rerun()
                        except AuthApiError as e:
                            st.error(f"❌ Sign-up failed: {e}")
        st.stop()

# Generator\...
