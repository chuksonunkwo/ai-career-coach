import gradio as gr
import google.generativeai as genai
from pypdf import PdfReader
import os
import markdown
from xhtml2pdf import pisa
import requests

# --- 1. CONFIGURATION ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("⚠️ SYSTEM ALERT: GEMINI_API_KEY is missing.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

# --- CRITICAL FIX: USING THE SECRET ID ---
# This matches the ID from your error message: A70XLqybP3M3f6C-euPZzg==
GUMROAD_PRODUCT_ID = "A70XLqybP3M3f6C-euPZzg=="

# --- 2. AUTHENTICATION LOGIC ---
def verify_gumroad_key(license_key):
    license_key = str(license_key).strip()
    
    if not license_key:
        return False, "⚠️ Please enter a license key."

    print(f"🔒 Verifying Key against ID: {GUMROAD_PRODUCT_ID}...")

    try:
        # We now use 'product_id' instead of 'product_permalink'
        response = requests.post(
            "https://api.gumroad.com/v2/licenses/verify",
            data={
                "product_id": GUMROAD_PRODUCT_ID,  # FIXED
                "license_key": license_key
            },
            timeout=10
        )
        
        data = response.json()
        print(f"Gumroad Response: {data}")

        if data.get("success") == True:
            if data["purchase"].get("refunded", False):
                return False, "❌ Access Denied: Refunded."
            return True, "✅ Success! Access Granted."
        else:
            return False, "❌ Invalid License Key. (Please check your email receipt)."
            
    except Exception as e:
        return False, f"⚠️ Connection Error: {e}"

# --- 3. PDF GENERATOR ---
def create_pdf(markdown_content):
    html_content = markdown.markdown(markdown_content)
    styled_html = f"<html><body>{html_content}</body></html>"
    output_filename = "Executive_Strategy_Report.pdf"
    with open(output_filename, "wb") as f:
        pisa.CreatePDF(styled_html, dest=f)
    return output_filename

# --- 4. CORE AI LOGIC ---
def extract_pdf_text(filepath):
    if not filepath: return ""
    try:
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages: text += page.extract_text() + "\n"
        return text
    except Exception as e: return str(e)

def career_coach_logic(license_key, resume_file, jd_file):
    is_valid, msg = verify_gumroad_key(license_key)
    if not is_valid:
        return f"🔒 SECURITY ALERT: {msg}", None

    if not resume_file or not jd_file:
        return "⚠️ Please upload BOTH files to begin.", None

    res_text = extract_pdf_text(resume_file)
    jd_text = extract_pdf_text(jd_file)

    prompt = f"""
    ROLE: Executive Career Strategist.
    INPUTS: RESUME: {res_text} | JD: {jd_text}
    OUTPUT: Strict Markdown.
    
    # 🏁 STRATEGIC ANALYSIS
    ## 🚦 Verdict
    * **Status:** [STRONG/POSSIBLE/WEAK]
    * **Summary:** (2 sentences)
    ## 🚩 Gaps
    * Gap 1...
    
    # ✍️ REWRITE
    ## 💎 Profile
    (Rewrite bio)
    ## 🚀 Experience
    (Top 2 roles rewritten)
    """
    
    try:
        response = model.generate_content(prompt)
        ai_text = response.text
        pdf_path = create_pdf(ai_text)
        return ai_text, pdf_path
    except Exception as e:
        return f"System Error: {e}", None

# --- 5. THE UI ---
LOGO_PATH = "logo.jpg" 

with gr.Blocks(theme=gr.themes.Soft()) as app:
    
    user_key_state = gr.State("")

    with gr.Column(visible=True) as login_view:
        gr.Markdown("## ")
        with gr.Row():
            with gr.Column(scale=1): pass
            with gr.Column(scale=2):
                
                # Safe Image Loader
                if os.path.exists(LOGO_PATH):
                    gr.Image(value=LOGO_PATH, show_label=False, height=200, container=False)
                else:
                    gr.Markdown("*(Logo missing: Please upload 'logo.jpg' to GitHub)*")

                gr.Markdown("# 🔒 Client Portal Access")
                gr.Markdown("Please enter your **Gumroad License Key** to proceed.")
                
                key_input = gr.Textbox(
                    label="License Key", 
                    placeholder="e.g. 14BCC8C0-...", 
                    type="password"
                )
                login_btn = gr.Button("Unlock Access", variant="primary")
                login_msg = gr.Markdown("")
            with gr.Column(scale=1): pass

    with gr.Column(visible=False) as main_view:
        with gr.Row():
            if os.path.exists(LOGO_PATH):
                gr.Image(value=LOGO_PATH, show_label=False, height=50, scale=0, container=False)
            gr.Markdown("# 🏛️ AI Career Architect")
        
        gr.Markdown("---")
        
        with gr.Row():
            res_upload = gr.File(label="📂 1. Upload Executive Resume (PDF)", file_types=[".pdf"])
            jd_upload = gr.File(label="🎯 2. Upload Target JD (PDF)", file_types=[".pdf"])
        
        generate_btn = gr.Button("✨ Generate Strategy & Rewrite", variant="primary", size="lg")
        
        with gr.Row():
            output_box = gr.Markdown(label="Strategic Analysis")
            pdf_download = gr.File(label="📄 Download Report")

    def attempt_login(key):
        is_valid, msg = verify_gumroad_key(key)
        if is_valid:
            return {
                login_view: gr.update(visible=False),
                main_view: gr.update(visible=True),
                user_key_state: key,
                login_msg: ""
            }
        else:
            return {
                login_view: gr.update(visible=True),
                main_view: gr.update(visible=False),
                user_key_state: "",
                login_msg: f"{msg}"
            }

    login_btn.click(attempt_login, inputs=[key_input], outputs=[login_view, main_view, user_key_state, login_msg])
    generate_btn.click(career_coach_logic, inputs=[user_key_state, res_upload, jd_upload], outputs=[output_box, pdf_download])

PORT = int(os.environ.get("PORT", 7860))
app.launch(server_name="0.0.0.0", server_port=PORT)
