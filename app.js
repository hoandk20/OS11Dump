"use strict";

const DATASET_URL = "index.json";
const STORAGE_PREFIX = "techlead-os11";
const THEME_KEY = `${STORAGE_PREFIX}:theme`;
const EXAM_GROUPS = [
  {
    id: "outsystems-techlead",
    title: "Outsystems TechLead",
    match: () => true,
  },
];

const state = {
  manifest: null,
  examCache: new Map(),
  activeExam: null,
  session: null,
  review: null,
};

const elements = {
  homeScreen: document.getElementById("home-screen"),
  examScreen: document.getElementById("exam-screen"),
  resultScreen: document.getElementById("result-screen"),
  examList: document.getElementById("exam-list"),
  datasetSummary: document.getElementById("dataset-summary"),
  messageBanner: document.getElementById("message-banner"),
  modeSelect: document.getElementById("mode-select"),
  shuffleQuestions: document.getElementById("shuffle-questions"),
  shuffleOptions: document.getElementById("shuffle-options"),
  themeToggleButton: document.getElementById("theme-toggle-button"),
  backHomeButton: document.getElementById("back-home-button"),
  examTitle: document.getElementById("exam-title"),
  examDescription: document.getElementById("exam-description"),
  modePill: document.getElementById("mode-pill"),
  progressLabel: document.getElementById("progress-label"),
  currentLabel: document.getElementById("current-label"),
  progressFill: document.getElementById("progress-fill"),
  questionNav: document.getElementById("question-nav"),
  submitExamButton: document.getElementById("submit-exam-button"),
  retryExamButton: document.getElementById("retry-exam-button"),
  questionBadge: document.getElementById("question-badge"),
  questionCategory: document.getElementById("question-category"),
  questionText: document.getElementById("question-text"),
  optionsForm: document.getElementById("options-form"),
  feedbackPanel: document.getElementById("feedback-panel"),
  previousButton: document.getElementById("previous-button"),
  nextButton: document.getElementById("next-button"),
  checkAnswerButton: document.getElementById("check-answer-button"),
  resultTitle: document.getElementById("result-title"),
  resultSubtitle: document.getElementById("result-subtitle"),
  scoreValue: document.getElementById("score-value"),
  correctValue: document.getElementById("correct-value"),
  incorrectValue: document.getElementById("incorrect-value"),
  unansweredValue: document.getElementById("unanswered-value"),
  reviewList: document.getElementById("review-list"),
  retryResultButton: document.getElementById("retry-result-button"),
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  applyTheme(readTheme());
  bindEvents();

  try {
    const manifest = await fetchJson(DATASET_URL);
    state.manifest = manifest;
    renderHome();
    showScreen("home");
  } catch (error) {
    renderBanner(
      "Unable to load JSON data. Open the project through a local HTTP server instead of `file://` so the browser can fetch `index.json` and the exam files."
    );
    console.error(error);
  }
}

function bindEvents() {
  elements.themeToggleButton.addEventListener("click", toggleTheme);

  elements.backHomeButton.addEventListener("click", () => {
    state.session = null;
    state.review = null;
    showScreen("home");
    renderHome();
  });

  elements.previousButton.addEventListener("click", () => moveQuestion(-1));
  elements.nextButton.addEventListener("click", handleNext);
  elements.checkAnswerButton.addEventListener("click", handleCheckAnswer);
  elements.submitExamButton.addEventListener("click", finishSession);
  elements.retryExamButton.addEventListener("click", retryCurrentExam);
  elements.retryResultButton.addEventListener("click", retryCurrentExam);
}

function readTheme() {
  return localStorage.getItem(THEME_KEY) || "dark";
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  elements.themeToggleButton.textContent = theme === "light" ? "Dark mode" : "White mode";
}

