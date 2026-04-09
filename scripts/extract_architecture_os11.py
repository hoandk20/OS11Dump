#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "Architecture OS11"
JSON_SOURCE_PATH = DATA_DIR / "Architecture Special List 011.json"
OUTPUT_PATH = DATA_DIR / "architecture-os11-question-bank.json"
INDEX_PATH = ROOT / "index.json"

EXAM_ID = "architecture-os11-question-bank"
EXAM_TITLE = "Question Bank"
COURSE = {"id": "architecture-os11", "title": "Architecture OS11"}
CATEGORY = "Architecture OS11"
LEADING_OPTION_RE = re.compile(r"^[A-Z][\.\)]\s*")


def normalize_space(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_option(value: str) -> str:
    return normalize_space(LEADING_OPTION_RE.sub("", value))


def parse_questions_from_json(raw_items: list[dict]) -> tuple[list[dict], str]:
    questions = []

    for item in raw_items:
        question_number = int(item["questionNumber"])
        raw_options = item.get("options") or []
        if not raw_options:
            raise ValueError(f"Question {question_number} has no options")

        options = []
        for option in raw_options:
            label = normalize_space(str(option.get("label", ""))).lower()
            if not label:
                option_index = int(option.get("index", len(options)))
                label = chr(97 + option_index)
            options.append(
                {
                    "id": label,
                    "text": normalize_option(str(option.get("text", ""))),
                }
            )

        correct_index = int(item["correctIndex"])
        if correct_index < 0 or correct_index >= len(options):
            raise ValueError(f"Question {question_number} has invalid correctIndex {correct_index}")

        correct_answer = options[correct_index]["id"]
        image = None
        if item.get("images"):
            image = item["images"][0].get("dataUrl")

        questions.append(
            {
                "id": f"{EXAM_ID}-q{question_number:03d}",
                "question": normalize_space(str(item.get("question", ""))),
                "options": options,
                "correctAnswer": correct_answer,
                "explanation": normalize_option(str(item.get("correctText", ""))) or None,
                "image": image,
                "category": CATEGORY,
                "source": {
                    "questionNumber": question_number,
                    "correctIndex": correct_index,
                    "correctLabel": item.get("correctLabel"),
                    "detectMethod": item.get("detectMethod"),
                    "sourceType": "json",
                },
            }
        )

    return questions, "data/Architecture OS11/Architecture Special List 011.json"


def load_questions() -> tuple[list[dict], str]:
    if JSON_SOURCE_PATH.is_file():
        raw_items = json.loads(JSON_SOURCE_PATH.read_text(encoding="utf-8"))
        return parse_questions_from_json(raw_items)

    raise FileNotFoundError("Architecture OS11 JSON source file not found")


def write_dataset(questions: list[dict], source_file: str) -> None:
    dataset = {
        "id": EXAM_ID,
        "title": EXAM_TITLE,
        "description": f"{len(questions)} questions extracted from {source_file}.",
        "questionCount": len(questions),
        "categories": [CATEGORY],
        "course": COURSE,
        "sourceFile": source_file,
        "questions": questions,
    }
    OUTPUT_PATH.write_text(json.dumps(dataset, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def update_index(question_count: int, source_file: str) -> None:
    manifest = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    description = f"{question_count} questions extracted from {source_file}."

    for exam in manifest.get("exams", []):
        if exam.get("id") == EXAM_ID:
            exam["title"] = EXAM_TITLE
            exam["description"] = description
            exam["questionCount"] = question_count
            exam["categories"] = [CATEGORY]
            exam["file"] = "data/Architecture OS11/architecture-os11-question-bank.json"
            exam["course"] = COURSE
            break
    else:
        manifest.setdefault("exams", []).append(
            {
                "id": EXAM_ID,
                "title": EXAM_TITLE,
                "description": description,
                "questionCount": question_count,
                "categories": [CATEGORY],
                "file": "data/Architecture OS11/architecture-os11-question-bank.json",
                "course": COURSE,
            }
        )

    manifest["examCount"] = len(manifest.get("exams", []))
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    INDEX_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> None:
    questions, source_file = load_questions()
    write_dataset(questions, source_file)
    update_index(len(questions), source_file)
    print(f"Wrote {len(questions)} questions to {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
