#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = ROOT / "data" / "Outystems Reactive OS11" / "data.json"
OUTPUT_PATH = ROOT / "data" / "Outystems Reactive OS11" / "outsystems-reactive-os11-question-bank.json"
INDEX_PATH = ROOT / "index.json"

EXAM_ID = "outsystems-reactive-os11-question-bank"
EXAM_TITLE = "Question Bank"
COURSE = {"id": "outsystems-reactive-os11", "title": "Outsystems Reactive OS11"}
CATEGORY = "Outsystems Reactive OS11"

LEADING_OPTION_RE = re.compile(r"^[A-D]\.\s*")
LEADING_NUMBER_RE = re.compile(r"^\d+\.\s*")


def normalize_question(text: str) -> str:
    return re.sub(r"\s+", " ", LEADING_NUMBER_RE.sub("", text)).strip()


def normalize_option(text: str) -> str:
    return re.sub(r"\s+", " ", LEADING_OPTION_RE.sub("", text)).strip()


def extract_questions() -> list[dict]:
    raw_items = json.loads(SOURCE_PATH.read_text())
    questions = []

    for item in raw_items:
        options = [
            {
                "id": option["label"].lower(),
                "text": normalize_option(option["text"]),
            }
            for option in item["options"]
        ]

        correct_answer = options[item["correctIndex"]]["id"]
        image = None
        if item.get("images"):
            image = item["images"][0].get("dataUrl")

        questions.append(
            {
                "id": f"{EXAM_ID}-q{item['questionNumber']:03d}",
                "question": normalize_question(item["question"]),
                "options": options,
                "correctAnswer": correct_answer,
                "explanation": normalize_option(item.get("correctText", "")) or None,
                "image": image,
                "category": CATEGORY,
                "source": {
                    "questionNumber": item["questionNumber"],
                    "correctIndex": item["correctIndex"],
                    "detectMethod": item.get("detectMethod"),
                },
            }
        )

    return questions


def write_dataset(questions: list[dict]) -> None:
    dataset = {
        "id": EXAM_ID,
        "title": EXAM_TITLE,
        "description": f"{len(questions)} questions extracted from data/Outystems Reactive OS11/data.json.",
        "questionCount": len(questions),
        "categories": [CATEGORY],
        "course": COURSE,
        "sourceFile": "data/Outystems Reactive OS11/data.json",
        "questions": questions,
    }
    OUTPUT_PATH.write_text(json.dumps(dataset, indent=2, ensure_ascii=True) + "\n")


def update_index(question_count: int) -> None:
    manifest = json.loads(INDEX_PATH.read_text())

    for exam in manifest.get("exams", []):
        if exam.get("id") == EXAM_ID:
            exam["title"] = EXAM_TITLE
            exam["description"] = f"{question_count} questions extracted from data/Outystems Reactive OS11/data.json."
            exam["questionCount"] = question_count
            exam["categories"] = [CATEGORY]
            exam["file"] = "data/Outystems Reactive OS11/outsystems-reactive-os11-question-bank.json"
            exam["course"] = COURSE
            break
    else:
        manifest.setdefault("exams", []).append(
            {
                "id": EXAM_ID,
                "title": EXAM_TITLE,
                "description": f"{question_count} questions extracted from data/Outystems Reactive OS11/data.json.",
                "questionCount": question_count,
                "categories": [CATEGORY],
                "file": "data/Outystems Reactive OS11/outsystems-reactive-os11-question-bank.json",
                "course": COURSE,
            }
        )

    manifest["examCount"] = len(manifest.get("exams", []))
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    INDEX_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n")


def main() -> None:
    questions = extract_questions()
    write_dataset(questions)
    update_index(len(questions))
    print(f"Wrote {len(questions)} questions to {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
