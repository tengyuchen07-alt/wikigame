import time
import requests
import re
import urllib.parse
import random
from collections import deque
from bs4 import BeautifulSoup

TIMEOUT = 120  # time limit in seconds for the search

session = requests.Session()
session.headers.update({
    "User-Agent": "WikiGameBot/1.0 (contact: sgw223@google.com)"
})

class TimeoutErrorWithLogs(Exception):
    def __init__(self, message, logs, time, discovered):
        super().__init__(message)
        self.logs = logs
        self.time = time
        self.discovered = discovered

def make_url(title, lang="en"):
    """將維基百科條目標題轉換為完整的 URL"""
    encoded_title = urllib.parse.quote(title.replace(" ", "_"))
    return f"https://{lang}.wikipedia.org/wiki/{encoded_title}"

def get_title_from_url(url):
    """從維基百科 URL 中萃取出原本的標題"""
    encoded_title = url.split("/wiki/")[-1].split('#')[0].split('?')[0]
    return urllib.parse.unquote(encoded_title).replace("_", " ")
    
# 新增這個函數：爬蟲也解析 HTML，並套用跟 server.py 一模一樣的過濾邏輯
def get_fwd_links_html(title, lang="en"):
    encoded_title = urllib.parse.quote(title.replace(" ", "_"))
    url = f"https://{lang}.wikipedia.org/wiki/{encoded_title}"
    try:
        res = session.get(url, timeout=5)
        if res.status_code != 200:
            time.sleep(0.5)
            return []
        
        soup = BeautifulSoup(res.content, 'html.parser')
        main_content = soup.find('div', id='mw-content-text')
        if not main_content:
            return []

        # 統一過濾維基百科網頁上的雜訊
        for element in main_content(["script", "style", "sup", "table"]):
            element.decompose()
        for element in main_content.find_all(['div', 'span'], class_=['reflist', 'navbox', 'infobox', 'metadata', 'mw-editsection']):
            element.decompose()
            
        links = []
        for a in main_content.find_all('a', href=True):
            href = a['href']
            # 必須是維基百科條目連結，且排除 Help:, Category: 等特殊空間
            if href.startswith('/wiki/') and ':' not in href:
                
                # 🚨 修正重點：把 # (錨點) 和 ? (查詢參數) 後面的字串通通切掉
                clean_href = href.split('/wiki/')[1].split('#')[0].split('?')[0]
                
                # 解碼並把底線換回空白
                link_title = urllib.parse.unquote(clean_href).replace("_", " ")
                
                # 確保不是空字串，且不重複加入
                if link_title and link_title not in links:
                    links.append(link_title)
        return links
    except Exception as e:
        print(f"HTML Parsing ERROR for {title}: {e}")
        return []

#正向api
def get_fwd_links_api(title, lang="en"):
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "links",
        "titles": title,
        "pllimit": "50",
        "plnamespace": 0,  # 0 代表只抓取一般條目，自動過濾掉 Help: 或 Wikipedia: 等頁面
        "format": "json"
    }
    try:
        res = session.get(url, params=params, timeout=5)
        if res.status_code != 200:
            time.sleep(0.5)
            return []
        data = res.json()
        pages = data.get("query", {}).get("pages", {})
        page_id = list(pages.keys())[0]
        if page_id == "-1":
            return []
        raw_links = pages[page_id].get("links", [])
        return [link["title"] for link in raw_links]
    except Exception as e:
        print(f"API ERROR for {title}: {e}")
        return []

#反向api
def get_bwd_links_api(title, lang="en"):
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "backlinks",
        "bltitle": title,
        "bllimit": "max",
        "blnamespace": 0,  # 0 代表只抓取一般條目，自動過濾掉 Help: 或 Wikipedia: 等頁面
        "format": "json"
    }
    try:
        res = session.get(url, params=params, timeout=5)
        if res.status_code != 200:
            time.sleep(0.5)
            return []
        data = res.json()
        # 修正：反向 API 直接抓 backlinks
        backlinks = data.get("query", {}).get("backlinks", [])
        return [bl["title"] for bl in backlinks]
    except Exception as e:
        print(f"API ERROR for {title}: {e}")
        return []

