import pymupdf as fitz
from docx import Document
import re
import spacy

nlp = spacy.load("en_core_web_sm")

SECTION_HEADERS = {
    "education": ["education", "academic qualification", "academic background"],
    "skills": ["technical skills", "skills", "core competencies", "technologies"],
    "experience": ["experience", "work experience", "employment", "work history"],
    "projects": ["projects", "personal projects", "academic projects"],
    "certifications": ["certifications", "certificates", "licenses"]
}

ALL_STOP_HEADERS = [
    "objective", "summary", "education", "academic qualification",
    "skills", "technical skills", "experience", "work experience",
    "employment", "projects", "personal projects", "academic projects",
    "certifications", "certificates", "achievements", "languages"
]


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
    ignore_prefixes = ("gmail:", "linkedin:", "github:", "mobile", "phone:", "email:", "http")
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    for line in lines[:5]:
        clean_line = line.lower()
        if any(clean_line.startswith(prefix) for prefix in ignore_prefixes):
            continue

        doc = nlp(line)
        for entity in doc.ents:
            if entity.label_ == "PERSON":
                return entity.text.strip()

        # Fallback: line near top with 1-4 words that isn't a URL or email
        words = line.split()
        if 1 <= len(words) <= 4 and not re.search(r"[@:/]", line):
            return line

    return None


def extract_section(text, target_headers):
    lines = text.splitlines()
    start = -1

    # Search for header line (Headers are short, typically <= 4 words)
    for i, line in enumerate(lines):
        clean_line = line.strip().lower()

        if len(clean_line.split()) <= 4:
            for header in target_headers:
                if clean_line == header or clean_line.startswith(header):
                    start = i
                    break
        if start != -1:
            break

    if start == -1:
        return []

    result = []
    for line in lines[start + 1:]:
        clean_line = line.strip().lower()

        # Stop if another section header is encountered
        if len(clean_line.split()) <= 4:
            if any(clean_line == stop or clean_line.startswith(stop) for stop in ALL_STOP_HEADERS):
                break

        if line.strip():
            result.append(line.strip())

    return result


def extract_skills(text):
    skill_list = [
        "python", "java", "javascript", "typescript", "html", "css",
        "react", "angular", "node.js", "express", "flask", "django",
        "spring boot", "sql", "mysql", "mongodb", "postgresql", "git",
        "github", "docker", "aws", "azure", "machine learning",
        "deep learning", "tensorflow", "pytorch", "opencv", "pandas", "numpy"
    ]

    text_lower = text.lower()
    found_skills = []

    for skill in skill_list:
        if skill.lower() in text_lower:
            found_skills.append(skill)

    return found_skills


def parse_resume(file_path):
    text = extract_text(file_path)

    return {
        "personal_information": {
            "name": extract_name(text),
            "email": extract_email(text),
            "phone": extract_phone(text)
        },
        "skills": extract_skills(text),
        "education": extract_section(text, SECTION_HEADERS["education"]),
        "experience": extract_section(text, SECTION_HEADERS["experience"]),
        "projects": extract_section(text, SECTION_HEADERS["projects"]),
        "certifications": extract_section(text, SECTION_HEADERS["certifications"]),
        "raw_text": text
    }