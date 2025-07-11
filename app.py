import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import os
from markdown_it import MarkdownIt
from weasyprint import HTML, CSS
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
    md = MarkdownIt('commonmark', {'breaks': True, 'html': True}).enable('table')
    html_content = md.render(markdown_text)

    # Basic CSS for table styling
    css_style = '''
    @page {
        size: A4;
        margin: 1in;
    }
    body {
        font-family: sans-serif;
        font-size: 12px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 1em;
    }
    th, td {
        border: 1px solid #dddddd;
        padding: 8px;
        text-align: left;
    }
    th {
        background-color: #f2f2f2;
        font-weight: bold;
    }
    '''

    html = HTML(string=html_content)
    css = CSS(string=css_style)
    pdf_bytes = html.write_pdf(stylesheets=[css])
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
        value="""
Convert the following academic content into clear, structured study notes.

    Use precise and simplified language appropriate for learners at any level.

    Include all relevant facts, definitions, concepts, formulas, examples, and data.

    Use proper headings, subheadings, bullet points, and numbered lists.

    Avoid introductory or concluding phrases like "Here are your notes" or "In summary."

    Exclude all conversational language, metaphors, analogies, and storytelling.

    Notes must be comprehensive, self-contained, and formatted in clean Markdown.

    Do not skip technical details or simplify at the cost of accuracy.
"""


    )
    pdf_files = st.file_uploader("Upload your chapter PDFs", type="pdf", accept_multiple_files=True)
    generate_button = st.button("Generate Notes", type="primary")
    cancel_all_button = st.button("Cancel All Generations", type="secondary")
    download_all_markdown_button = st.button("Download All Notes as Markdown", type="secondary")
    download_all_pdf_button = st.button("Download All Notes as PDF", type="secondary")

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
                    "file": pdf_file,
                    "cancelled": False
                }

if cancel_all_button:
    for file_name in st.session_state.files:
        st.session_state.files[file_name]["cancelled"] = True
        st.session_state.files[file_name]["status"] = "Cancelled"
    st.rerun()

if download_all_markdown_button:
    all_notes_markdown = ""
    for file_name, file_data in st.session_state.files.items():
        if file_data["status"] == "Completed" and file_data["notes"]:
            all_notes_markdown += f"# Notes for {file_name.replace('.pdf', '')}\n\n"
            all_notes_markdown += file_data["notes"]
            all_notes_markdown += "\n\n---\n\n"
    if all_notes_markdown:
        st.download_button(
            label="Download All Notes as Markdown",
            data=all_notes_markdown,
            file_name="all_ncert_notes.md",
            mime="text/markdown",
            key="download_all_md"
        )
    else:
        st.warning("No completed notes to download as Markdown.")

if download_all_pdf_button:
    st.warning("Merging PDFs is not yet supported. Please download individual PDFs.")

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

    tabs = st.tabs(st.session_state.files.keys())
    for i, (file_name, file_data) in enumerate(st.session_state.files.items()):
        with tabs[i]:
            st.header(file_name)
            col1, col2 = st.columns([0.7, 0.3])
            with col1:
                st.write(f"Status: {file_data['status']}")
            with col2:
                if file_data["status"] in ["In Queue", "Processing"]:
                    if st.button("Cancel", key=f"cancel_{file_name}"):
                        st.session_state.files[file_name]["cancelled"] = True
                        st.session_state.files[file_name]["status"] = "Cancelled"
                        st.rerun()

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
            elif file_data["status"] == "Cancelled":
                st.warning("Note generation for this file has been cancelled.")

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
        if st.session_state.files[processing_file]["cancelled"]:
            st.session_state.files[processing_file]["status"] = "Cancelled"
            st.rerun()
        else:
            with st.spinner(f"Processing {processing_file}..."):
                pdf_file = st.session_state.files[processing_file]["file"]
                chapter_text = extract_text_from_pdf(pdf_file)
                
                if st.session_state.files[processing_file]["cancelled"]:
                    st.session_state.files[processing_file]["status"] = "Cancelled"
                    st.rerun()
                elif chapter_text:
                    notes = generate_notes_with_gemini(api_key, chapter_text, user_prompt)
                    
                    if st.session_state.files[processing_file]["cancelled"]:
                        st.session_state.files[processing_file]["status"] = "Cancelled"
                        st.rerun()
                    else:
                        st.session_state.files[processing_file]["notes"] = notes
                        if notes:
                            st.session_state.files[processing_file]["status"] = "Completed"
                        else:
                            st.session_state.files[processing_file]["status"] = "Failed"
                        st.rerun()
                else:
                    st.session_state.files[processing_file]["notes"] = None
                    st.session_state.files[processing_file]["status"] = "Failed"
                    st.rerun()
else:
    st.info("Please provide your API key, prompt, and upload PDFs in the sidebar to get started.")
