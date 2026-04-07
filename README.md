# TechLead OS11 Practice Website

## Project structure

```text
.
├── app.js
├── index.html
├── index.json
├── schema.json
├── style.css
├── raw/
│   └── Dump01.html ... Dump06.html
├── scripts/
│   └── extract_techlead_os11.py
└── data/
    └── TechLeadOS11/
        └── dump-01.json ... dump-06.json
```

## Data assumptions

- The Udemy export pages consistently contain question text, answer options, the correct answer, and category.
- The source files do **not** include explanations, so `explanation` is stored as `null`.
- Each question is treated as a single-choice question because each source question exposes one correct answer.

## JSON schema shape

```json
{
  "id": "dump-01",
  "title": "Dump 01",
  "description": "50 questions extracted from Dump01.html. Explanations were not present in the source HTML.",
  "questionCount": 50,
  "categories": ["Outsystems"],
  "sourceFile": "raw/Dump01.html",
  "questions": [
    {
      "id": "dump-01-q001",
      "question": "When integrating with an ERP with hundreds of APIs, across several business areas, you should:",
      "options": [
        { "id": "a", "text": "Create a Driver module per functional area..." }
      ],
      "correctAnswer": "c",
      "explanation": null,
      "category": "Outsystems"
    }
  ]
}
```

## Run locally

Browsers usually block `fetch()` calls from `file://`. Run a tiny local server from the project root instead:

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Regenerate JSON after adding raw files

1. Put the new exported files into `raw/`.
2. Run:

```bash
python3 scripts/extract_techlead_os11.py
```

The script regenerates:

- `index.json`
- `schema.json`
- one JSON file per exam set

## Add a new exam set later

1. Save the exported HTML result page into `raw/`.
2. Keep the same question/result structure used by the existing dumps.
3. Run the extraction script again.
4. The homepage updates automatically because the app reads `index.json`.

## Current feature set

- Homepage with exam set list
- Exam mode and practice mode
- Randomize questions and answer choices
- Progress indicator and question navigator
- Final scoring summary
- Review screen with correct answers
- Retry flow
- Saved progress and last result via `localStorage`
