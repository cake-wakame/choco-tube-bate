import os
import json
import requests
import urllib.parse
import concurrent.futures
from flask import Flask, render_template, request, jsonify, Response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')

EDU_VIDEO_API = "https://siawaseok.duckdns.org/api/video2/"
STREAM_API = "https://ytdl-0et1.onrender.com/stream/"
M3U8_API = "https://ytdl-0et1.onrender.com/m3u8/"
SHORT_STREAM_API = "https://yt-dl-kappa.vercel.app/short/"

INVIDIOUS_INSTANCES = [
    'https://inv.nadeko.net/',
    'https://invidious.f5.si/',
    'https://invidious.lunivers.trade/',
    'https://invidious.ducks.party/',
    'https://super8.absturztau.be/',
    'https://invidious.nikkosphere.com/',
    'https://yt.omada.cafe/',
    'https://iv.melmac.space/',
    'https://iv.duti.dev/',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def safe_request(url, timeout=(3, 8)):
    try:
        res = requests.get(url, headers=HEADERS, timeout=timeout)
        res.raise_for_status()
        return res.json()
    except:
        return None

def get_youtube_search(query, max_results=20):
    if not YOUTUBE_API_KEY:
        return invidious_search(query)
    
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&q={urllib.parse.quote(query)}&maxResults={max_results}&key={YOUTUBE_API_KEY}"
    
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        results = []
        for item in data.get('items', []):
            snippet = item.get('snippet', {})
            results.append({
                'type': 'video',
                'id': item.get('id', {}).get('videoId', ''),
                'title': snippet.get('title', ''),
                'author': snippet.get('channelTitle', ''),
                'channel_id': snippet.get('channelId', ''),
                'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                'published': snippet.get('publishedAt', ''),
                'description': snippet.get('description', '')
            })
        return results
    except Exception as e:
        print(f"YouTube API error: {e}")
        return invidious_search(query)

def invidious_search(query, page=1):
    path = f"/api/v1/search?q={urllib.parse.quote(query)}&page={page}&hl=jp"
    
    for instance in INVIDIOUS_INSTANCES:
        try:
            res = requests.get(instance + path, headers=HEADERS, timeout=(3, 8))
            if res.status_code == 200:
                data = res.json()
                results = []
                for item in data:
                    if item.get('type') == 'video':
                        results.append({
                            'type': 'video',
                            'id': item.get('videoId', ''),
                            'title': item.get('title', ''),
                            'author': item.get('author', ''),
                            'channel_id': item.get('authorId', ''),
                            'thumbnail': f"https://i.ytimg.com/vi/{item.get('videoId', '')}/hqdefault.jpg",
                            'published': item.get('publishedText', ''),
                            'views': item.get('viewCountText', ''),
                            'duration': item.get('lengthSeconds', 0)
                        })
                return results
        except:
            continue
    return []

def get_video_info(video_id):
    try:
        res = requests.get(f"{EDU_VIDEO_API}{video_id}", headers=HEADERS, timeout=(3, 10))
        res.raise_for_status()
        data = res.json()
        
        related_videos = []
        for item in data.get('related', [])[:20]:
            related_videos.append({
                'id': item.get('videoId', ''),
                'title': item.get('title', ''),
                'author': item.get('channel', ''),
                'views': item.get('views', ''),
                'thumbnail': f"https://i.ytimg.com/vi/{item.get('videoId', '')}/mqdefault.jpg"
            })
        
        return {
            'title': data.get('title', ''),
            'description': data.get('description', {}).get('formatted', ''),
            'author': data.get('author', {}).get('name', ''),
            'author_id': data.get('author', {}).get('id', ''),
            'author_thumbnail': data.get('author', {}).get('thumbnail', ''),
            'views': data.get('views', ''),
            'likes': data.get('likes', ''),
            'subscribers': data.get('author', {}).get('subscribers', ''),
            'published': data.get('relativeDate', ''),
            'related': related_videos
        }
    except Exception as e:
        print(f"Video info error: {e}")
        return None

def get_stream_url(video_id):
    urls = {
        'primary': None,
        'fallback': None,
        'm3u8': None,
        'embed': f"https://www.youtube-nocookie.com/embed/{video_id}?autoplay=1"
    }
    
    try:
        res = requests.get(f"{STREAM_API}{video_id}", headers=HEADERS, timeout=(5, 10))
        if res.status_code == 200:
            data = res.json()
            formats = data.get('formats', [])
            
            for fmt in formats:
                if fmt.get('itag') == '18':
                    urls['primary'] = fmt.get('url')
                    break
            
            if not urls['primary']:
                for fmt in formats:
                    if fmt.get('url') and fmt.get('vcodec') != 'none':
                        urls['fallback'] = fmt.get('url')
                        break
    except:
        pass
    
    try:
        res = requests.get(f"{M3U8_API}{video_id}", headers=HEADERS, timeout=(5, 10))
        if res.status_code == 200:
            data = res.json()
            m3u8_formats = data.get('m3u8_formats', [])
            if m3u8_formats:
                best = max(m3u8_formats, key=lambda x: int(x.get('resolution', '0x0').split('x')[-1] or 0))
                urls['m3u8'] = best.get('url')
    except:
        pass
    
    return urls

def get_comments(video_id):
    for instance in INVIDIOUS_INSTANCES:
        try:
            res = requests.get(f"{instance}api/v1/comments/{video_id}", headers=HEADERS, timeout=(3, 8))
            if res.status_code == 200:
                data = res.json()
                comments = []
                for item in data.get('comments', []):
                    comments.append({
                        'author': item.get('author', ''),
                        'author_thumbnail': item.get('authorThumbnails', [{}])[-1].get('url', ''),
                        'content': item.get('contentHtml', '').replace('\n', '<br>'),
                        'likes': item.get('likeCount', 0),
                        'published': item.get('publishedText', '')
                    })
                return comments
        except:
            continue
    return []

def get_trending():
    fast_instances = ['https://inv.nadeko.net/']
    
    for instance in fast_instances:
        try:
            res = requests.get(f"{instance}api/v1/popular", headers=HEADERS, timeout=(2, 5))
            if res.status_code == 200 and res.text.strip().startswith('['):
                data = res.json()
                results = []
                for item in data[:24]:
                    if item.get('type') in ['video', 'shortVideo']:
                        results.append({
                            'type': 'video',
                            'id': item.get('videoId', ''),
                            'title': item.get('title', ''),
                            'author': item.get('author', ''),
                            'thumbnail': f"https://i.ytimg.com/vi/{item.get('videoId', '')}/hqdefault.jpg",
                            'published': item.get('publishedText', ''),
                            'views': item.get('viewCountText', '')
                        })
                if results:
                    return results
        except Exception as e:
            print(f"Popular API error: {e}")
            continue
    
    default_videos = [
        {'type': 'video', 'id': 'dQw4w9WgXcQ', 'title': 'Rick Astley - Never Gonna Give You Up', 'author': 'Rick Astley', 'thumbnail': 'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg', 'published': '', 'views': '17億 回視聴'},
        {'type': 'video', 'id': 'kJQP7kiw5Fk', 'title': 'Luis Fonsi - Despacito ft. Daddy Yankee', 'author': 'Luis Fonsi', 'thumbnail': 'https://i.ytimg.com/vi/kJQP7kiw5Fk/hqdefault.jpg', 'published': '', 'views': '80億 回視聴'},
        {'type': 'video', 'id': 'JGwWNGJdvx8', 'title': 'Ed Sheeran - Shape of You', 'author': 'Ed Sheeran', 'thumbnail': 'https://i.ytimg.com/vi/JGwWNGJdvx8/hqdefault.jpg', 'published': '', 'views': '64億 回視聴'},
        {'type': 'video', 'id': 'RgKAFK5djSk', 'title': 'Wiz Khalifa - See You Again ft. Charlie Puth', 'author': 'Wiz Khalifa', 'thumbnail': 'https://i.ytimg.com/vi/RgKAFK5djSk/hqdefault.jpg', 'published': '', 'views': '60億 回視聴'},
        {'type': 'video', 'id': 'OPf0YbXqDm0', 'title': 'Mark Ronson - Uptown Funk ft. Bruno Mars', 'author': 'Mark Ronson', 'thumbnail': 'https://i.ytimg.com/vi/OPf0YbXqDm0/hqdefault.jpg', 'published': '', 'views': '50億 回視聴'},
        {'type': 'video', 'id': 'lp-EO5I60KA', 'title': 'PPAP (Pen Pineapple Apple Pen)', 'author': 'Pikotaro', 'thumbnail': 'https://i.ytimg.com/vi/lp-EO5I60KA/hqdefault.jpg', 'published': '', 'views': '4億 回視聴'},
        {'type': 'video', 'id': '9bZkp7q19f0', 'title': 'PSY - Gangnam Style', 'author': 'PSY', 'thumbnail': 'https://i.ytimg.com/vi/9bZkp7q19f0/hqdefault.jpg', 'published': '', 'views': '50億 回視聴'},
        {'type': 'video', 'id': 'XqZsoesa55w', 'title': 'Baby Shark Dance', 'author': 'Pinkfong', 'thumbnail': 'https://i.ytimg.com/vi/XqZsoesa55w/hqdefault.jpg', 'published': '', 'views': '150億 回視聴'},
        {'type': 'video', 'id': 'fJ9rUzIMcZQ', 'title': 'Queen - Bohemian Rhapsody', 'author': 'Queen Official', 'thumbnail': 'https://i.ytimg.com/vi/fJ9rUzIMcZQ/hqdefault.jpg', 'published': '', 'views': '16億 回視聴'},
        {'type': 'video', 'id': 'CevxZvSJLk8', 'title': 'Katy Perry - Roar', 'author': 'Katy Perry', 'thumbnail': 'https://i.ytimg.com/vi/CevxZvSJLk8/hqdefault.jpg', 'published': '', 'views': '40億 回視聴'},
        {'type': 'video', 'id': 'YQHsXMglC9A', 'title': 'Adele - Hello', 'author': 'Adele', 'thumbnail': 'https://i.ytimg.com/vi/YQHsXMglC9A/hqdefault.jpg', 'published': '', 'views': '33億 回視聴'},
        {'type': 'video', 'id': 'hT_nvWreIhg', 'title': 'OneRepublic - Counting Stars', 'author': 'OneRepublic', 'thumbnail': 'https://i.ytimg.com/vi/hT_nvWreIhg/hqdefault.jpg', 'published': '', 'views': '40億 回視聴'},
    ]
    return default_videos

@app.route('/')
def index():
    trending = get_trending()
    return render_template('index.html', videos=trending)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return render_template('search.html', videos=[], query='')
    
    results = get_youtube_search(query)
    return render_template('search.html', videos=results, query=query)

@app.route('/watch/<video_id>')
def watch(video_id):
    video_info = get_video_info(video_id)
    stream_urls = get_stream_url(video_id)
    comments = get_comments(video_id)
    
    return render_template('watch.html', 
                         video_id=video_id,
                         video=video_info,
                         streams=stream_urls,
                         comments=comments)

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'Query required'}), 400
    
    results = get_youtube_search(query)
    return jsonify(results)

@app.route('/api/video/<video_id>')
def api_video(video_id):
    info = get_video_info(video_id)
    streams = get_stream_url(video_id)
    return jsonify({'info': info, 'streams': streams})

@app.route('/api/comments/<video_id>')
def api_comments(video_id):
    comments = get_comments(video_id)
    return jsonify(comments)

@app.route('/api/trending')
def api_trending():
    videos = get_trending()
    return jsonify(videos)

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
