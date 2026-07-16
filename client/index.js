const startButton = document.querySelector("#start-button");
const statusElement = document.querySelector("#start-status");

startButton.addEventListener("click", async () => {
  startButton.disabled = true;
  statusElement.textContent = "正在從 Wikipedia 產生題目…";

  try {
    const response = await fetch("/find_path");
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "無法產生題目");
    }

    sessionStorage.setItem(
      "wikiGame",
      JSON.stringify({
        startTitle: data.start_title,
        targetTitle: data.target_title,
        solutionPath: data.path,
        startedAt: Date.now(),
      }),
    );
    window.location.assign("inGame.html");
  } catch (error) {
    console.error(error);
    statusElement.textContent = "題目產生失敗，請稍後再試。";
    startButton.disabled = false;
  }
});
