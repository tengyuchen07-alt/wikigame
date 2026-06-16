from flask import Flask, send_from_directory, jsonify, request
from bs4 import BeautifulSoup
import urllib.parse
import requests
import crawler
import os
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__, static_folder = '../client', static_url_path = '')


def clean_noise(main_content):
    """統一過濾維基百科網頁上的雜訊，確保爬蟲與玩家看到的畫面一致"""
    # 1. 移除腳本、樣式、上標(參考文獻[1][2]等)、表格(包含右側的 Infobox)
    for element in main_content(["script", "style", "sup", "table"]):
        element.decompose()
    
    # 2. 移除維基百科常見的底部導覽列 (navbox)、參考文獻區塊 (reflist) 與編輯按鈕
    for element in main_content.find_all(['div', 'span'], class_=['reflist', 'navbox', 'infobox', 'metadata', 'mw-editsection']):
        element.decompose()
        
    return main_content

# ---------------------------------------------------------
# 修改 1：將 extract_article_text 替換成使用 clean_noise
def extract_article_text(title):
    encoded_title = urllib.parse.quote(title)
    url = f"https://en.wikipedia.org/wiki/{encoded_title}"
    res = crawler.session.get(url, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.content, 'html.parser')

    main_content = soup.find('div', id='mw-content-text')
    if not main_content:
        return ""

    # 套用統一過濾器
    main_content = clean_noise(main_content)

    text = ' '.join(main_content.get_text(" ", strip=True).split())
    return text[:3000]
#從維基百科頁面提取純文本內容，並限制在3000字以內

def extract_article_text(title):
    encoded_title = urllib.parse.quote(title)
    url = f"https://en.wikipedia.org/wiki/{encoded_title}"
    res = crawler.session.get(url, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.content, 'html.parser')

    main_content = soup.find('div', id='mw-content-text')
    if not main_content:
        return ""

    for element in main_content(["script", "style", "sup", "table"]):
        element.decompose()

    text = ' '.join(main_content.get_text(" ", strip=True).split())
    return text[:3000]


def get_gemini_hint(current_title, target_title, article_text):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return "目前未設定 GEMINI_API_KEY，無法呼叫 AI 提示。"

    prompt = (
        "你是維基闖關遊戲的提示助理。"
        f"目前頁面：{current_title}。目標頁面：{target_title}。"
        "請只給玩家一段中文提示，幫助他思考下一步，但不要直接告訴答案；"
        "提示要簡短、清楚、且適合遊戲中使用。"
        f"文章內容摘要：{article_text[:2000]}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }

    response = requests.post(url, json=payload, timeout=40)
    response.raise_for_status()
    data = response.json()
    return data['candidates'][0]['content']['parts'][0]['text'].strip()


@app.route('/', methods = ['GET'])
def home():
    return send_from_directory(app.static_folder , 'index.html')

@app.route('/find_path', methods=['Get', 'POST'])
def find_path():
    start_title = ""
    target_title = ""
    try:
        start_title, target_title = crawler.generate_puzzle(steps= 2, lang= "en")
        start_url = crawler.make_url(start_title, "en")
        target_url = crawler.make_url(target_title, "en")
 
        path, logs, time, discovered = crawler.find_path(start_url, target_url)
        elapsed_time = logs[-1]
        return jsonify({
            'start_title': start_title,
            'target_title': target_title,
            'start_url': start_url,
            'target_url': target_url,
            'path': path, 
            'logs': logs, 
            'time': elapsed_time, 
            'discovered': discovered
        })
    except crawler.TimeoutErrorWithLogs as e:
        app.logger.error(f"Error occurred: {e}")
        return jsonify({
            'error': str(e), 
            'start_title': start_title,
            'target_title': target_title,
            'logs': e.logs, 
            'time': e.time, 
            'discovered': e.discovered
        }), 408
    except Exception as e:
        app.logger.error(f"Error occurred: {e}")
        return jsonify({'error': 'An error occurred while finding path', 'logs': logs, 'time': time, 'discovered': discovered}), 500

# 提示 API，接受目前題目標題和目標標題，返回一段提示文字


@app.route('/api/hint')
def get_hint():
    try:
        current_title = request.args.get('title', '').strip()
        target_title = request.args.get('target', '').strip()

        if not current_title:
            return jsonify({'success': False, 'error': '缺少目前題目標題'}), 400

        article_text = extract_article_text(current_title)
        hint = get_gemini_hint(current_title, target_title or '未知目標', article_text)

        return jsonify({
            'success': True,
            'hint': hint,
            'title': current_title,
            'target': target_title
        })
    except Exception as e:
        app.logger.error(f"Hint error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/api/wiki/<title>')
def get_wiki_content(title):
    try:
        encoded_title = urllib.parse.quote(title)
        url = f"https://en.wikipedia.org/wiki/{encoded_title}"
        res = crawler.session.get(url, timeout=5)

        soup = BeautifulSoup(res.content, 'html.parser')
        main_content = soup.find('div', id='mw-content-text')

        if not main_content:
            return jsonify({'success': False, 'error': '找不到內文區塊'}), 404
        
        # 套用統一過濾器，確保玩家畫面上不會出現雜訊連結
        main_content = clean_noise(main_content)
        
        # 修復圖片破圖
        for img in main_content.find_all('img'):
            if img.has_attr('src'):
                if img['src'].startswith('//'):
                    img['src'] = 'https:' + img['src']
                elif img['src'].startswith('/'):
                    img['src'] = 'https://en.wikipedia.org' + img['src']

        return jsonify({'success': True, 'html': str(main_content)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, threaded=True, debug=True)
