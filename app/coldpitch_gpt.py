import streamlit as st
import random
import re

st.set_page_config(page_title='ColdCraft', layout='centered')
st.title('🧊 ColdCraft - Cold Email Generator')
st.write('Paste your lead info below and get a personalized cold email opener.')

# Input form
lead = st.text_area("🔍 Paste LinkedIn bio, job post, or context about your lead:", height=200)

if st.button("✉️ Generate Cold Email"):
    if not lead.strip():
        st.warning("Please enter some lead info first.")
    else:
        # Normalize input
        cleaned_lead = re.sub(r'[^\w\s]', '', lead.strip().lower())

        # Enhanced example openers using keywords
        templates = [
            "Hey there — loved your work on '{}', wanted to connect!",
            "Saw your profile mentioning '{}', really impressive — had to reach out.",
            "What you're doing around '{}' is super interesting. Let’s talk."
        ]

        # Pick keyword to personalize the message
        words = cleaned_lead.split()
        keyword = words[0] if words else "your recent work"

        result = random.choice(templates).format(keyword)
        st.success("✅ Generated cold opener:")
        st.text(result)  # plain text instead of markdown
