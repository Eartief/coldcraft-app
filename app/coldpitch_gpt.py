# app/coldpitch_gpt.py

[... code unchanged up to GENERATOR UI ...]

# ---------- GENERATOR UI ----------
if st.session_state["active_tab"] == "Generator":
    st.title("🧊 ColdCraft - Cold Email Generator")
    st.write("Paste your lead info below and get a personalized cold email opener.")

    raw_lead = st.text_area("🔍 Paste LinkedIn bio, job post, or context about your lead:", height=200)
    company = st.text_input("🏢 Lead's Company:")
    job_title = st.text_input("💼 Lead's Job Title:")
    notes = st.text_input("📝 Private Notes:")
    tag = st.selectbox("🏷️ Tag this lead", ["None", "Hot", "Follow-up", "Cold", "Replied"], index=0)
    style = st.selectbox("✍️ Tone/Style", ["Friendly", "Professional", "Funny", "Bold", "Casual"])
    length = st.radio("📏 Opener length:", ["Short", "Medium", "Long"], index=1)
    num_openers = st.slider("📄 Number of openers:", min_value=1, max_value=5, value=3)
    view_mode = st.radio("📀 Display Mode", ["List View", "Card View"], index=1)

    lead = clean_lead(raw_lead)

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
                    openers = parse_openers(result, num_openers)
                    duration = round(time.time() - start_time, 2)

                    # persist values
                    st.session_state.openers = openers
                    st.session_state.generated_lead = {
                        "timestamp": datetime.now().isoformat(),
                        "lead": lead,
                        "company": company,
                        "job_title": job_title,
                        "style": style,
                        "length": length,
                        "notes": notes,
                        "tag": tag,
                        "openers": openers[:num_openers],
                        "user_email": st.session_state["user_email"]
                    }

                    st.success("✅ Generated cold openers:")
                    combined_output = "\n\n".join(openers)

                    for idx, opener in enumerate(openers):
                        st.markdown(f"### ✉️ Opener {idx+1}")
                        if view_mode == "Card View":
                            st.markdown(
                                f"<div style='padding: 1rem; margin-bottom: 1rem; border-radius: 12px; background-color: rgba(240,240,255,0.1); border: 1px solid rgba(200,200,200,0.3); box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>{opener}</div>",
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(opener)
                        st.code(opener, language='text')

                    st.text_area("📋 All Openers (copy manually if needed):", combined_output, height=150)
                    st.caption(f"⏱️ Generated in {duration} seconds | 📏 {len(result)} characters")

                except Exception as e:
                    st.error(f"❌ Error generating openers: {e}")

    # ---------- SAVE LOGIC ----------
    if st.session_state.get("openers"):
        if st.session_state["authenticated"]:
            if st.button("💾 Save This Lead"):
                try:
                    supabase.table("coldcraft").insert(st.session_state.generated_lead).execute()
                    st.success("✅ Lead saved to Supabase.")
                except Exception as db_err:
                    st.error(f"❌ Failed to save to Supabase: {db_err}")
        else:
            st.info("Log in to save leads.")