function toggleTheme() {
  const nextTheme = readTheme() === "light" ? "dark" : "light";
  localStorage.setItem(THEME_KEY, nextTheme);
  applyTheme(nextTheme);
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load ${url}: ${response.status}`);
  }
  return response.json();
}

function renderBanner(message) {
  elements.messageBanner.textContent = message;
  elements.messageBanner.classList.remove("hidden");
}

function clearBanner() {
  elements.messageBanner.textContent = "";
  elements.messageBanner.classList.add("hidden");
}

function getHomeSettings() {
  return {
    mode: elements.modeSelect.value,
    shuffleQuestions: elements.shuffleQuestions.checked,
    shuffleOptions: elements.shuffleOptions.checked,
  };
}

function renderHome() {
  clearBanner();

  const exams = state.manifest?.exams ?? [];
  const questionTotal = exams.reduce((total, exam) => total + exam.questionCount, 0);
  elements.datasetSummary.textContent = `${exams.length} exam sets • ${questionTotal} questions`;

  elements.examList.innerHTML = "";

  const groups = buildExamGroups(exams);
  groups.forEach((group) => {
    const section = document.createElement("section");
    section.className = "folder-group";

    const folderHeader = document.createElement("button");
    folderHeader.type = "button";
    folderHeader.className = "folder-header";
    folderHeader.setAttribute("aria-expanded", "true");
    folderHeader.innerHTML = `
      <div>
        <div class="folder-title-row">
          <span class="folder-icon">📁</span>
          <h3>${escapeHtml(group.title)}</h3>
        </div>
        <p class="muted">${group.exams.length} exam sets • ${group.questionTotal} questions</p>
      </div>
      <span class="folder-toggle">▾</span>
    `;

    const folderContent = document.createElement("div");
    folderContent.className = "folder-content exam-list";

    folderHeader.addEventListener("click", () => {
      const isCollapsed = folderContent.classList.toggle("collapsed");
      folderHeader.setAttribute("aria-expanded", String(!isCollapsed));
      folderHeader.querySelector(".folder-toggle").textContent = isCollapsed ? "▸" : "▾";
    });

    group.exams.forEach((exam) => {
      folderContent.appendChild(createExamCard(exam));
    });

    section.appendChild(folderHeader);
    section.appendChild(folderContent);
    elements.examList.appendChild(section);
  });

  elements.examList.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const examId = button.dataset.examId;
      if (button.dataset.action === "resume") {
        await resumeExam(examId);
        return;
      }
      await startExam(examId, getHomeSettings());
    });
  });
}

function buildExamGroups(exams) {
  return EXAM_GROUPS.map((group) => {
    const groupedExams = exams.filter(group.match);
    return {
      ...group,
      exams: groupedExams,
      questionTotal: groupedExams.reduce((total, exam) => total + exam.questionCount, 0),
    };
  }).filter((group) => group.exams.length > 0);
}

function createExamCard(exam) {
    const lastResult = readLastResult(exam.id);
    const hasResume = Boolean(readSession(exam.id));

    const article = document.createElement("article");
    article.className = "exam-card";
    article.innerHTML = `
      <h3>${escapeHtml(exam.title)}</h3>
      <p class="muted">${escapeHtml(exam.description)}</p>
      <div class="exam-meta">
        <span class="chip">${exam.questionCount} questions</span>
        ${(exam.categories || []).map((category) => `<span class="chip">${escapeHtml(category)}</span>`).join("")}
      </div>
      ${
        lastResult
          ? `<p class="muted">Last result: ${lastResult.correct}/${lastResult.total} correct (${lastResult.score}%).</p>`
          : `<p class="muted">No saved result yet.</p>`
      }
      <div class="card-actions">
        <button class="primary-button" type="button" data-action="start" data-exam-id="${exam.id}">Start exam</button>
        ${
          hasResume
            ? `<button class="ghost-button" type="button" data-action="resume" data-exam-id="${exam.id}">Resume</button>`
            : ""
        }
      </div>
    `;
    return article;
}

async function getExam(examId) {
  if (state.examCache.has(examId)) {
    return state.examCache.get(examId);
  }

  const entry = state.manifest.exams.find((exam) => exam.id === examId);
  const exam = await fetchJson(entry.file);
  state.examCache.set(examId, exam);
  return exam;
}

async function startExam(examId, settings) {
  const exam = await getExam(examId);
  state.activeExam = exam;
  state.review = null;

  // Build a session copy so source JSON remains immutable and can be reused.
  const questions = exam.questions.map((question) => ({
    ...question,
    options: question.options.map((option) => ({ ...option })),
  }));

  if (settings.shuffleQuestions) {
    shuffleArray(questions);
  }

  if (settings.shuffleOptions) {
    questions.forEach((question) => {
      shuffleArray(question.options);
    });
  }

  state.session = {
    examId,
    mode: settings.mode,
    shuffleQuestions: settings.shuffleQuestions,
    shuffleOptions: settings.shuffleOptions,
    currentIndex: 0,
    startedAt: new Date().toISOString(),
    questions,
    answers: {},
    checked: {},
  };

  persistSession();
  renderExam();
  showScreen("exam");
}

async function resumeExam(examId) {
  const saved = readSession(examId);
  if (!saved) {
    await startExam(examId, getHomeSettings());
    return;
  }

  state.activeExam = await getExam(examId);
  state.review = null;
  state.session = saved;
  renderExam();
  showScreen("exam");
}

function renderExam() {
  const { questions, currentIndex, mode, answers, checked } = state.session;
  const currentQuestion = questions[currentIndex];
  const answeredCount = Object.keys(answers).length;
  const checkedCount = Object.values(checked).filter(Boolean).length;
  const progressBase = mode === "practice" ? checkedCount : answeredCount;
  const progressPercent = questions.length ? Math.round((progressBase / questions.length) * 100) : 0;

  elements.examTitle.textContent = state.activeExam.title;
  elements.examDescription.textContent = state.activeExam.description;
  elements.modePill.textContent = mode === "practice" ? "Practice mode" : "Exam mode";
  elements.progressLabel.textContent = `${answeredCount} / ${questions.length} answered`;
  elements.currentLabel.textContent = `Question ${currentIndex + 1} of ${questions.length}`;
  elements.progressFill.style.width = `${progressPercent}%`;
  elements.questionBadge.textContent = `Question ${currentIndex + 1}`;
  elements.questionText.textContent = currentQuestion.question;

  if (currentQuestion.category) {
    elements.questionCategory.textContent = currentQuestion.category;
    elements.questionCategory.classList.remove("hidden");
  } else {
    elements.questionCategory.classList.add("hidden");
  }

  renderOptions(currentQuestion);
  renderQuestionNav();
  renderFeedback(currentQuestion);

  elements.previousButton.disabled = currentIndex === 0;
  elements.nextButton.textContent = currentIndex === questions.length - 1 ? "Finish" : "Next";
  elements.submitExamButton.classList.toggle("hidden", mode === "practice");
  elements.checkAnswerButton.classList.toggle("hidden", mode !== "practice");
}

function renderOptions(question) {
  const selected = state.session.answers[question.id];
  const isChecked = Boolean(state.session.checked[question.id]);
  const mode = state.session.mode;

  elements.optionsForm.innerHTML = "";

  question.options.forEach((option) => {
    const label = document.createElement("label");
    label.className = "option-card";

    if (selected === option.id) {
      label.classList.add("selected");
    }

    if (mode === "practice" && isChecked) {
      if (option.id === question.correctAnswer) {
        label.classList.add("correct");
      } else if (selected === option.id) {
        label.classList.add("incorrect");
      }
    }

    label.innerHTML = `
      <input type="radio" name="answer" value="${option.id}" ${selected === option.id ? "checked" : ""} ${mode === "practice" && isChecked ? "disabled" : ""}>
      <span class="option-id">${option.id}</span>
      <span>${escapeHtml(option.text)}</span>
    `;

    label.querySelector("input").addEventListener("change", (event) => {
      state.session.answers[question.id] = event.target.value;
      persistSession();
      renderExam();
    });

    elements.optionsForm.appendChild(label);
  });
}

function renderQuestionNav() {
  elements.questionNav.innerHTML = "";

  state.session.questions.forEach((question, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = index + 1;

    if (index === state.session.currentIndex) {
      button.classList.add("current");
    }
    if (state.session.answers[question.id]) {
      button.classList.add("answered");
    }
    if (state.session.checked[question.id]) {
      button.classList.add("reviewed");
    }

    button.addEventListener("click", () => {
      state.session.currentIndex = index;
      persistSession();
      renderExam();
    });

    elements.questionNav.appendChild(button);
  });
}

function renderFeedback(question) {
  const mode = state.session.mode;
  const selected = state.session.answers[question.id];
  const isChecked = Boolean(state.session.checked[question.id]);

  if (mode !== "practice" || !isChecked) {
    elements.feedbackPanel.className = "feedback-panel hidden";
    elements.feedbackPanel.innerHTML = "";
    return;
  }

  const isCorrect = selected === question.correctAnswer;
  const correctOption = question.options.find((option) => option.id === question.correctAnswer);
  const explanation = question.explanation || "No explanation was available in the source documents.";

  elements.feedbackPanel.className = `feedback-panel ${isCorrect ? "success" : "error"}`;
  elements.feedbackPanel.innerHTML = `
    <strong>${isCorrect ? "Correct answer." : "Incorrect answer."}</strong>
    <p>Correct option: <strong>${question.correctAnswer.toUpperCase()}</strong> — ${escapeHtml(correctOption?.text || "")}</p>
    <p>${escapeHtml(explanation)}</p>
  `;
}

function handleCheckAnswer() {
  const question = state.session.questions[state.session.currentIndex];
  if (!state.session.answers[question.id]) {
    renderBanner("Select an option before checking the answer.");
    return;
  }

  clearBanner();
  state.session.checked[question.id] = true;
  persistSession();
  renderExam();
}

function handleNext() {
  clearBanner();

  const lastIndex = state.session.questions.length - 1;

  if (state.session.mode === "practice") {
    const question = state.session.questions[state.session.currentIndex];
    if (!state.session.checked[question.id]) {
      renderBanner("Check the current answer before moving to the next question.");
      return;
    }
  }

  if (state.session.currentIndex >= lastIndex) {
    finishSession();
    return;
  }

  state.session.currentIndex += 1;
  persistSession();
  renderExam();
}

function moveQuestion(delta) {
  clearBanner();
  const nextIndex = state.session.currentIndex + delta;
  if (nextIndex < 0 || nextIndex >= state.session.questions.length) {
    return;
  }
  state.session.currentIndex = nextIndex;
  persistSession();
  renderExam();
}

function finishSession() {
  clearBanner();

  const review = buildReview(state.session);
  state.review = review;
  saveLastResult(state.session.examId, review.summary);
  clearSession(state.session.examId);

  renderResults();
  showScreen("results");
}

function buildReview(session) {
  let correct = 0;
  let incorrect = 0;
  let unanswered = 0;

  const questions = session.questions.map((question, index) => {
    const selected = session.answers[question.id] || null;
    const correctOption = question.options.find((option) => option.id === question.correctAnswer) || null;
    const selectedOption = question.options.find((option) => option.id === selected) || null;

    let status = "unanswered";
    if (!selected) {
      unanswered += 1;
    } else if (selected === question.correctAnswer) {
      status = "correct";
      correct += 1;
    } else {
      status = "incorrect";
      incorrect += 1;
    }

    return {
      index: index + 1,
      status,
      question,
      selected,
      selectedOption,
      correctOption,
    };
  });

  const total = session.questions.length;
  const score = total ? Math.round((correct / total) * 100) : 0;

  return {
    summary: {
      examId: session.examId,
      mode: session.mode,
      correct,
      incorrect,
      unanswered,
      total,
      score,
      completedAt: new Date().toISOString(),
    },
    questions,
  };
}

function renderResults() {
  const { summary, questions } = state.review;

  elements.resultTitle.textContent = `${state.activeExam.title} results`;
  elements.resultSubtitle.textContent = `${summary.mode === "practice" ? "Practice mode" : "Exam mode"} • ${summary.total} questions`;
  elements.scoreValue.textContent = `${summary.score}%`;
  elements.correctValue.textContent = String(summary.correct);
  elements.incorrectValue.textContent = String(summary.incorrect);
  elements.unansweredValue.textContent = String(summary.unanswered);

  elements.reviewList.innerHTML = "";

  questions.forEach((item) => {
    const article = document.createElement("article");
    article.className = `review-card ${item.status}`;
    article.innerHTML = `
      <div class="review-meta">
        <span class="chip">Question ${item.index}</span>
        <span class="chip">${capitalize(item.status)}</span>
        ${item.question.category ? `<span class="chip">${escapeHtml(item.question.category)}</span>` : ""}
      </div>
      <h3>${escapeHtml(item.question.question)}</h3>
      <p class="review-answer">Your answer: ${
        item.selectedOption ? `${item.selectedOption.id.toUpperCase()} — ${escapeHtml(item.selectedOption.text)}` : "Not answered"
      }</p>
      <p class="review-answer">Correct answer: ${
        item.correctOption ? `${item.correctOption.id.toUpperCase()} — ${escapeHtml(item.correctOption.text)}` : "Unknown"
      }</p>
      <p class="review-explanation">Explanation: ${escapeHtml(item.question.explanation || "No explanation was available in the source documents.")}</p>
    `;
    elements.reviewList.appendChild(article);
  });
}

function retryCurrentExam() {
  if (!state.activeExam) {
    return;
  }
  startExam(state.activeExam.id, {
    mode: state.session?.mode || state.review?.summary.mode || getHomeSettings().mode,
    shuffleQuestions: state.session?.shuffleQuestions || false,
    shuffleOptions: state.session?.shuffleOptions || false,
  });
}

function showScreen(name) {
  elements.homeScreen.classList.toggle("active", name === "home");
  elements.examScreen.classList.toggle("active", name === "exam");
  elements.resultScreen.classList.toggle("active", name === "results");
  elements.backHomeButton.classList.toggle("hidden", name === "home");
}

function sessionKey(examId) {
  return `${STORAGE_PREFIX}:session:${examId}`;
}

function resultKey(examId) {
  return `${STORAGE_PREFIX}:result:${examId}`;
}

function persistSession() {
  localStorage.setItem(sessionKey(state.session.examId), JSON.stringify(state.session));
}

function readSession(examId) {
  const raw = localStorage.getItem(sessionKey(examId));
  return raw ? JSON.parse(raw) : null;
}

function clearSession(examId) {
  localStorage.removeItem(sessionKey(examId));
}

function saveLastResult(examId, result) {
  localStorage.setItem(resultKey(examId), JSON.stringify(result));
}

function readLastResult(examId) {
  const raw = localStorage.getItem(resultKey(examId));
  return raw ? JSON.parse(raw) : null;
}

function shuffleArray(items) {
  for (let index = items.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [items[index], items[swapIndex]] = [items[swapIndex], items[index]];
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
