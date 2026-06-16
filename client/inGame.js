 // AI提示按鈕
const hintBtn = document.getElementById('hint-btn');
let gameTarget = "";
// 目前所在的條目標題（例如 "Fruit"）
let currentTitle = "";
let stepCount = 0;


hintBtn.addEventListener('click', async () => {
    if (!currentTitle) {
        alert('請先開始遊戲並進入一個條目，再點擊 AI 提示。');
        return;
    }

    hintBtn.disabled = true;
    try {
        const response = await fetch(`/api/hint?title=${encodeURIComponent(currentTitle)}&target=${encodeURIComponent(gameTarget)}`);
        const data = await response.json();

        if (response.ok && data.success) {
            alert(`AI 提示：\n${data.hint}`);
        } else {
            alert(`AI 提示載入失敗：${data.error || '請稍後再試'}`);
        }
    } catch (err) {
        console.error('AI 提示錯誤:', err);
        alert('無法連線到 AI 提示服務。');
    } finally {
        hintBtn.disabled = false;
    }
});

 let solutionPath = []; // 後端算出的最短路徑 (URL 陣列)

    // inGame.html 初始化
    document.addEventListener("DOMContentLoaded", function() {
        const startTitleFromSession = sessionStorage.getItem("startTitle");
        const targetTitleFromSession = sessionStorage.getItem("targetTitle");
        const solutionPathFromSession = sessionStorage.getItem("solutionPath");

        if (startTitleFromSession && targetTitleFromSession && solutionPathFromSession) {
            // 從 sessionStorage 恢復遊戲狀態
            startTitle = startTitleFromSession;
            targetTitle = targetTitleFromSession;
            currentTitle = startTitle;
            pathHistory = [startTitle];
            solutionPath = JSON.parse(solutionPathFromSession); // 最短路徑

            document.getElementById("targetTitle").innerText = targetTitle;
            document.getElementById("currentTitle").innerText = currentTitle;

            // 淡入效果
            const gameArea = document.querySelector(".game-area");
            gameArea.style.opacity = "0";
            gameArea.style.transition = "opacity 0.6s ease";
            
            setTimeout(() => {
                gameArea.style.opacity = "1";
            }, 50);

            startTimer();
            loadWikiPage(currentTitle);
            renderPath();
            updateBackButton();

        } else {
            // 沒有題目資訊，返回主頁
            alert("遊戲資訊遺失，請重新開始");
            window.location.href = "index.html";
        }
    });

    let seconds = 0;
    let timerId = null;
    // 啟動計時器
    function startTimer() {
        if (timerId) clearInterval(timerId); // 清除舊的計時器
        timerId = setInterval(() => {
            seconds++;
            const timerElement = document.getElementById("timer");
            if (timerElement) {
                timerElement.innerHTML = `${seconds}<small>秒</small>`;
            }
        }, 1000);
    }

    // 載入 Wiki 頁面內容（從後端 API）
    async function loadWikiPage(pageTitle) {
        const wikiContent = document.getElementById("wikiContent");
        wikiContent.innerHTML = `<p>Loading ${pageTitle}...</p>`;

        try {
            const response = await fetch(`/api/wiki/${encodeURIComponent(pageTitle)}`);
            const data = await response.json();

            if (data.success) {
                // 將 HTML 內容放入 DOM
                wikiContent.innerHTML = data.html;
                
                // 為所有 <a> 標籤加事件監聽
                const links = wikiContent.querySelectorAll('a');
                links.forEach(link => {
                    link.addEventListener('click', (e) => handleLinkClick(e, pageTitle));
                });
                
                window.scrollTo(0, 0);
            } else {
                wikiContent.innerHTML = `<h3 style="color: red;">載入失敗：${data.error}</h3>`;
            }
        } catch (err) {
            console.error("Fetch 錯誤:", err);
            wikiContent.innerHTML = '<h3 style="color: red;">連線後端失敗，請檢查 Flask 是否有啟動</h3>';
        }
    }

    // 處理連結點擊事件
    function handleLinkClick(e, currentPageTitle) {
        const link = e.target.closest('a');
        if (!link) return;

        const href = link.getAttribute('href');
        if (!href) return;

        // 正常的條目長這樣：/wiki/Fruit
        // 特殊頁面(不要讓玩家點)長這樣：/wiki/Help:Contents 或 /wiki/File:apple.jpg
        if (href.startsWith('/wiki/') && !href.includes(':')) {
            e.preventDefault(); // 攔截

            const nextTitle = href.split('/wiki/')[1].split('?')[0].split('#')[0];
            const decodedNextTitle = decodeURIComponent(nextTitle).replace(/_/g, ' ');

            // 檢查該連結是否在允許範圍內（檢查是否能到達目標）
            // 簡單方案：只要不是已經走過的頁面，就允許
            if (pathHistory.includes(decodedNextTitle)) {
                alert(`「${decodedNextTitle}」已經走過了，請選擇其他連結`);
                return;
            }

            goToPage(decodedNextTitle);
        } else {
            e.preventDefault();
            console.log("阻擋跳轉非條目連結:", href);
        }
    }

    // 跳轉到新的 Wiki 頁面
    function goToPage(pageTitle) {
        currentTitle = pageTitle;
        stepCount++;
        pathHistory.push(pageTitle);

        document.getElementById("currentTitle").innerText = currentTitle;
        document.getElementById("stepCount").innerText = stepCount;

        renderPath();
        updateProgress();
        updateBackButton();

        // 檢查是否到達目標
        if (currentTitle === targetTitle) {
            finishGame();
        } else {
            // 載入新頁面
            loadWikiPage(currentTitle);
        }
    }

    // 返回上一個頁面
    function goBackPage() {
        if (pathHistory.length <= 1) {
            alert("已經在第一頁了");
            return;
        }

        // 移除當前頁面，回到前一個
        pathHistory.pop();
        currentTitle = pathHistory[pathHistory.length - 1];
        stepCount = pathHistory.length - 1;

        // 更新 UI
        document.getElementById("currentTitle").innerText = currentTitle;
        document.getElementById("stepCount").innerText = stepCount;
        renderPath();
        updateProgress();
        updateBackButton();

        // 載入頁面
        loadWikiPage(currentTitle);
    }

    // 更新返回按鈕顯示狀態
    function updateBackButton() {
        const backBtn = document.getElementById("backBtn");
        if (pathHistory.length <= 1) {
            backBtn.style.display = "none";
        } else {
            backBtn.style.display = "block";
        }
    }

    // 完成遊戲
    function finishGame() {
        clearInterval(timerId);

        const finalSteps = stepCount;
        const finalTime = seconds;
        const optimalSteps = solutionPath.length - 1; // 最短路徑的步數

        alert(`🎉 完成！\n步數: ${finalSteps}\n時間: ${finalTime} 秒\n最短路徑: ${optimalSteps} 步`);

        // 淡出效果後返回主頁
        const gameScreen = document.getElementById("gameScreen");
        if (gameScreen) {
            gameScreen.style.transition = "opacity 0.6s ease";
            gameScreen.style.opacity = "0";
            
            setTimeout(() => {
                window.location.href = "index.html";
            }, 600);
        }
    }

    // 進度條相關函數（來自 app.js）
    function renderPath() {
        const pathList = document.getElementById("pathList");
        pathList.innerHTML = "";

        pathHistory.forEach((page, index) => {
            const li = document.createElement("li");
            li.innerText = `▸ ${page}`;
            if (page === currentTitle) {
                li.classList.add("current");
            }
            pathList.appendChild(li);
        });
    }

    function updateProgress() {
    // 1. 後端傳來的 solutionPath 是 URL 陣列，我們需要把它們轉換成純標題陣列來做比對
    const solutionTitles = solutionPath.map(url => {
        const rawTitle = url.split('/wiki/')[1];
        // 處理編碼與底線，確保格式跟 currentTitle 一致
        return decodeURIComponent(rawTitle).replace(/_/g, ' ');
    });

    // 2. 尋找目前所在的頁面，在正確解答路徑中的哪一個位置
    const currentIndexInSolution = solutionTitles.indexOf(currentTitle);

    let progress = 0;
    
    // 如果 currentIndexInSolution 不是 -1，代表玩家目前走在正確的路徑上
    if (currentIndexInSolution !== -1) {
        // 分母為 總節點數 - 1 (因為起點的進度應該要是 0%)
        // Math.max(1, ...) 是為了防止起點等於終點時發生除以零的錯誤
        const totalSteps = Math.max(1, solutionTitles.length - 1);
        progress = (currentIndexInSolution / totalSteps) * 100;
    } else {
        // 如果目前頁面不在解答路徑中 (偏離軌道)，進度歸 0
        progress = 0;
    }

    // 3. 更新進度條 UI
    document.querySelector(".progress-fill").style.width = progress + "%";
    document.querySelector(".progress-percent").innerText = Math.round(progress) + "%";
}