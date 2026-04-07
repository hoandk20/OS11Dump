#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
OUTPUT_DIR = ROOT / "data" / "TechLeadOS11"
ROOT_MANIFEST = ROOT / "index.json"
ROOT_SCHEMA = ROOT / "schema.json"
WRAPPER_MARKER = '<div class="result-pane--question-result-pane-wrapper--2bGiz">'
ANSWER_MARKER = '<div class="result-pane--answer-result-pane--Niazi">'


@dataclass
class ParsedQuestion:
    question: str
    options: list[dict[str, str]]
    correct_answer: str
    category: str | None


def strip_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</(p|div|li|ul|ol)>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = unescape(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_first(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.S)
    return strip_html(match.group(1)) if match else None


def parse_question(block: str) -> ParsedQuestion | None:
    question_text = extract_first(r'id="question-prompt">(.*?)</div>', block)
    if not question_text:
        return None

    options: list[dict[str, str]] = []
    correct_answer: str | None = None

    for index, answer_block in enumerate(block.split(ANSWER_MARKER)[1:], start=1):
        option_text = extract_first(r'id="answer-text">(.*?)</div>', answer_block)
        if not option_text:
            continue

        option_id = chr(96 + index)
        options.append({"id": option_id, "text": option_text})

        if "answer-result-pane--answer-correct" in answer_block:
            correct_answer = option_id

    if not options or correct_answer is None:
        raise ValueError(f"Unable to extract options or correct answer for question: {question_text[:80]}")

    category = extract_first(
        r'<div class="domain-pane--domain-pane-header--2263m ud-heading-md">.*?</div>\s*<div class="ud-text-md">(.*?)</div>',
        block,
    )

    return ParsedQuestion(
        question=question_text,
        options=options,
        correct_answer=correct_answer,
        category=category,
    )


def parse_exam(source_file: Path) -> dict:
    raw_html = source_file.read_text(encoding="utf-8", errors="ignore")
    title = extract_first(r'<h2[^>]*data-purpose="title"[^>]*>(.*?)</h2>', raw_html) or source_file.stem
    title = title.replace(" - Kết quả", "").strip()

    question_blocks = []
    for block in raw_html.split(WRAPPER_MARKER)[1:]:
        if 'id="question-prompt"' not in block:
            continue
        question_blocks.append(block)

    parsed_questions = [parse_question(block) for block in question_blocks]
    parsed_questions = [question for question in parsed_questions if question is not None]

    exam_id = source_file.stem.lower().replace("dump", "dump-")
    categories = sorted({question.category for question in parsed_questions if question.category})

    questions = []
    for index, question in enumerate(parsed_questions, start=1):
        questions.append(
            {
                "id": f"{exam_id}-q{index:03d}",
                "question": question.question,
                "options": question.options,
                "correctAnswer": question.correct_answer,
                "explanation": None,
                "category": question.category,
                "source": {
                    "rawFile": f"raw/{source_file.name}",
                    "questionNumber": index,
                },
            }
        )

    return {
        "id": exam_id,
        "title": title,
        "description": f"{len(questions)} questions extracted from {source_file.name}. Explanations were not present in the source HTML.",
        "questionCount": len(questions),
        "categories": categories,
        "sourceFile": f"raw/{source_file.name}",
        "questions": questions,
    }


def write_schema() -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "TechLead OS11 Exam Schema",
        "type": "object",
        "required": ["id", "title", "description", "questionCount", "questions"],
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "questionCount": {"type": "integer", "minimum": 1},
            "categories": {
                "type": "array",
                "items": {"type": "string"},
            },
            "sourceFile": {"type": "string"},
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "question", "options", "correctAnswer"],
                    "properties": {
                        "id": {"type": "string"},
                        "question": {"type": "string"},
                        "options": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["id", "text"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "text": {"type": "string"},
                                },
                            },
                        },
                        "correctAnswer": {"type": "string"},
                        "explanation": {"type": ["string", "null"]},
                        "category": {"type": ["string", "null"]},
                        "source": {"type": "object"},
                    },
                },
            },
        },
    }
    ROOT_SCHEMA.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    exams = [parse_exam(path) for path in sorted(RAW_DIR.glob("Dump*.html"))]

    manifest = {
        "id": "techlead-os11",
        "title": "TechLead OS11 Exam Practice",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "examCount": len(exams),
        "exams": [],
    }

    for exam in exams:
        exam_file = OUTPUT_DIR / f"{exam['id']}.json"
        exam_file.write_text(json.dumps(exam, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        manifest["exams"].append(
            {
                "id": exam["id"],
                "title": exam["title"],
                "description": exam["description"],
                "questionCount": exam["questionCount"],
                "categories": exam["categories"],
                "file": f"data/TechLeadOS11/{exam['id']}.json",
            }
        )

    ROOT_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_schema()


if __name__ == "__main__":
    main()
