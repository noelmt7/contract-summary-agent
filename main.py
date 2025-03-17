import streamlit as st
import typer
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import re
import nltk 
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import sys
from extract_text import extract_text
from summary_generation import generate_summary  # Removed ner_extraction

# Load environment variables
load_dotenv(Path(__file__).parent / '.env')

# Download necessary NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')


def preprocess_text(text):
    """Preprocess the text data"""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\d+', '', text)  # Remove numbers
    text = text.strip()
    return text


def main():
    """Command-line interface for the contract summary agent."""
    typer.echo("### 📄 Contract Summary Agent ###")
    print("Welcome to the Contract Summary Agent! Let's analyze your content.")

    # Get user input for file paths
    tender_path = typer.prompt("Enter the path to the tender document")
    template_path = typer.prompt("Enter the path to the template document")

    # Extract file extensions
    tender_type = tender_path.split('.')[-1].lower()
    template_type = template_path.split('.')[-1].lower()

    try:
        # Read file contents
        with open(tender_path, 'rb') as f:
            tender_data = f.read()
        with open(template_path, 'rb') as f:
            template_data = f.read()
        
        # Extract text from files
        tender_text = extract_text(tender_data, tender_type)
        template_text = extract_text(template_data, template_type)

        print("\nExtracting text from tender document...")
        print(f"Extracted {len(tender_text)} characters.")
        
        print("\nExtracting text from template document...")
        print(f"Extracted {len(template_text)} characters.")
        
        print("\nGenerating summary...")
        summary = generate_summary(tender_text, template_text)
        
        print("\n=== SUMMARY ===")
        print(summary)
        
    except FileNotFoundError:
        print("Error: One or both files not found. Please check the file paths.")
    except Exception as e:
        print(f"Error: {str(e)}")


def streamlit_ui():
    """Streamlit web UI for contract summarization."""
    st.set_page_config(page_title="Contract Summary Agent", page_icon="📄")
    st.title("📄 Contract Summary Agent")
    
    secret_token = st.text_input("Enter your secret token", type="password")
    if not secret_token or secret_token != st.secrets["CONTRACT_SUMMARY_TOKEN"]:
        st.error("Invalid secret token. Please try again.")
        return
    
    st.subheader("Upload files")

    # File uploader for tender & template documents
    tender_file = st.file_uploader("Upload tender document", type=["pdf", "docx", "txt"])
    template_file = st.file_uploader("Upload template document", type=["pdf", "docx", "txt"])

    if tender_file and template_file:
        st.success("Files uploaded successfully!")

        tender_type = tender_file.name.split('.')[-1].lower()
        template_type = template_file.name.split('.')[-1].lower()

        tender_text = extract_text(tender_file.read(), tender_type)
        template_text = extract_text(template_file.read(), template_type)

        with st.expander("View Extracted Tender Text"):
            st.text(tender_text)

        with st.expander("View Extracted Template Text"):
            st.text(template_text)

        if st.button("Generate Summary"):
            summary = generate_summary(tender_text, template_text)
            st.subheader("Summary")
            st.write(summary)

            # Download button for summary
            summary_bytes = summary.encode('utf-8')
            st.download_button(
                label="Download Summary",
                data=summary_bytes,
                file_name="summary.txt", 
                mime="text/plain"
            )


if __name__ == "__main__":
    if 'streamlit' in sys.modules:
        streamlit_ui()
    else:
        typer.run(main)
