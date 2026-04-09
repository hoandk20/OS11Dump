#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = ROOT / "data" / "Web developers" / "data.txt"
OUTPUT_PATH = ROOT / "data" / "Web developers" / "web-developers-special-list.json"
INDEX_PATH = ROOT / "index.json"

QUESTION_ID = "web-developers-special-list"
QUESTION_TITLE = "Special List"
QUESTION_DESCRIPTION = "208 questions extracted from data/Web developers/data.txt."
COURSE = {"id": "web-developers", "title": "Web developers"}
CATEGORY = "Web developers"

OPTION_LINE_RE = re.compile(r"^([a-d])\)\s*(.*)$", re.IGNORECASE)
ANSWER_RE = re.compile(r'^"?([a-d](?:\s*(?:/|or|and)\s*[a-d])*)\)\s*(.*)$', re.IGNORECASE)


class TermTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.capture = False
        self.depth = 0
        self.current: list[str] = []
        self.items: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "") or ""
        if not self.capture and tag == "span" and "TermText" in classes and "lang-en" in classes:
            self.capture = True
            self.depth = 1
            self.current = []
            return

        if self.capture:
            self.depth += 1
            if tag in {"br", "p", "div", "li"}:
                self.current.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self.capture:
            return

        if tag in {"p", "div", "li"}:
            self.current.append("\n")

        self.depth -= 1
        if self.depth == 0:
            self.items.append("".join(self.current))
            self.capture = False

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.current.append(data)


@dataclass
class ParsedQuestion:
    question: str
    options: list[dict[str, str]]
    answer_text: str
    inferred: bool = False


def normalize_lines(text: str) -> list[str]:
    lines = [re.sub(r"\s+", " ", unescape(line)).strip().strip('"') for line in text.split("\n")]
    return [line for line in lines if line]


def parse_question_block(lines: list[str]) -> tuple[str, list[dict[str, str]], str | None] | None:
    option_lines = [(index, line) for index, line in enumerate(lines) if OPTION_LINE_RE.match(line)]

    if len(option_lines) >= 4:
        first_option_index = option_lines[0][0]
        stem = " ".join(lines[:first_option_index]).strip().strip('"')
        options = []
        for _, raw_line in option_lines[:4]:
            match = OPTION_LINE_RE.match(raw_line)
            assert match is not None
            options.append({"id": match.group(1).lower(), "text": match.group(2).strip().strip('"')})
        remainder = " ".join(lines[option_lines[3][0] + 1 :]).strip().strip('"')
        return stem, options, remainder or None

    joined = " ".join(lines)
    joined = re.sub(r"\s+", " ", joined).strip().strip('"')
    positions: list[tuple[str, int]] = []
    search_from = 0

    for letter in "abcd":
        match = re.search(rf"(?i)(^|\s){letter}\)", joined[search_from:])
        if not match:
            return None
        pos = search_from + match.start(0) + (0 if match.group(1) == "" else 1)
        positions.append((letter, pos))
        search_from = pos + 2

    stem = joined[: positions[0][1]].strip().strip('"')
    options = []
    for index, (letter, pos) in enumerate(positions):
        end = positions[index + 1][1] if index + 1 < len(positions) else len(joined)
        chunk = joined[pos:end].strip()
        chunk = re.sub(rf"(?i)^{letter}\)\s*", "", chunk).strip().strip('"')
        options.append({"id": letter, "text": chunk})

    return stem, options, None


def extract_questions(raw_text: str) -> list[ParsedQuestion]:
    extractor = TermTextExtractor()
    extractor.feed(raw_text)
    items = [normalize_lines(item) for item in extractor.items]

    questions: list[ParsedQuestion] = []
    index = 0
    while index < len(items):
        lines = items[index]
        parsed = parse_question_block(lines)
        if parsed is None:
            index += 1
            continue

        question_text, options, inline_answer = parsed
        answer_text = inline_answer
        inferred = False

        if not answer_text and index + 1 < len(items):
            next_lines = items[index + 1]
            next_joined = " ".join(next_lines).strip()
            if ANSWER_RE.match(next_joined):
                answer_text = next_joined
                index += 1
            elif "run every weekday at 9:00 AM" in question_text and next_joined == "12:00 AM":
                answer_text = 'a) "09:00 Mon-Fri" is the intended weekday schedule.'
                inferred = True
                index += 1

        if not answer_text:
            raise ValueError(f"Could not determine answer for question: {question_text}")

        questions.append(
            ParsedQuestion(
                question=question_text,
                options=options,
                answer_text=answer_text,
                inferred=inferred,
            )
        )
        index += 1

    return questions


def build_dataset(parsed_questions: list[ParsedQuestion]) -> dict:
    questions = []

    for index, parsed in enumerate(parsed_questions, start=1):
        answer_match = ANSWER_RE.match(parsed.answer_text)
        if not answer_match:
            raise ValueError(f"Could not parse answer prefix: {parsed.answer_text}")

        raw_answer_key = answer_match.group(1).lower()
        correct_answer = re.search(r"[a-d]", raw_answer_key).group(0)  # type: ignore[union-attr]
        explanation = answer_match.group(2).strip().strip('"') or None

        source = {
            "rawAnswerKey": raw_answer_key,
            "ambiguous": raw_answer_key != correct_answer,
        }
        if parsed.inferred:
            source["inferred"] = True

        questions.append(
            {
                "id": f"{QUESTION_ID}-q{index:03d}",
                "question": parsed.question,
                "options": parsed.options,
                "correctAnswer": correct_answer,
                "explanation": explanation,
                "category": CATEGORY,
                "source": source,
            }
        )

    return {
        "id": QUESTION_ID,
        "title": QUESTION_TITLE,
        "description": QUESTION_DESCRIPTION,
        "questionCount": len(questions),
        "categories": [CATEGORY],
        "course": COURSE,
        "sourceFile": "data/Web developers/data.txt",
        "questions": questions,
    }


def update_index(question_count: int) -> None:
    manifest = json.loads(INDEX_PATH.read_text())
    for exam in manifest.get("exams", []):
        if exam.get("id") == QUESTION_ID:
            exam["description"] = "208 questions extracted from data/Web developers/data.txt."
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
                "description": "208 questions extracted from data/Web developers/data.txt.",
                "questionCount": question_count,
                "categories": [CATEGORY],
                "file": "data/Web developers/web-developers-special-list.json",
                "course": COURSE,
            }
        )
        manifest["examCount"] = len(manifest["exams"])

    manifest["examCount"] = len(manifest.get("exams", []))
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    INDEX_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n")


def main() -> None:
    raw_text = SOURCE_PATH.read_text()
    parsed_questions = extract_questions(raw_text)
    dataset = build_dataset(parsed_questions)
    OUTPUT_PATH.write_text(json.dumps(dataset, indent=2, ensure_ascii=True) + "\n")
    update_index(dataset["questionCount"])
    print(f"Wrote {dataset['questionCount']} questions to {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
