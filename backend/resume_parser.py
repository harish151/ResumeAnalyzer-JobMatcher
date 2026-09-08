import pymupdf as fitz
from docx import Document
import re
import spacy

nlp = spacy.load("en_core_web_sm")


def extract_pdf_text(file_path):

    text = ""

    document = fitz.open(file_path)

    for page in document:
        text += page.get_text()

    document.close()

    return text


def extract_docx_text(file_path):

    document = Document(file_path)

    text = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            text.append(paragraph.text)

    return "\n".join(text)


def extract_text(file_path):

    if file_path.lower().endswith(".pdf"):
        return extract_pdf_text(file_path)

    elif file_path.lower().endswith(".docx"):
        return extract_docx_text(file_path)

    else:
        raise Exception("Unsupported file format")


def extract_email(text):

    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

    match = re.search(pattern, text)

    if match:
        return match.group()

    return None


def extract_phone(text):

    patterns = [
        r"\+91[-\s]?[6-9]\d{9}",
        r"\b[6-9]\d{9}\b"
    ]

    for pattern in patterns:

        match = re.search(pattern, text)

        if match:
            return match.group()

    return None


def extract_name(text):

    doc = nlp(text)

    for entity in doc.ents:

        if entity.label_ == "PERSON":

            return entity.text.strip()

    # fallback
    lines = text.split("\n")

    for line in lines[:5]:

        line = line.strip()

        if line and len(line.split()) <= 5:
            return line

    return None


def extract_section(text, section_names):

    lines = text.splitlines()

    start = -1

    for i, line in enumerate(lines):

        clean_line = line.strip().lower()

        for section in section_names:

            if section in clean_line:
                start = i
                break

        if start != -1:
            break

    if start == -1:
        return []

    result = []

    for line in lines[start + 1:]:

        clean_line = line.strip().lower()

        # Stop at another common section
        if clean_line in [
            "education",
            "experience",
            "work experience",
            "skills",
            "projects",
            "certifications",
            "achievements",
            "summary",
            "objective",
            "languages"
        ]:
            break

        if line.strip():
            result.append(line.strip())

    return result


def extract_skills(text):

    skill_list = [
        "python",
        "java",
        "javascript",
        "typescript",
        "html",
        "css",
        "react",
        "angular",
        "node.js",
        "express",
        "flask",
        "django",
        "spring boot",
        "sql",
        "mysql",
        "mongodb",
        "postgresql",
        "git",
        "github",
        "docker",
        "aws",
        "azure",
        "machine learning",
        "deep learning",
        "tensorflow",
        "pytorch",
        "opencv",
        "pandas",
        "numpy"
    ]

    text_lower = text.lower()

    found_skills = []

    for skill in skill_list:

        if skill.lower() in text_lower:
            found_skills.append(skill)

    return found_skills


def parse_resume(file_path):

    text = extract_text(file_path)

    education = extract_section(
        text,
        ["education", "academic qualification"]
    )

    experience = extract_section(
        text,
        ["experience", "work experience", "employment"]
    )

    projects = extract_section(
        text,
        ["projects", "personal projects", "academic projects"]
    )

    certifications = extract_section(
        text,
        ["certifications", "certificates"]
    )

    return {

        "personal_information": {
            "name": extract_name(text),
            "email": extract_email(text),
            "phone": extract_phone(text)
        },

        "skills": extract_skills(text),

        "education": education,

        "experience": experience,

        "projects": projects,

        "certifications": certifications,

        "raw_text": text
    }