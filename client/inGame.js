const storedGame = sessionStorage.getItem("wikiGame");
if (!storedGame) {
  window.location.replace("index.html");
  throw new Error("Missing game state");
}

const game = JSON.parse(storedGame);
const solutionTitles = game.solutionPath.map(titleFromUrl);
const history = [game.startTitle];
let currentTitle = game.startTitle;
let elapsedSeconds = Math.max(0, Math.floor((Date.now() - game.startedAt) / 1000));

const elements = {
  article: document.querySelector("#wiki-content"),
  articleStatus: document.querySelector("#article-status"),
  backButton: document.querySelector("#back-button"),
  currentTitle: document.querySelector("#current-title"),
  hintButton: document.querySelector("#hint-button"),
  hintText: document.querySelector("#hint-text"),
  pathList: document.querySelector("#path-list"),
  resultDialog: document.querySelector("#result-dialog"),
  resultSummary: document.querySelector("#result-summary"),
  stepCount: document.querySelector("#step-count"),
  targetTitle: document.querySelector("#target-title"),
  timer: document.querySelector("#timer"),
};

elements.targetTitle.textContent = game.targetTitle;
elements.backButton.addEventListener("click", goBack);
elements.hintButton.addEventListener("click", showHint);

const timerId = window.setInterval(() => {
  elapsedSeconds += 1;
  elements.timer.textContent = elapsedSeconds;
}, 1000);

renderState();
loadArticle(currentTitle);

function titleFromUrl(url) {
  const encoded = new URL(url).pathname.split("/wiki/")[1] || "";
  return decodeURIComponent(encoded).replaceAll("_", " ");
}

async function loadArticle(title) {
  elements.article.replaceChildren();
  elements.articleStatus.hidden = false;
  elements.articleStatus.textContent = `正在載入 ${title}…`;

  try {
    const response = await fetch(`/api/wiki/${encodeURIComponent(title)}`);
    const data = await response.json();
    if (!response.ok || !data.success) {
      throw new Error(data.error || "文章載入失敗");
    }

    elements.article.innerHTML = data.html;
    elements.article.querySelectorAll("a[href]").forEach((link) => {
      link.addEventListener("click", handleArticleLink);
    });
    elements.articleStatus.hidden = true;
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (error) {
    console.error(error);
    elements.articleStatus.textContent = "文章載入失敗，請返回上一頁或重新開始。";
  }
}

function handleArticleLink(event) {
  const href = event.currentTarget.getAttribute("href");
  if (!href?.startsWith("/wiki/") || href.slice(6).includes(":")) {
    return;
  }

  event.preventDefault();
  const nextTitle = decodeURIComponent(href.slice(6).split(/[?#]/)[0]).replaceAll("_", " ");
  if (!nextTitle || history.includes(nextTitle)) {
    elements.hintText.textContent = "這篇文章已經走過了，換一條路試試看。";
    return;
  }

  currentTitle = nextTitle;
  history.push(nextTitle);
  elements.hintText.textContent = "";
  renderState();

  if (currentTitle === game.targetTitle) {
    finishGame();
  } else {
    loadArticle(currentTitle);
  }
}

function goBack() {
  if (history.length <= 1) return;
  history.pop();
  currentTitle = history.at(-1);
  elements.hintText.textContent = "";
  renderState();
  loadArticle(currentTitle);
}

async function showHint() {
  const index = solutionTitles.indexOf(currentTitle);
  const nextTitle = index >= 0 ? solutionTitles[index + 1] || "" : "";
  elements.hintButton.disabled = true;

  try {
    const query = new URLSearchParams({
      title: currentTitle,
      target: game.targetTitle,
      next: nextTitle,
    });
    const response = await fetch(`/api/hint?${query}`);
    const data = await response.json();
    elements.hintText.textContent = data.hint || data.error || "目前沒有提示。";
  } catch (error) {
    console.error(error);
    elements.hintText.textContent = "提示暫時無法使用。";
  } finally {
    elements.hintButton.disabled = false;
  }
}

function renderState() {
  elements.currentTitle.textContent = currentTitle;
  elements.stepCount.textContent = history.length - 1;
  elements.timer.textContent = elapsedSeconds;
  elements.backButton.disabled = history.length <= 1;
  elements.pathList.replaceChildren(
    ...history.map((title) => {
      const item = document.createElement("li");
      item.textContent = title;
      if (title === currentTitle) item.setAttribute("aria-current", "step");
      return item;
    }),
  );
}

function finishGame() {
  window.clearInterval(timerId);
  elements.resultSummary.textContent = `你用了 ${history.length - 1} 步、${elapsedSeconds} 秒完成。`;
  elements.resultDialog.showModal();
  sessionStorage.removeItem("wikiGame");
}
