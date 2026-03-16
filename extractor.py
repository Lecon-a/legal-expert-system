import os
import pdfplumber
import docx


def extract_text(file_path):
    """
    Extracts text from PDF, DOCX, or TXT files.
    Returns a string. Returns a descriptive message for unsupported formats.
    """
    ext = os.path.splitext(file_path)[1].lower()
    text_chunks = []

    try:
        if ext == ".pdf":
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_chunks.append(page_text)

        elif ext == ".docx":
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                if para.text.strip():
                    text_chunks.append(para.text)

        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                text_chunks.append(f.read())

        else:
            return "Unsupported document format."

    except Exception as e:
        return f"Error extracting text: {e}"

    return "\n".join(text_chunks)