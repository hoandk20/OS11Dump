#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "TechLeadOS11"
MANIFEST_PATH = ROOT / "index.json"

SOURCE_FILES = [
    ("TechLead1.json", "dump-01", "Dump 01"),
    ("techlead2.json", "dump-02", "Dump 02"),
    ("techlead3.json", "dump-03", "Dump 03"),
    ("techlead4.json", "dump-04", "Dump 04"),
    ("techlead5.json", "dump-05", "Dump 05"),
    ("techlead6.json", "dump-06", "Dump 06"),
]


def normalize_space(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_question_text(value: str) -> str:
    return normalize_space(value)


def normalize_answer_text(value: str) -> str:
    value = normalize_space(value)
    value = re.sub(r"^[A-D][\.\)]\s+", "", value)
    return value.strip()


def get_correct_answer_id(answers: list[dict]) -> str:
    correct_indexes = [index for index, answer in enumerate(answers) if answer.get("isCorrect") is True]
    if len(correct_indexes) != 1:
        raise ValueError(f"Expected exactly one correct answer, found {len(correct_indexes)}")
    return chr(97 + correct_indexes[0])


def get_first_image(images: list[dict]) -> str | None:
    for image in images:
        base64_value = image.get("base64")
        if isinstance(base64_value, str) and base64_value.startswith("data:"):
            return base64_value
    return None


def parse_exam(source_name: str, exam_id: str, title: str) -> dict:
    source_path = DATA_DIR / source_name
    items = json.loads(source_path.read_text(encoding="utf-8"))

    questions = []
    categories = set()

    for index, item in enumerate(items, start=1):
        raw_answers = item.get("answers") or []
        if not raw_answers:
            raise ValueError(f"{source_name} question {index} has no answers")

        options = []
        for option_index, answer in enumerate(raw_answers, start=1):
            option_id = chr(96 + option_index)
            options.append(
                {
                    "id": option_id,
                    "text": normalize_answer_text(str(answer.get("text", ""))),
                }
            )

        correct_answer_id = get_correct_answer_id(raw_answers)
        image_data = get_first_image(item.get("images") or [])
        category = item.get("category")
        if isinstance(category, str):
            category = normalize_space(category)
        else:
            category = None

        if category:
            categories.add(category)

        question_text = normalize_question_text(str(item.get("question", "")))
        if not question_text:
            raise ValueError(f"{source_name} question {index} is empty")

        questions.append(
            {
                "id": f"{exam_id}-q{index:03d}",
                "question": question_text,
                "options": options,
                "correctAnswer": correct_answer_id,
                "explanation": None,
                "image": image_data,
                "category": category,
                "source": {
                    "rawFile": f"data/TechLeadOS11/{source_name}",
                    "questionNumber": item.get("questionNumber") or index,
                    "correctAnswerText": normalize_space(str(item.get("correctAnswer", ""))) or None,
                    "imageCount": len(item.get("images") or []),
                },
            }
        )

    return {
        "id": exam_id,
        "title": title,
        "description": f"{len(questions)} questions normalized from data/TechLeadOS11/{source_name}.",
        "questionCount": len(questions),
        "categories": sorted(categories) if categories else ["Outsystems"],
        "sourceFile": f"data/TechLeadOS11/{source_name}",
        "course": {
            "id": "outsystems-techlead",
            "title": "Outsystems TechLead",
        },
        "questions": questions,
    }


def update_manifest(exams: list[dict]) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    exam_by_id = {exam["id"]: exam for exam in exams}

    for item in manifest.get("exams", []):
        exam_id = item.get("id")
        if exam_id not in exam_by_id:
            continue
        exam = exam_by_id[exam_id]
        item["title"] = exam["title"]
        item["description"] = exam["description"]
        item["questionCount"] = exam["questionCount"]
        item["categories"] = exam["categories"]
        item["file"] = f"data/TechLeadOS11/{exam_id}.json"
        item["course"] = exam["course"]

    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    manifest["examCount"] = len(manifest.get("exams", []))
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    exams = []
    for source_name, exam_id, title in SOURCE_FILES:
        exam = parse_exam(source_name, exam_id, title)
        output_path = DATA_DIR / f"{exam_id}.json"
        output_path.write_text(json.dumps(exam, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        exams.append(exam)

    update_manifest(exams)


if __name__ == "__main__":
    main()
