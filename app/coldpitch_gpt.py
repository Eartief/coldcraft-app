# file: app/coldpitch_gpt.py

import streamlit as st
import openai
import os
import pandas as pd
from io import StringIO

# --- Config ---
openai.api_key = os.getenv("OPENAI_API_KEY")
st.set_page_config(page_title="ColdPitchGPT", layout="centered")

# --- App Title ---
st.title("🚀 ColdPitchGPT: AI-Personalized Cold Email Generator")
st.markdown("Generate hyper-personalized email openers based on LinkedIn info.")

# --- Input Type Selection ---
input_mode = st.radio("Select Input Mode", ["Manual Entry", "CSV Upload"])

# --- Prompt Builder ---
def build_prompt(name, title, company, tone, notes):
    return f"""
Write a short, personalized cold email opener (1-2 sentences) for a prospect.

Name: {name}
Title: {title}
Company: {company}
Tone: {tone}
Extra Info: {notes if notes else 'N/A'}

Make it personalized, relevant, and engaging. Avoid cliches.
"""

# --- GPT Call Wrapper ---
def generate_email(name, title, company, tone, notes):
    prompt = build_prompt(name, title, company, tone, notes)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a B2B outbound sales expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Error: {e}"

# --- Manual Entry Form ---
if input_mode == "Manual Entry":
    with st.form("pitch_form"):
        name = st.text_input("Prospect Name")
        title = st.text_input("Job Title")
        company = st.text_input("Company")
        custom_notes = st.text_area("Custom Notes (optional)", placeholder="e.g. saw their talk at Web Summit...")
        tone = st.selectbox("Tone of Email", ["Friendly", "Direct", "Playful"])
        submitted = st.form_submit_button("Generate Cold Email")

    if submitted:
        if not name or not title or not company:
            st.error("Please fill in name, title, and company.")
        else:
            with st.spinner("Generating cold email..."):
                message = generate_email(name, title, company, tone, custom_notes)
                st.success("Cold email generated!")
                st.text_area("Generated Email Opener:", value=message, height=150)

# --- CSV Upload Mode ---
else:
    st.info("Upload a CSV with columns: name, title, company, notes (optional)")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            required_cols = {"name", "title", "company"}
            if not required_cols.issubset(df.columns):
                st.error("CSV must contain columns: name, title, company")
            else:
                st.success(f"{len(df)} rows loaded from CSV.")
                generate_bulk = st.button("Generate Email Variants for All Rows")
                if generate_bulk:
                    results = []
                    with st.spinner("Generating multiple variants for all rows..."):
                        for i, row in df.iterrows():
                            friendly = generate_email(row['name'], row['title'], row['company'], "Friendly", row.get('notes', ''))
                            direct = generate_email(row['name'], row['title'], row['company'], "Direct", row.get('notes', ''))
                            playful = generate_email(row['name'], row['title'], row['company'], "Playful", row.get('notes', ''))

                            results.append({
                                **row,
                                "cold_email_friendly": friendly,
                                "cold_email_direct": direct,
                                "cold_email_playful": playful
                            })

                    result_df = pd.DataFrame(results)
                    st.success("All email variants generated!")
                    st.dataframe(result_df)
                    csv_download = result_df.to_csv(index=False)
                    st.download_button("Download Results as CSV", csv_download, "cold_email_variants.csv", "text/csv")
        except Exception as e:
            st.error(f"Error processing file: {e}")
