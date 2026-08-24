"use strict";

const REPOSITORY = "nexus-ai-2045/fiction-forks";
const ISSUE_URL = `https://github.com/${REPOSITORY}/issues/new`;
const API_URL = `https://api.github.com/repos/${REPOSITORY}/issues?state=all&labels=idea&sort=created&direction=desc&per_page=100`;
const ISSUE_PATH_PREFIX = `/${REPOSITORY}/issues/`;

const form = document.querySelector("#idea-form");
const nextButton = document.querySelector('[data-action="next"]');
const formError = document.querySelector("#form-error");
const issuePreview = document.querySelector("#issue-preview");
const issueMarkdown = document.querySelector("#issue-markdown");
const issueLink = document.querySelector("#github-issue-link");
const copyStatus = document.querySelector("#copy-status");
const handoffStatus = document.querySelector("#handoff-status");
const ideaQueueStatus = document.querySelector("#idea-queue-status");
const boundaryDialog = document.querySelector("#boundary-dialog");

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

function worldlinePrompt(issueUrl = "（ここにIssue URLを貼る）") {
  return `このIdea Issueを、Fiction Forksの新しいworldline PRにしてください。\n\nIssue URL: ${issueUrl}\nRepository: https://github.com/${REPOSITORY}\n\n書込権限がなければrepoをforkし、fork内の専用branchで作業してください。書込権限があれば本repo内の専用branchを使ってください。介入JSON、同じslugのsocial configとfixture、同一seedの通常比較と遅延比較、テストを作り、PR種別をworldlineにしてください。fixtureをlive LLM実測と表現せず、権利・安全境界を保ち、人間レビュー前で止めてください。`;
}

function issueExcerpt(body) {
  const source = String(body ?? "");
  const match = source.match(/## (?:アイデア|借りたい機能)\s+([\s\S]*?)(?=\n## |\n### |$)/);
  return compact(match?.[1] ?? "", "詳しい内容はIssueで確認できます。").slice(0, 150);
}

function updateSummary() {
  document.querySelector('[data-summary="work"]').textContent = compact(value("workTitle"));
  document.querySelector('[data-summary="idea"]').textContent = compact(value("ideaText"));
}

function validateForm() {
  const required = [...form.querySelectorAll("[required]")];
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
    formError.textContent = "作品、アイデア、権利・安全の確認を完了してください。";
    firstInvalid.focus();
    return false;
  }
  formError.textContent = "";
  return true;
}

function issueTitle() {
  const work = value("workTitle");
  const idea = compact(value("ideaText")).slice(0, 56);
  return `[idea] ${work}から考える：${idea}`;
}

function buildIssueBody() {
  return `<!-- fiction-forks-kind: idea -->
## 作品

${value("workTitle")}

## アイデア

${value("ideaText")}

## 現在の状態

- [x] アイデア段階（シミュレーション未実行）
- [ ] contributorがworldline PRとして実装
- [ ] 5役のfixture / live runで検証

## worldline PRで検討すること

- [ ] 作品を知らない人向けの同義表現
- [ ] 変えたい未来課題と影響を受ける人・地域
- [ ] 実現に必要な技術・制度・運用
- [ ] 費用・副作用・悪用や失敗の可能性

## 権利・安全

- [x] 作品名と、独自に考えたアイデアだけを記載した
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
  if (!validateForm()) return;
  renderPreview();
});

form.addEventListener("input", (event) => {
  if (event.target.matches("[aria-invalid]")) event.target.setAttribute("aria-invalid", "false");
  issuePreview.hidden = true;
  issueMarkdown.textContent = "";
  issueLink.href = "#";
  updateSummary();
});

document.querySelector('[data-action="edit"]').addEventListener("click", () => {
  issuePreview.hidden = true;
  form.querySelector("textarea, input")?.focus();
});

document.querySelector('[data-action="copy-issue"]').addEventListener("click", () => {
  copyText(`${issueTitle()}\n\n${buildIssueBody()}`, copyStatus, "Issue用の文章をコピーしました。GitHub以外でも相談に使えます。");
});

document.querySelector('[data-action="copy-ai-prompt"]').addEventListener("click", () => {
  copyText(worldlinePrompt(), handoffStatus, "AI用の依頼文をコピーしました。あとはIssue URLを貼るだけです。");
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
      const article = document.createElement("article");
      article.className = "queue-item";

      const meta = document.createElement("div");
      meta.className = "queue-item-meta";

      const number = document.createElement("strong");
      number.textContent = `#${String(issue.number ?? "?")}`;
      const state = document.createElement("span");
      const isOpen = issue.state === "open";
      state.className = `idea-state${isOpen ? "" : " is-closed"}`;
      state.textContent = isOpen ? "OPEN" : "CLOSED";
      meta.append(number, state);

      const title = document.createElement("h4");
      title.textContent = String(issue.title ?? "無題のアイデア");
      const excerpt = document.createElement("p");
      excerpt.textContent = issueExcerpt(issue.body);
      const author = document.createElement("span");
      author.className = "queue-author";
      const login = issue.user && typeof issue.user === "object" ? issue.user.login : "unknown";
      author.textContent = `提案者 @${String(login ?? "unknown")}`;

      const actions = document.createElement("div");
      actions.className = "queue-actions";
      const issueAnchor = document.createElement("a");
      issueAnchor.href = href;
      issueAnchor.rel = "noreferrer";
      issueAnchor.textContent = "Issueを見る";
      const copyButton = document.createElement("button");
      copyButton.type = "button";
      copyButton.dataset.action = "copy-idea-prompt";
      copyButton.dataset.issueUrl = href;
      copyButton.textContent = "AIにworldline PR化を頼む";
      actions.append(issueAnchor, copyButton);

      article.append(meta, title, excerpt, author, actions);
      container.append(article);
    });
    ideaQueueStatus.textContent = "公開GitHubのIdea Issueから最新状態を表示しています。";
  } catch {
    ideaQueueStatus.textContent = "GitHubから更新できないため、HTMLに保存した一覧を表示しています。";
  }
}

document.querySelector("#idea-queue-list").addEventListener("click", (event) => {
  const button = event.target.closest('[data-action="copy-idea-prompt"]');
  if (!button) return;
  const href = trustedIssueUrl(button.dataset.issueUrl);
  if (!href) {
    ideaQueueStatus.textContent = "Issue URLを確認できませんでした。GitHubでIssueを開いてください。";
    return;
  }
  copyText(
    worldlinePrompt(href),
    ideaQueueStatus,
    "Issue URL入りのAI用依頼文をコピーしました。そのままAIへ渡せます。",
  );
});

updateSummary();
loadIdeaQueue();
