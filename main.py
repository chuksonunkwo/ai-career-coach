import gradio as gr
import google.generativeai as genai
from pypdf import PdfReader
import os

# --- CONFIGURATION FOR RENDER ---
# We get the key from Render's "Environment Variables" setting
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise ValueError("⚠️ GEMINI_API_KEY not found! Set this in Render Dashboard.")

# Configure the Brain
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash") # Or "gemini-1.5-pro"

def extract_pdf_text(filepath):
    if not filepath: return ""
    try:
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading file: {e}"

def career_coach_logic(resume_file, jd_file):
    if not resume_file or not jd_file:
        return "⚠️ Please upload BOTH files to start."

    # Read files
    res_text = extract_pdf_text(resume_file)
    jd_text = extract_pdf_text(jd_file)

    # --- THE EXECUTIVE LOGIC (KEPT INTACT) ---
    prompt = f"""
    # Executive Strategy Prompt (System-Level) — BLUF Reporting Enabled

    ROLE: Executive Career Strategist (C-suite/VP/Director caliber).

    INPUTS:
    1) RESUME: {res_text}
    2) JOB DESCRIPTION: {jd_text}

    OBJECTIVE:
    Assess executive-level fit and produce a BLUF-first report.

    OUTPUT FORMAT (STRICT MARKDOWN):

    # 🏁 BLUF: The Verdict
    - Status: [STRONG MATCH | POSSIBLE MATCH | WEAK MATCH]
    - Score: [0–100]
    - One-line verdict: (Summary)

    ---
    # 🚩 Critical Gaps
    - Gap 1: (What is missing)
    - Gap 2: (What is missing)

    ---
    # ✍️ Executive Resume Rewrite
    (Rewrite the top 2 roles using CAR format - Context, Action, Result)

    ---
    # ✉️ The Hook
    (3-sentence executive email opener)
    """
    
    # Generate
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

# --- THE UI (Password Protected) ---
with gr.Blocks(theme=gr.themes.Soft(primary_hue="slate")) as app:
    gr.Markdown("# 🏛️ Executive Career Architect")
    gr.Markdown("Exclusive Access. Please log in.")
    
    with gr.Row():
        res_upload = gr.File(label="1. Executive Resume (PDF)", file_types=[".pdf"])
        jd_upload = gr.File(label="2. Target Job Description (PDF)", file_types=[".pdf"])
    
    btn = gr.Button("Generate Strategy", variant="primary", size="lg")
    output_box = gr.Markdown(label="Strategic Analysis")
    
    btn.click(fn=career_coach_logic, inputs=[res_upload, jd_upload], outputs=output_box)

# --- LAUNCH FOR RENDER ---
# Render gives us a PORT environment variable. We must listen on it.
PORT = int(os.environ.get("PORT", 7860))
app.launch(server_name="0.0.0.0", server_port=PORT, auth=("vip_user", "career2026"))
