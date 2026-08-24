"use strict";

const REPOSITORY = "nexus-ai-2045/fiction-forks";
const ISSUE_URL = `https://github.com/${REPOSITORY}/issues/new`;
const API_URL = `https://api.github.com/repos/${REPOSITORY}/issues?state=open&labels=idea&per_page=6`;
const ISSUE_PATH_PREFIX = `/${REPOSITORY}/issues/`;

const form = document.querySelector("#idea-form");
const steps = [...document.querySelectorAll("[data-step]")];
const indicators = [...document.querySelectorAll("[data-step-indicator]")];
const summarySteps = [...document.querySelectorAll("[data-summary-step]")];
const nextButton = document.querySelector('[data-action="next"]');
const backButton = document.querySelector('[data-action="back"]');
const formError = document.querySelector("#form-error");
const issuePreview = document.querySelector("#issue-preview");
const issueMarkdown = document.querySelector("#issue-markdown");
const issueLink = document.querySelector("#github-issue-link");
const copyStatus = document.querySelector("#copy-status");
const handoffStatus = document.querySelector("#handoff-status");
const boundaryDialog = document.querySelector("#boundary-dialog");

let currentStep = 1;

function value(name) {
  return form.elements[name]?.value.trim() ?? "";
}

function compact(text, fallback = "未入力") {
  const normalized = text.replace(/\s+/g, " ").trim();
  return normalized || fallback;
}

function trustedIssueUrl(candidate) {
  try {
    const url = new URL(String(candidate));
    if (url.origin !== "https://github.com" || !url.pathname.startsWith(ISSUE_PATH_PREFIX)) {
      return null;
    }
    return url.toString();
  } catch {
    return null;
  }
}

function updateSummary() {
  const work = [value("workTitle"), value("characterName")].filter(Boolean).join(" / ");
  document.querySelector('[data-summary="work"]').textContent = compact(work);
  document.querySelector('[data-summary="function"]').textContent = compact(value("borrowedFunction"));
  document.querySelector('[data-summary="future"]').textContent = compact(value("futureProblem"));
  document.querySelector('[data-summary="conditions"]').textContent = compact(
    [value("requirements"), value("tradeoffs")].filter(Boolean).join(" / "),
  );
}

function setStep(step) {
  currentStep = Math.max(1, Math.min(4, step));
  steps.forEach((section) => {
    const active = Number(section.dataset.step) === currentStep;
    section.hidden = !active;
    section.classList.toggle("is-active", active);
  });
  indicators.forEach((indicator) => {
    const index = Number(indicator.dataset.stepIndicator);
    indicator.classList.toggle("is-current", index === currentStep);
    indicator.classList.toggle("is-complete", index < currentStep);
    if (index === currentStep) indicator.setAttribute("aria-current", "step");
    else indicator.removeAttribute("aria-current");
  });
  summarySteps.forEach((item) => {
    item.classList.toggle("is-current", Number(item.dataset.summaryStep) === currentStep);
  });
  backButton.hidden = currentStep === 1;
  nextButton.firstChild.textContent = currentStep === 4 ? "Issueを確認 " : "次へ ";
  issuePreview.hidden = true;
  formError.textContent = "";
  updateSummary();
  const heading = steps[currentStep - 1].querySelector("h2");
  heading?.focus({ preventScroll: true });
}

function validateCurrentStep() {
  const active = steps[currentStep - 1];
  const required = [...active.querySelectorAll("[required]")];
  let firstInvalid = null;

  required.forEach((field) => {
    const emptyAfterTrim = field.matches('input:not([type="checkbox"]), textarea')
      && field.value.trim().length === 0;
    const invalid = !field.checkValidity() || emptyAfterTrim;
    if (field.matches('input:not([type="checkbox"]), textarea')) {
      field.setAttribute("aria-invalid", String(invalid));
    }
    if (invalid && !firstInvalid) firstInvalid = field;
  });

  if (firstInvalid) {
    formError.textContent = currentStep === 4
      ? "必須項目と権利・安全の確認を完了してください。"
      : "このステップの必須項目を入力してください。";
    firstInvalid.focus();
    return false;
  }
  formError.textContent = "";
  return true;
}

function issueTitle() {
  const work = value("workTitle");
  const capability = compact(value("plainLanguage")).slice(0, 56);
  return `[idea] ${work}から考える：${capability}`;
}

function buildIssueBody() {
  const character = value("characterName") || "（指定なし）";
  return `<!-- fiction-forks-kind: idea -->
## 作品・登場人物

- 作品: ${value("workTitle")}
- 登場人物: ${character}

## 借りたい機能

${value("borrowedFunction")}

### 作品を知らない人向けの同義表現

${value("plainLanguage")}

## 変えたい未来

${value("futureProblem")}

- 特に影響を受ける人・地域: ${value("affectedPeople")}

## 実現条件

${value("requirements")}

## 費用・副作用・失敗条件

${value("tradeoffs")}

## 現在の状態

- [x] アイデア段階（シミュレーション未実行）
- [ ] contributorがworldline PRとして実装
- [ ] 5役のfixture / live runで検証

## 権利・安全

- [x] 作品名・登場人物名と、独自に抽出した抽象機能だけを記載した
- [x] 画像、台詞、音声、映像、ロゴ、外見・口調の再現を含めていない
- [x] 個人情報、秘密情報、実在システムへの攻撃手順を含めていない

---
Fiction Forks Idea Builderで作成。投稿前にGitHub上で編集できます。`;
}

