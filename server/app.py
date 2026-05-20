from flask import Flask, send_from_directory, jsonify
from bs4 import BeautifulSoup
import urllib.parse
import crawler

app = Flask(__name__, static_folder = '../client', static_url_path = '/static')


@app.route('/', methods = ['GET'])
def home():
    return send_from_directory(app.static_folder , 'index.html')

@app.route('/find_path', methods=['Get', 'POST'])
def find_path():
    start_title = ""
    target_title = ""
    try:
        start_title, target_title = crawler.generate_puzzle(steps= 3, lang= "en")
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


@app.route('/api/wiki/<title>')
def get_wiki_content(title):
    try:
        encoded_title = urllib.parse.quote(title) #處理中文編碼問題
        url = f"https://en.wikipedia.org/wiki/{encoded_title}"
        res = crawler.session.get(url, timeout=5)

        soup = BeautifulSoup(res.content, 'html.parser')
        # with open('wiki_text.txt', "w", encoding="utf-8") as f:
        #     f.write(soup.prettify())


        main_content = soup.find('div', id='mw-content-text')

        if not main_content:
            return jsonify({
                'success': False,
                'error': '找不到內文區塊'
            }), 404
        
        #修復圖片破圖
        for img in main_content.find_all('img'):
            if img.has_attr('src'):
                if img['src'].startswith('//'):
                    img['src'] = 'https:' + img['src']
                elif img['src'].startswith('/'):
                    img['src'] = 'https://en.wikipedia.org' + img['src']

        return jsonify({
            'success': True,
            'html': str(main_content)
        });
    

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, threaded=True)
