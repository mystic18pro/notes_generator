import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import os
from markdown_it import MarkdownIt
from weasyprint import HTML
import time

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="NCERT Notes Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Helper Functions ---

def markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    """
    Converts a Markdown string to a PDF and returns it as bytes.
    """
    md = MarkdownIt()
    html_content = md.render(markdown_text)
    html = HTML(string=html_content)
    pdf_bytes = html.write_pdf()
    return pdf_bytes

def extract_text_from_pdf(pdf_file):
    """
    Extracts text from an uploaded PDF file.
    """
    try:
        file_bytes = pdf_file.read()
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            text = ""
            for page in doc:
                text += page.get_text()
        return text
    except Exception as e:
        st.error(f"Error reading the PDF file: {e}")
        return None

def generate_notes_with_gemini(api_key, chapter_text, user_prompt):
    """
    Generates study notes from text using the Google Gemini Pro model.
    """
    try:
        genai.configure(api_key=api_key)
        
        prompt_template = f"""
{user_prompt}

Here is the chapter text:
---
{chapter_text}
---
"""
        model = genai.GenerativeModel('gemini-2.5-pro')
        response = model.generate_content(prompt_template)

        return response.text
    except Exception as e:
        st.error(f"An error occurred with the Gemini API: {e}")
        return None

# --- Streamlit App UI ---

st.title("📝 NCERT Chapter Notes Generator")
st.markdown("Upload an NCERT chapter in PDF format, and get well-structured, AI-generated study notes in Markdown.")

# --- Sidebar for Inputs ---
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input(
        "Enter your Google AI Studio API Key:",
        type="password",
        help="Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)"
    )
    user_prompt = st.text_area(
        "Enter your prompt for the notes generation (don't change anything if you are a normal user):",
        height=200,
        value='''You are an expert at creating concise and easy-to-understand study notes from complex academic texts. Based on the following text from an NCERT chapter, generate comprehensive study notes in Markdown format. Your notes must strictly follow these rules:
1. Main Title: Start with a single Level 1 Heading (`#`) for the chapter's main theme.
2. Topics & Sub-topics: Use Level 2 (`##`) and Level 3 (`###`) headings to structure the main topics and sub-topics logically.
3. Key Terms: Bold all important keywords, definitions, and names using `**Term**`.
4. Lists: Use bullet points (`*`) for important facts, features, characteristics, or steps.
5. Definitions: Enclose critical definitions or important statements in blockquotes (`>`).
6. Clarity: Ensure the language is simple, clear, and optimized for student revision. Do not include any conversational text or introductions like 'Here are the notes...'. The output must be pure Markdown.'''
    )
    pdf_files = st.file_uploader("Upload your chapter PDFs", type="pdf", accept_multiple_files=True)
    generate_button = st.button("Generate Notes", type="primary")

# --- Main Application Logic ---
if 'files' not in st.session_state:
    st.session_state.files = {}

if generate_button:
    if not api_key:
        st.warning("Please enter your Google AI Studio API key in the sidebar.")
    elif not pdf_files:
        st.warning("Please upload at least one PDF file.")
    elif not user_prompt:
        st.warning("Please enter a prompt.")
    else:
        for pdf_file in pdf_files:
            if pdf_file.name not in st.session_state.files:
                st.session_state.files[pdf_file.name] = {
                    "status": "In Queue",
                    "notes": None,
                    "file": pdf_file
                }

if any(st.session_state.files):
    
    processing_file = None
    for file_name, file_data in st.session_state.files.items():
        if file_data["status"] == "Processing":
            processing_file = file_name
            break

    if not processing_file:
        for file_name, file_data in st.session_state.files.items():
            if file_data["status"] == "In Queue":
                st.session_state.files[file_name]["status"] = "Processing"
                processing_file = file_name
                break

    if processing_file:
        with st.spinner(f"Processing {processing_file}..."):
            pdf_file = st.session_state.files[processing_file]["file"]
            chapter_text = extract_text_from_pdf(pdf_file)
            if chapter_text:
                notes = generate_notes_with_gemini(api_key, chapter_text, user_prompt)
                st.session_state.files[processing_file]["notes"] = notes
                if notes:
                    st.session_state.files[processing_file]["status"] = "Completed"
                else:
                    st.session_state.files[processing_file]["status"] = "Failed"
                st.rerun()
            else:
                st.session_state.files[processing_file]["notes"] = None
                st.session_state.files[processing_file]["status"] = "Failed"
                st.experimental_rerun()

    tabs = st.tabs(st.session_state.files.keys())
    for i, (file_name, file_data) in enumerate(st.session_state.files.items()):
        with tabs[i]:
            st.header(file_name)
            st.write(f"Status: {file_data['status']}")

            if file_data["status"] == "Completed" and file_data["notes"]:
                st.markdown(file_data["notes"])
                st.download_button(
                    label="Download Notes as Markdown",
                    data=file_data["notes"],
                    file_name=f"{file_name.replace('.pdf', '')}_notes.md",
                    mime="text/markdown",
                )
                pdf_bytes = markdown_to_pdf_bytes(file_data["notes"])
                st.download_button(
                    label="Download Notes as PDF",
                    data=pdf_bytes,
                    file_name=f"{file_name.replace('.pdf', '')}_notes.pdf",
                    mime="application/pdf",
                )
            elif file_data["status"] == "Failed":
                st.error("Note generation failed for this file. Please check the logs or try again.")
else:
    st.info("Please provide your API key, prompt, and upload PDFs in the sidebar to get started.")