function renderPreview() {
  const body = buildIssueBody();
  issueMarkdown.textContent = `${issueTitle()}\n\n${body}`;
  const url = new URL(ISSUE_URL);
  url.searchParams.set("title", issueTitle());
  url.searchParams.set("body", body);
  url.searchParams.set("labels", "idea");
  issueLink.href = url.toString();
  issuePreview.hidden = false;
  issuePreview.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function copyText(text, statusElement, message) {
  try {
    await navigator.clipboard.writeText(text);
    statusElement.textContent = message;
  } catch {
    statusElement.textContent = "コピーできませんでした。テキストを選択してコピーしてください。";
  }
}

nextButton.addEventListener("click", () => {
  if (!validateCurrentStep()) return;
  if (currentStep < 4) setStep(currentStep + 1);
  else renderPreview();
});

backButton.addEventListener("click", () => setStep(currentStep - 1));

form.addEventListener("input", (event) => {
  if (event.target.matches("[aria-invalid]")) event.target.setAttribute("aria-invalid", "false");
  issuePreview.hidden = true;
  issueMarkdown.textContent = "";
  issueLink.href = "#";
  updateSummary();
});

document.querySelector('[data-action="edit"]').addEventListener("click", () => {
  issuePreview.hidden = true;
  steps[currentStep - 1].querySelector("textarea, input")?.focus();
});

document.querySelector('[data-action="copy-issue"]').addEventListener("click", () => {
  copyText(`${issueTitle()}\n\n${buildIssueBody()}`, copyStatus, "Issue用の文章をコピーしました。GitHub以外でも相談に使えます。");
});

document.querySelector('[data-action="copy-ai-prompt"]').addEventListener("click", () => {
  const prompt = `次の公開Issueから、Fiction Forksの新しいworldlineを実装してください。\n\nIssue URL: （ここにIssue URLを貼る）\nRepository: https://github.com/${REPOSITORY}\n\n書込権限がなければrepositoryをforkし、fork内の専用branchで作業してください。書込権限があれば本repository内の専用branchを使えます。intervention JSON、同じslugのsocial configとfixture、通常比較と遅延比較、テストを作ってください。PR種別はworldlineとし、人間レビュー前で止めてください。`;
  copyText(prompt, handoffStatus, "AIへ渡す依頼文をコピーしました。Issue URLを追加してください。");
});

document.querySelectorAll('[data-action="open-boundary"]').forEach((button) => {
  button.addEventListener("click", () => boundaryDialog.showModal());
});

document.querySelectorAll('[data-action="close-boundary"]').forEach((button) => {
  button.addEventListener("click", () => boundaryDialog.close());
});

async function loadIdeaQueue() {
  const container = document.querySelector("#idea-queue-list");
  try {
    const response = await fetch(API_URL, {
      headers: { Accept: "application/vnd.github+json" },
      referrerPolicy: "no-referrer",
    });
    if (!response.ok) throw new Error(`GitHub API: ${response.status}`);
    const payload = await response.json();
    if (!Array.isArray(payload)) throw new Error("GitHub API response is not an array");
    const issues = payload.filter((item) => item && typeof item === "object" && !item.pull_request);
    container.replaceChildren();
    if (issues.length === 0) {
      const empty = document.createElement("p");
      empty.className = "queue-empty";
      empty.textContent = "最初のアイデアを待っています。上のフォームから参加できます。";
      container.append(empty);
      return;
    }
    issues.forEach((issue) => {
      const href = trustedIssueUrl(issue.html_url);
      if (!href) return;
      const link = document.createElement("a");
      link.className = "queue-item";
      link.href = href;
      link.rel = "noreferrer";

      const number = document.createElement("strong");
      number.textContent = `#${String(issue.number ?? "?")}`;
      const title = document.createElement("b");
      title.textContent = String(issue.title ?? "無題のアイデア");
      const author = document.createElement("span");
      const login = issue.user && typeof issue.user === "object" ? issue.user.login : "unknown";
      author.textContent = `提案者 @${String(login ?? "unknown")}`;

      link.append(number, title, author);
      container.append(link);
    });
  } catch {
    container.replaceChildren();
    const fallback = document.createElement("p");
    fallback.className = "queue-empty";
    fallback.textContent = "現在一覧を取得できません。GitHubのIssue一覧から確認できます。";
    container.append(fallback);
  }
}

setStep(1);
loadIdeaQueue();
