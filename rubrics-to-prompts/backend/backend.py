from pathlib import Path
from openai import OpenAI
from PIL import Image
import pandas as pd
from docx import Document
import mammoth
import pytesseract
import pdfplumber
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def upload_file(file_path):
    file = Path(file_path)
    suffix = file.suffix.lower()

    if suffix == ".pdf":  # works correctly
        results = parse_pdf(file_path)

    # elif suffix in {".png", ".jpg", ".jpeg"}:     # need to install tesseract engine sep
    #     img = Image.open(file_path)
    #     text = pytesseract.image_to_string(img)
    #     results = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]

    elif suffix == ".docx": # works correctly
        doc = Document(file_path)
        results = [para.text.strip() for para in doc.paragraphs if para.text.strip()]

    elif suffix == ".doc":
        with open(file_path, "rb") as doc_file:
            result = mammoth.convert_to_text(doc_file)
            text = result.value
            results = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]

    elif suffix in {".xlsx", ".xls"}: # .xslx worked, need to test legacy
        df = pd.read_excel(file_path)
        results = df.apply(
            lambda row: " | ".join(str(v) for v in row if pd.notnull(v)), axis=1
        ).tolist()

    elif suffix == ".csv":  # works correctly
        try:
            df = pd.read_csv(file_path, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding="latin1")

        headers = df.columns.tolist()
        results = []
        for _, row in df.iterrows():
            row_values = [
                str(row[col]).strip() if pd.notnull(row[col]) else "" for col in headers
            ]
            combined = " | ".join(
                f"{col}: {val}" for col, val in zip(headers, row_values) if val
            )
            if combined:
                results.append(combined)

    return generate_rubric_with_llm(results)


def parse_pdf(path):
    chunks = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")
            buffer = ""
            for line in lines:
                line = line.strip()
                if not line:
                    if buffer:
                        chunks.append(buffer.strip())
                        buffer = ""
                else:
                    buffer += " " + line
            if buffer:
                chunks.append(buffer.strip())

    return chunks


def generate_rubric_with_llm(chunks):
    prompt = f"""
    You're an expert assistant. Based on the following extracted rubric text, generate a list of structured rubric criteria in YAML format.

    Rubric Text:
    {chr(10).join(f'- {chunk}' for chunk in chunks)}
    """

    response = client.responses.create(
        model="gpt-4o-mini-2024-07-18",
        input=[
            {
                "role": "system",
                "content": "You help format rubrics from unstructured text.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    return response.output_text


def main():
    print(upload_file("Station 1B - Skin Concern - Tinea.docx"))


if __name__ == "__main__":
    main()
