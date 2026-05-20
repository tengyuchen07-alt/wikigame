// const startInput = document.getElementById('start-input');
// const loadBtn = document.getElementById('load-btn');
const randomBtn = document.getElementById('random-btn');
const gamestatus = document.getElementById('game-status');
const wikiContainer = document.getElementById('wiki-container');
const currentStatus = document.getElementById('current-status');

let gameTarget = "";
let stepCount = 0;

//載入wiki
async function loadWikiPage(title) {
    const decoded_title = decodeURIComponent(title).replace(/_/g, ' ');
    currentStatus.innerText = `目前位置: ${decoded_title}`;
    wikiContainer.innerHTML = `<h3>loading ${decoded_title}...</h3>`;



    try{
        const response = await fetch(`/api/wiki/${encodeURIComponent(title)}`);
        const data = await response.json();
        
        if(data.success){
            wikiContainer.innerHTML = data.html;
            window.scrollTo(0, 0);

            if(gameTarget){
                const current = decoded_title.toLowerCase().trim();
                const target = gameTarget.toLowerCase().trim();

                if(current == target){
                    console.log('抵達終點');
                    setTimeout(() => {
                        gamestatus.innerText = `破關, 總共花了 ${stepCount} 步！`;
                        alert(`你成功走到「${decoded_title}」了！\n總共花了 ${stepCount} 步！`);
                    }, 300); // 0.3s
                  
                }
            }
        }
        else{
            wikiContainer.innerHTML = `<h3 style="color: red;">載入失敗：${data.error}</h3>`;
        }
    } catch (err){
        console.error("Fetch 錯誤:", err);
        wikiContainer.innerHTML = '<h3 style="color: red;">連線後端失敗，請檢查 Flask 是否有啟動</h3>';
    }
    
}

randomBtn.addEventListener('click', async()=>{
    randomBtn.disabled = true;
    gamestatus.innerText = "找路徑中...";
    wikiContainer.innerHTML = "";

    try{
        const response = await fetch('/find_path');
        const data = await response.json();

        if(response.ok && data.start_title){
            gameTarget = data.target_title;//目標
            stepCount = 0;
            gamestatus.innerText = `請走到 ${data.target_title.replace(/_/g, ' ')}`;
            gamestatus.style.color = "#e74c3c";
            
            
            // sessionStorage.setItem('gamePath', JSON.stringify(data.path));

            const solutionPath = data.path;
            const readablePath = solutionPath.map(url => {
                return decodeURIComponent(url.split('/').pop()).replace(/_/g, ' ');
            }).join(' ➔ ');


            // 把文字塞進我們剛剛在 HTML 做的 span 裡
            document.getElementById('solution-path').innerText = readablePath;
            // 讓整個解答區塊顯示出來
            document.getElementById('debug').style.display = 'block';


            loadWikiPage(data.start_title);
        }
        else{
            gamestatus.innerText = `出題失敗: ${data.error}`;
        }
    } catch (err) {
        console.error("連線錯誤", err);
        gamestatus.innerText = "無法連線到伺服器";
    } finally {
        randomBtn.disabled = false;
    }
    
});
// loadBtn.addEventListener('click', async()=>{
//     const title = startInput.value.trim();
//     if(title){
//         loadWikiPage(title);
//     }
// });

wikiContainer.addEventListener('click', function(event){
    const anchor = event.target.closest('a');
    if(!anchor)return;

    const href = anchor.getAttribute('href');
    if(!href)return;


    // 正常的條目長這樣：/wiki/Fruit
    // 特殊頁面(不要讓玩家點)長這樣：/wiki/Help:Contents 或 /wiki/File:apple.jpg
    if(href.startsWith('/wiki/') && !href.includes(':')){
        event.preventDefault(); //攔截
        const nextTitle = href.split('/wiki/')[1];
        
        stepCount+=1;
        loadWikiPage(nextTitle);
        
    }
    else{
        event.preventDefault();
        console.log("阻擋跳轉非連結:", href);
    }
});




// const box = document.getElementById('box');
// box.innerHTML = '<h1>test</h1>';