def generate_puzzle(steps=2, lang="en"):
    print(f"\n🎲 開始產生 {steps} 步的隨機題目...")
    
    while True: # 如果遇到死胡同，就重新產生
        try:
            # 1. 取得隨機起點
            random_url = f"https://{lang}.wikipedia.org/w/api.php"
            random_params = {"action": "query", "list": "random", "rnnamespace": 0, "rnlimit": 1, "format": "json"}
            res = session.get(random_url, params=random_params, timeout=5)
            start_title = res.json()["query"]["random"][0]["title"]
            
            current_title = start_title
            path_taken = [start_title]
            dead_end = False
            
            for i in range(steps):
                # 呼叫你寫好的正向 API 抓取目前頁面的所有連結
                links = get_fwd_links_html(current_title, lang)
                
                # 排除已經走過的節點，避免原地繞圈圈 (例如 A -> B -> A)
                valid_links = [link for link in links if link not in path_taken]
                
                if not valid_links:
                    print(f"⚠️ {current_title} 是一條死胡同，重新尋找起點...")
                    dead_end = True
                    break
                    
                # 從有效的連結中隨機挑選一個往下走
                next_title = random.choice(valid_links)
                path_taken.append(next_title)
                current_title = next_title
                
            # 3. 如果順利走完指定的步數，就回傳結果！
            if not dead_end:
                print(f"✅ 題目產生成功！")
                print(f"🗺️ 電腦的漫步路徑: {' -> '.join(path_taken)}")
                return start_title, current_title
                
        except Exception as e:
            print(f"產生題目時發生錯誤: {e}，正在重試...")
            time.sleep(1)

#bfs
#回傳 path, logs, time, discovered(探索節點數量)
def find_path(start_url, target_url):
    lang = "zh" if "zh.wikipedia" in start_url else "en"
    start_title = get_title_from_url(start_url)
    target_title = get_title_from_url(target_url)

    if start_title == target_title:
        return [make_url(start_title, lang)], ["起點等同於終點!"], 0, 1
    # A->B->C->D
    fwd_queue = deque([start_title]) # [A]
    bwd_queue = deque([target_title]) # [D]

    fwd_visit = {}
    fwd_visit[start_title] = [start_title] # {"A", [A]}
    bwd_visit = {}
    bwd_visit[target_title] = [target_title] #{"D", [D]}

    logs = []
    maxdepth = 3
    start_time = time.time()
    while fwd_queue and bwd_queue:
        pass_time = time.time() - start_time
        if pass_time > TIMEOUT:
            logs.append(f"搜尋超過 {TIMEOUT} 秒, 已停止")
            raise TimeoutErrorWithLogs("Search exceeded time limit.", logs, pass_time, len(bwd_visit) + len(fwd_visit))
        # 正
        cur_fwd = fwd_queue.popleft() # pop [A] 得到 A
        depth_fwd = len(fwd_visit[cur_fwd]) - 1 # 走過路徑-1

        if depth_fwd < maxdepth:
            log_msg = f"[正向] 探索: {cur_fwd} (深度 {depth_fwd})"
            print(log_msg)
            logs.append(log_msg)
            links = get_fwd_links_html(cur_fwd, lang) # links = A 能去的點 e.g. [X,Y,Z]
            for next_title in links:
                #假設next_title = B
                if next_title in bwd_visit:#相遇
                    pass_time = time.time() - start_time
                    fwd_path = fwd_visit[cur_fwd] # ['A','B']
                    bwd_path = bwd_visit[next_title] #['D', 'C']
                    final_path_title = fwd_path + bwd_path[::-1] #['A','B','C','D']
                    final_path_url = []
                    for t in final_path_title:
                        final_path_url.append(make_url(t,lang))
                    
                    logs.append(f"[正]找到相遇點: {next_title}")
                    return final_path_url, logs, pass_time, len(fwd_visit) + len(bwd_visit)
                if next_title not in fwd_visit:
                    fwd_queue.append(next_title)
                    fwd_visit[next_title] = fwd_visit[cur_fwd] + [next_title]
        # 反
        cur_bwd = bwd_queue.popleft()
        depth_bwd = len(bwd_visit[cur_bwd]) - 1

        if depth_bwd < maxdepth:
            log_msg = f"[反向] 探索: {cur_bwd} (深度 {depth_bwd})"
            print(log_msg)
            logs.append(log_msg)
            links = get_bwd_links_api(cur_bwd, lang)
            for prev_title in links:
                if prev_title in fwd_visit:
                    pass_time = time.time() - start_time
                    fwd_path = fwd_visit[prev_title]
                    bwd_path = bwd_visit[cur_bwd]
                    final_path_title = fwd_path + bwd_path[::-1]
                    
                    final_path_url = []
                    for t in final_path_title:
                        final_path_url.append(make_url(t, lang))
                    logs.append(f"[反]找到相遇點: {prev_title}")
                    return final_path_url, logs, pass_time, len(fwd_visit) + len(bwd_visit)
                if prev_title not in bwd_visit:
                    bwd_queue.append(prev_title)
                    bwd_visit[prev_title] = bwd_visit[cur_bwd] + [prev_title]
    pass_time = time.time() - start_time
    logs.append(f"找不到結果")
    print('\n找不到路徑')
    raise TimeoutErrorWithLogs("Path not found.", logs, pass_time, len(fwd_visit) + len(bwd_visit))
