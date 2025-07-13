# app/coldpitch_gpt.py

import streamlit as st
import openai
import os
import re
import time
from datetime import datetime
from supabase import create_client, Client
from gotrue.errors import AuthApiError

# ---------- CONFIG ----------
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]
openai.api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = get_supabase()

if "initialized" not in st.session_state:
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
    st.session_state.initialized = True

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "guest" not in st.session_state:
    st.session_state["guest"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "Login"

# ---------- LOGIN PAGE ----------
if st.session_state["active_tab"] == "Login":
    if not st.session_state["authenticated"] and not st.session_state["guest"]:
        st.subheader("🔐 Welcome to ColdCraft")
        st.write("Login or continue as guest to use the app.")

        with st.form("login_form"):
            email = st.text_input("📧 Email")
            password = st.text_input("🔑 Password", type="password")
            login_btn = st.form_submit_button("Login")

            if login_btn:
                try:
                    supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    st.session_state["authenticated"] = True
                    st.session_state["user_email"] = email
                    st.session_state["active_tab"] = "Generator"
                    st.success(f"✅ Logged in as {email}")
                    st.rerun()
                except AuthApiError as e:
                    st.error(f"❌ Login failed: {e}")

        st.markdown("Don't have an account? [Sign up here](https://coldcraft.supabase.co/auth/sign-up)")
        if st.button("Continue as Guest"):
            st.session_state["guest"] = True
            st.session_state["active_tab"] = "Generator"
            st.success("✅ Continuing as guest...")
            st.rerun()
        st.stop()

# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("### 👤 Session")
    if st.session_state["authenticated"]:
        st.write(f"Logged in as: {st.session_state['user_email']}")
        if st.button("🚪 Log out"):
            supabase.auth.sign_out()
            st.session_state["authenticated"] = False
            st.session_state["user_email"] = ""
            st.session_state["active_tab"] = "Login"
            st.rerun()
        if st.button("📂 View My Saved Leads"):
            st.session_state["active_tab"] = "Saved Leads"
            st.rerun()
        if st.button("✍️ Generate New Email"):
            st.session_state["active_tab"] = "Generator"
            st.rerun()
    elif st.session_state["guest"]:
        st.write("Guest access")
        if st.button("🚪 Exit Guest Mode"):
            st.session_state["guest"] = False
            st.session_state["active_tab"] = "Login"
            st.rerun()

# ---------- ROUTING ----------
if st.session_state["active_tab"] == "Saved Leads":
    st.title("📁 Saved Leads")
    user_email = st.session_state.get("user_email", "")
    try:
        data = supabase.table("coldcraft").select("*").eq("user_email", user_email).order("timestamp", desc=True).execute()
        leads = data.data
        if not leads:
            st.info("No leads saved yet.")
        for lead in leads:
            with st.expander(f"{lead.get('lead')[:40]}..."):
                st.write(f"**Company**: {lead.get('company')}")
                st.write(f"**Job Title**: {lead.get('job_title')}")
                st.write(f"**Style**: {lead.get('style')} | **Length**: {lead.get('length')}")
                st.write(f"**Notes**: {lead.get('notes')}")
                st.write(f"**Tag**: {lead.get('tag')}")
                for idx, opener in enumerate(lead.get("openers", [])):
                    st.markdown(f"**Opener {idx+1}:** {opener}")
    except Exception as e:
        st.error(f"Failed to load saved leads: {e}")

# include the generator logic
if st.session_state["active_tab"] == "Generator":
    # include generator block here (was previously working)
    st.write("🔧 Generator interface goes here. (temporarily hidden)")
