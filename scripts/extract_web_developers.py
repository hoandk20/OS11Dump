#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = ROOT / "data" / "Web developers" / "Web- developer-specialList.json"
OUTPUT_PATH = ROOT / "data" / "Web developers" / "web-developers-special-list.json"
INDEX_PATH = ROOT / "index.json"

QUESTION_ID = "web-developers-special-list"
QUESTION_TITLE = "Special List"
COURSE = {"id": "web-developers", "title": "Web developers"}
CATEGORY = "Web developers"

OPTION_SPLIT_RE = re.compile(r"\s*\|\s*")
QUESTION_OPTION_RE = re.compile(r"^(.*?)\s+([A-Da-d][\.\)])\s*(.*)$", re.S)
OPTION_RE = re.compile(r"([A-Da-d])[\.\)]\s*(.*?)(?=\s+[A-Da-d][\.\)]\s|$)", re.S)
ANSWER_RE = re.compile(r"^([A-Da-d])[\.\)]\s*(.*)$", re.S)


def normalize_space(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_question_and_options(raw_question: str) -> tuple[str, list[dict[str, str]]]:
    normalized = normalize_space(raw_question)
    match = QUESTION_OPTION_RE.match(normalized)
    if not match:
        raise ValueError(f"Could not parse question/options from: {raw_question[:120]}")

    question_text = normalize_space(match.group(1))
    options_blob = f"{match.group(2)} {match.group(3)}"
    options = []

    for option_match in OPTION_RE.finditer(options_blob):
        label = option_match.group(1).lower()
        text = normalize_space(option_match.group(2))
        options.append({"id": label, "text": text})

    if len(options) < 2:
        raise ValueError(f"Expected multiple options for question: {question_text[:120]}")

    return question_text, options


def parse_combined_question_and_answer(raw_question: str, raw_answer: str) -> tuple[str, list[dict[str, str]], str]:
    for separator in ['","', '", "', '" , "', ',"']:
        if separator not in raw_answer:
            continue
        stem_and_options, answer_blob = raw_answer.split(separator, 1)
        question_text, options = parse_question_and_options(f"{raw_question} {stem_and_options}")
        return question_text, options, normalize_space(answer_blob.strip('"'))

    combined = normalize_space(f"{raw_question} {raw_answer}")
    split_match = re.match(r"^(.*?)([A-Da-d][\.\)].*?)([A-Da-d](?:\s*(?:/|or|and)\s*[A-Da-d])?[\.\)].*)$", combined)
    if not split_match:
        raise ValueError(f"Could not recover malformed question/answer from: {combined[:160]}")

    question_text = normalize_space(split_match.group(1))
    options_blob = normalize_space(split_match.group(2))
    answer_blob = normalize_space(split_match.group(3))
    _, options = parse_question_and_options(f"{question_text} {options_blob}")
    return question_text, options, answer_blob


def parse_answer(raw_answer: str, options: list[dict[str, str]]) -> tuple[str, str | None]:
    normalized = normalize_space(raw_answer)
    match = ANSWER_RE.match(normalized)
    if not match:
        ambiguous_match = re.match(r"^([A-Da-d](?:\s*(?:/|or|and)\s*[A-Da-d])*)[\.\)]\s*(.*)$", normalized)
        if not ambiguous_match:
            raise ValueError(f"Could not parse answer from: {raw_answer}")
        correct_id = re.search(r"[A-Da-d]", ambiguous_match.group(1)).group(0).lower()  # type: ignore[union-attr]
        explanation = normalize_space(ambiguous_match.group(2)) or None
        return correct_id, explanation

    correct_id = match.group(1).lower()
    explanation = normalize_space(match.group(2)) or None

    option_ids = {option["id"] for option in options}
    if correct_id not in option_ids:
        raise ValueError(f"Answer {correct_id} not found in options {sorted(option_ids)}")

    return correct_id, explanation


def get_first_image(images: list[dict], key: str) -> str | None:
    for image in images:
        value = image.get(key)
        if isinstance(value, str) and value.startswith("data:"):
            return value
    return None


def build_dataset(raw_items: list[dict]) -> dict:
    questions = []

    for item in raw_items:
        question_number = int(item["index"])
        raw_question = str(item.get("question", ""))
        raw_answer = str(item.get("answer", ""))

        try:
            question_text, options = parse_question_and_options(raw_question)
            answer_input = raw_answer
        except ValueError:
            question_text, options, answer_input = parse_combined_question_and_answer(raw_question, raw_answer)

        correct_answer, explanation = parse_answer(answer_input, options)

        image = get_first_image(item.get("questionImages") or [], "dataUrl")
        if image is None:
            image = get_first_image(item.get("questionImages") or [], "base64")

        questions.append(
            {
                "id": f"{QUESTION_ID}-q{question_number:03d}",
                "question": question_text,
                "options": options,
                "correctAnswer": correct_answer,
                "explanation": explanation,
                "image": image,
                "category": CATEGORY,
                "source": {
                    "questionNumber": question_number,
                    "sourceType": "json",
                    "answerImages": len(item.get("answerImages") or []),
                    "questionImages": len(item.get("questionImages") or []),
                },
            }
        )

    description = f"{len(questions)} questions extracted from data/Web developers/Web- developer-specialList.json."
    return {
        "id": QUESTION_ID,
        "title": QUESTION_TITLE,
        "description": description,
        "questionCount": len(questions),
        "categories": [CATEGORY],
        "course": COURSE,
        "sourceFile": "data/Web developers/Web- developer-specialList.json",
        "questions": questions,
    }


def update_index(question_count: int) -> None:
    manifest = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    description = f"{question_count} questions extracted from data/Web developers/Web- developer-specialList.json."

    for exam in manifest.get("exams", []):
        if exam.get("id") == QUESTION_ID:
            exam["title"] = QUESTION_TITLE
            exam["description"] = description
            exam["questionCount"] = question_count
            exam["categories"] = [CATEGORY]
            exam["file"] = "data/Web developers/web-developers-special-list.json"
            exam["course"] = COURSE
            break
    else:
        manifest.setdefault("exams", []).append(
            {
                "id": QUESTION_ID,
                "title": QUESTION_TITLE,
                "description": description,
                "questionCount": question_count,
                "categories": [CATEGORY],
                "file": "data/Web developers/web-developers-special-list.json",
                "course": COURSE,
            }
        )

    manifest["examCount"] = len(manifest.get("exams", []))
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    INDEX_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> None:
    raw_items = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    dataset = build_dataset(raw_items)
    OUTPUT_PATH.write_text(json.dumps(dataset, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    update_index(dataset["questionCount"])
    print(f"Wrote {dataset['questionCount']} questions to {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
