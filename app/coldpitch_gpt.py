import streamlit as st
from supabase import create_client
from gotrue.errors import AuthApiError
import openai, os, time
from datetime import datetime

# 1) Page config + styling
st.set_page_config(page_title="ColdCraft", layout="centered")
st.markdown("""
<style>
html, body, .stApp { background-color: #f8f9fa; color: #111; }
textarea, input, select { background-color: #fff; color: #000; }
</style>
""", unsafe_allow_html=True)
st.image("https://i.imgur.com/fX4tDCb.png", width=200)

# 2) Session-state defaults
for key, default in {
    "authenticated": False,
    "guest": False,
    "user_email": "",
    "active_tab": "Login",
    "saved_num_openers": 3,
    "generated_openers": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# 3) Cached Supabase + OpenAI clients
@st.experimental_singleton
def get_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)

supabase = get_supabase()

@st.experimental_singleton
def init_openai():
    openai.api_key = (
        st.secrets.get("OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    return openai

init_openai()

# 4) LOGIN / GUEST tab
if st.session_state.active_tab == "Login":
    if not st.session_state.authenticated and not st.session_state.guest:
        st.subheader("🔐 Welcome to ColdCraft")
        st.write("Login or continue as guest to use the app.")
        with st.form("auth_form"):
            email = st.text_input("📧 Email")
            pwd   = st.text_input("🔑 Password", type="password")
            login_btn, guest_btn = st.form_submit_button("Login"), st.form_submit_button("Continue as Guest")
            if login_btn:
                try:
                    supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.active_tab = "Generator"
                    st.experimental_rerun()
                except AuthApiError as e:
                    st.error(f"❌ Login failed: {e}")
            if guest_btn:
                st.session_state.guest = True
                st.session_state.active_tab = "Generator"
                st.experimental_rerun()

        st.markdown("Don't have an account? [Sign up here](https://coldcraft.supabase.co/auth/sign-up)")
        st.stop()

# 5) SIDEBAR (logout / navigate)
with st.sidebar:
    st.markdown("### 👤 Session")
    if st.session_state.authenticated:
        st.write(f"Logged in as: {st.session_state.user_email}")
        if st.button("🚪 Log out"):
            supabase.auth.sign_out()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.session_state.active_tab = "Login"
            st.experimental_rerun()
        if st.button("📂 View My Saved Leads"):
            st.session_state.active_tab = "Saved Leads"
            st.experimental_rerun()
        if st.button("✍️ Generate New Email"):
            # don't clear saved_num_openers here—keep their last choice
            st.session_state.generated_openers = None
            st.session_state.active_tab = "Generator"
            st.experimental_rerun()
    elif st.session_state.guest:
        st.write("Guest access")
        if st.button("🚪 Exit Guest Mode"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.session_state.active_tab = "Login"
            st.experimental_rerun()

# 6) GENERATOR tab
if st.session_state.active_tab == "Generator":
    st.title("🧊 ColdCraft - Cold Email Generator")
    with st.form("generator_form"):
        raw_lead  = st.text_area("🔍 Paste LinkedIn bio, job post, or context:", height=200)
        company   = st.text_input("🏢 Lead's Company")
        job_title = st.text_input("💼 Lead's Job Title")
        notes     = st.text_input("📝 Private Notes")
        tag       = st.selectbox("🏷️ Tag this lead", ["None", "Hot", "Follow-up", "Cold", "Replied"])
        style     = st.selectbox("✍️ Tone/Style", ["Friendly", "Professional", "Funny", "Bold", "Casual"])
        length    = st.radio("📏 Opener length", ["Short", "Medium", "Long"], index=1)
        num_openers = st.slider(
            "📄 Number of openers", 1, 5, st.session_state.saved_num_openers
        )
        view_mode = st.radio("📀 Display Mode", ["List View", "Card View"], index=1)

        generate_btn = st.form_submit_button("Generate Openers")
        if generate_btn:
            # remember their slider choice
            st.session_state.saved_num_openers = num_openers

            # call OpenAI
            with st.spinner("🛠️ Generating..."):
                messages = [
                    {"role": "system", "content": "You’re a world-class cold email copywriter."},
                    {"role": "user", "content": (
                        f"Context: {raw_lead}\n"
                        f"Company: {company}\n"
                        f"Job Title: {job_title}\n"
                        f"Notes: {notes}\n"
                        f"Tone: {style}\n"
                        f"Length: {length}\n"
                        f"Count: {num_openers}"
                    )}
                ]
                resp = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens= num_openers * 50
                )
                text = resp.choices[0].message.content.strip()
                openers = [line for line in text.split("\n") if line.strip()]
                st.session_state.generated_openers = openers

            # save to Supabase if logged in
            if st.session_state.authenticated:
                try:
                    supabase.table("coldcraft").insert({
                        "user_email": st.session_state.user_email,
                        "lead": raw_lead,
                        "company": company,
                        "job_title": job_title,
                        "notes": notes,
                        "tag": tag,
                        "style": style,
                        "length": length,
                        "openers": openers,
                        "timestamp": datetime.utcnow().isoformat()
                    }).execute()
                    st.success("✔️ Openers saved to your account!")
                except Exception as e:
                    st.error(f"Failed to save: {e}")
            else:
                st.info("🔒 Sign up to save your leads permanently.")

    # render the results
    if st.session_state.generated_openers:
        if view_mode == "List View":
            for i, op in enumerate(st.session_state.generated_openers, 1):
                st.markdown(f"**Opener {i}:** {op}")
        else:
            cols = st.columns(len(st.session_state.generated_openers))
            for col, op in zip(cols, st.session_state.generated_openers):
                with col:
                    st.write(op)

# 7) SAVED LEADS tab
if st.session_state.active_tab == "Saved Leads":
    st.title("📁 Your Saved Leads")
    try:
        data = supabase.table("coldcraft") \
                        .select("*") \
                        .eq("user_email", st.session_state.user_email) \
                        .order("timestamp", desc=True) \
                        .execute()
        leads = data.data or []
    except Exception as e:
        st.error(f"Error loading leads: {e}")
        leads = []

    if not leads:
        st.info("No saved leads — try generating some over in the Generator tab!")
    else:
        for lead in leads:
            with st.expander(lead["lead"][:40] + "..."):
                st.write(f"**Company:** {lead['company']}")
                st.write(f"**Job Title:** {lead['job_title']}")
                st.write(f"**Style/Length:** {lead['style']} / {lead['length']}")
                st.write(f"**Notes:** {lead['notes']}")
                st.write(f"**Tag:** {lead['tag']}")
                for idx, opener in enumerate(lead["openers"], 1):
                    st.markdown(f"- **Opener {idx}:** {opener}")
