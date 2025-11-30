import os
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib.parse
import datetime
import random
import time
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')

EDU_VIDEO_API = "https://siawaseok.duckdns.org/api/video2/"
EDU_CONFIG_URL = "https://raw.githubusercontent.com/siawaseok3/wakame/master/video_config.json"
STREAM_API = "https://ytdl-0et1.onrender.com/stream/"
M3U8_API = "https://ytdl-0et1.onrender.com/m3u8/"

_edu_params_cache = {'params': None, 'timestamp': 0}
_trending_cache = {'data': None, 'timestamp': 0}
_thumbnail_cache = {}

session = requests.Session()
retry_strategy = Retry(total=2, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=20, pool_maxsize=20)
session.mount("http://", adapter)
session.mount("https://", adapter)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0',
]

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

def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS)
    }

def get_edu_params():
    cache_duration = 300
    current_time = time.time()

    if _edu_params_cache['params'] and (current_time - _edu_params_cache['timestamp']) < cache_duration:
        return _edu_params_cache['params']

    try:
        res = session.get(EDU_CONFIG_URL, headers=get_random_headers(), timeout=3)
        res.raise_for_status()
        data = res.json()
        params = data.get('params', '')
        if params.startswith('?'):
            params = params[1:]
        params = params.replace('&amp;', '&')
        _edu_params_cache['params'] = params
        _edu_params_cache['timestamp'] = current_time
        return params
    except Exception as e:
        print(f"Failed to fetch edu params: {e}")
        return "autoplay=1&rel=0&modestbranding=1"

def safe_request(url, timeout=(2, 5)):
    try:
        res = session.get(url, headers=get_random_headers(), timeout=timeout)
        res.raise_for_status()
        return res.json()
    except:
        return None

def request_invidious_api(path, timeout=(2, 5)):
    random_instances = random.sample(INVIDIOUS_INSTANCES, min(3, len(INVIDIOUS_INSTANCES)))
    for instance in random_instances:
        try:
            url = instance + 'api/v1' + path
            res = session.get(url, headers=get_random_headers(), timeout=timeout)
            if res.status_code == 200:
                return res.json()
        except:
            continue
    return None

def get_youtube_search(query, max_results=20):
    if YOUTUBE_API_KEY:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&q={urllib.parse.quote(query)}&maxResults={max_results}&key={YOUTUBE_API_KEY}"
        try:
            res = session.get(url, timeout=5)
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
                    'authorId': snippet.get('channelId', ''),
                    'thumbnail': f"https://i.ytimg.com/vi/{item.get('id', {}).get('videoId', '')}/hqdefault.jpg",
                    'published': snippet.get('publishedAt', ''),
                    'description': snippet.get('description', ''),
                    'views': '',
                    'length': ''
                })
            return results
        except Exception as e:
            print(f"YouTube API error: {e}")

    return invidious_search(query)

def invidious_search(query, page=1):
    path = f"/search?q={urllib.parse.quote(query)}&page={page}&hl=jp"
    data = request_invidious_api(path)

    if not data:
        return []

    results = []
    for item in data:
        item_type = item.get('type', '')

        if item_type == 'video':
            length_seconds = item.get('lengthSeconds', 0)
            results.append({
                'type': 'video',
                'id': item.get('videoId', ''),
                'title': item.get('title', ''),
                'author': item.get('author', ''),
                'authorId': item.get('authorId', ''),
                'thumbnail': f"https://i.ytimg.com/vi/{item.get('videoId', '')}/hqdefault.jpg",
                'published': item.get('publishedText', ''),
                'views': item.get('viewCountText', ''),
                'length': str(datetime.timedelta(seconds=length_seconds)) if length_seconds else ''
            })
        elif item_type == 'channel':
            thumbnails = item.get('authorThumbnails', [])
            thumb_url = thumbnails[-1].get('url', '') if thumbnails else ''
            if thumb_url and not thumb_url.startswith('https'):
                thumb_url = 'https:' + thumb_url
            results.append({
                'type': 'channel',
                'id': item.get('authorId', ''),
                'author': item.get('author', ''),
                'thumbnail': thumb_url,
                'subscribers': item.get('subCount', 0)
            })
        elif item_type == 'playlist':
            results.append({
                'type': 'playlist',
                'id': item.get('playlistId', ''),
                'title': item.get('title', ''),
                'thumbnail': item.get('playlistThumbnail', ''),
                'count': item.get('videoCount', 0)
            })

    return results

def get_video_info(video_id):
    path = f"/videos/{urllib.parse.quote(video_id)}"
    data = request_invidious_api(path, timeout=(5, 15))

    if not data:
        try:
            res = session.get(f"{EDU_VIDEO_API}{video_id}", headers=get_random_headers(), timeout=(2, 6))
            res.raise_for_status()
            edu_data = res.json()

            related_videos = []
            for item in edu_data.get('related', [])[:20]:
                related_videos.append({
                    'id': item.get('videoId', ''),
                    'title': item.get('title', ''),
                    'author': item.get('channel', ''),
                    'authorId': item.get('channelId', ''),
                    'views': item.get('views', ''),
                    'thumbnail': f"https://i.ytimg.com/vi/{item.get('videoId', '')}/mqdefault.jpg",
                    'length': ''
                })

            return {
                'title': edu_data.get('title', ''),
                'description': edu_data.get('description', {}).get('formatted', ''),
                'author': edu_data.get('author', {}).get('name', ''),
                'authorId': edu_data.get('author', {}).get('id', ''),
                'authorThumbnail': edu_data.get('author', {}).get('thumbnail', ''),
                'views': edu_data.get('views', ''),
                'likes': edu_data.get('likes', ''),
                'subscribers': edu_data.get('author', {}).get('subscribers', ''),
                'published': edu_data.get('relativeDate', ''),
                'related': related_videos,
                'streamUrls': [],
                'highstreamUrl': None,
                'audioUrl': None
            }
        except Exception as e:
            print(f"EDU Video API error: {e}")
            return None

    recommended = data.get('recommendedVideos', data.get('recommendedvideo', []))
    related_videos = []
    for item in recommended[:20]:
        length_seconds = item.get('lengthSeconds', 0)
        related_videos.append({
            'id': item.get('videoId', ''),
            'title': item.get('title', ''),
            'author': item.get('author', ''),
            'authorId': item.get('authorId', ''),
            'views': item.get('viewCountText', ''),
            'thumbnail': f"https://i.ytimg.com/vi/{item.get('videoId', '')}/mqdefault.jpg",
            'length': str(datetime.timedelta(seconds=length_seconds)) if length_seconds else ''
        })

    adaptive_formats = data.get('adaptiveFormats', [])
    stream_urls = []
    highstream_url = None
    audio_url = None

    for stream in adaptive_formats:
        if stream.get('container') == 'webm' and stream.get('resolution'):
            stream_urls.append({
                'url': stream.get('url', ''),
                'resolution': stream.get('resolution', '')
            })
            if stream.get('resolution') == '1080p' and not highstream_url:
                highstream_url = stream.get('url')
            elif stream.get('resolution') == '720p' and not highstream_url:
                highstream_url = stream.get('url')

    for stream in adaptive_formats:
        if stream.get('container') == 'm4a' and stream.get('audioQuality') == 'AUDIO_QUALITY_MEDIUM':
            audio_url = stream.get('url')
            break

    format_streams = data.get('formatStreams', [])
    video_urls = [stream.get('url', '') for stream in reversed(format_streams)][:2]

    author_thumbnails = data.get('authorThumbnails', [])
    author_thumbnail = author_thumbnails[-1].get('url', '') if author_thumbnails else ''

    return {
        'title': data.get('title', ''),
        'description': data.get('descriptionHtml', '').replace('\n', '<br>'),
        'author': data.get('author', ''),
        'authorId': data.get('authorId', ''),
        'authorThumbnail': author_thumbnail,
        'views': data.get('viewCount', 0),
        'likes': data.get('likeCount', 0),
        'subscribers': data.get('subCountText', ''),
        'published': data.get('publishedText', ''),
        'lengthText': str(datetime.timedelta(seconds=data.get('lengthSeconds', 0))),
        'related': related_videos,
        'videoUrls': video_urls,
        'streamUrls': stream_urls,
        'highstreamUrl': highstream_url,
        'audioUrl': audio_url
    }

def get_channel_info(channel_id):
    path = f"/channels/{urllib.parse.quote(channel_id)}"
    data = request_invidious_api(path, timeout=(5, 15))

    if not data:
        return None

    latest_videos = data.get('latestVideos', data.get('latestvideo', []))
    videos = []
    for item in latest_videos:
        length_seconds = item.get('lengthSeconds', 0)
        videos.append({
            'type': 'video',
            'id': item.get('videoId', ''),
            'title': item.get('title', ''),
            'author': data.get('author', ''),
            'authorId': data.get('authorId', ''),
            'published': item.get('publishedText', ''),
            'views': item.get('viewCountText', ''),
            'length': str(datetime.timedelta(seconds=length_seconds)) if length_seconds else ''
        })

    author_thumbnails = data.get('authorThumbnails', [])
    author_thumbnail = author_thumbnails[-1].get('url', '') if author_thumbnails else ''

    author_banners = data.get('authorBanners', [])
    author_banner = urllib.parse.quote(author_banners[0].get('url', ''), safe='-_.~/:'
    ) if author_banners else ''

    return {
        'videos': videos,
        'channelName': data.get('author', ''),
        'channelIcon': author_thumbnail,
        'channelProfile': data.get('descriptionHtml', ''),
        'authorBanner': author_banner,
        'subscribers': data.get('subCount', 0),
        'tags': data.get('tags', [])
    }

def get_stream_url(video_id):
    edu_params = get_edu_params()
    urls = {
        'primary': None,
        'fallback': None,
        'm3u8': None,
        'embed': f"https://www.youtube-nocookie.com/embed/{video_id}?autoplay=1",
        'education': f"https://www.youtubeeducation.com/embed/{video_id}?{edu_params}"
    }

    try:
        res = session.get(f"{STREAM_API}{video_id}", headers=get_random_headers(), timeout=(3, 6))
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
        res = session.get(f"{M3U8_API}{video_id}", headers=get_random_headers(), timeout=(3, 6))
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
    path = f"/comments/{urllib.parse.quote(video_id)}?hl=jp"
    data = request_invidious_api(path)

    if not data:
        return []

    comments = []
    for item in data.get('comments', []):
        thumbnails = item.get('authorThumbnails', [])
        author_thumbnail = thumbnails[-1].get('url', '') if thumbnails else ''
        comments.append({
            'author': item.get('author', ''),
            'authorThumbnail': author_thumbnail,
            'authorId': item.get('authorId', ''),
            'content': item.get('contentHtml', '').replace('\n', '<br>'),
            'likes': item.get('likeCount', 0),
            'published': item.get('publishedText', '')
        })

    return comments

def get_trending():
    cache_duration = 300
    current_time = time.time()

    if _trending_cache['data'] and (current_time - _trending_cache['timestamp']) < cache_duration:
        return _trending_cache['data']

    path = "/popular"
    data = request_invidious_api(path, timeout=(2, 4))

    if data:
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
            _trending_cache['data'] = results
            _trending_cache['timestamp'] = current_time
            return results

    default_videos = [
        {'type': 'video', 'id': 'dQw4w9WgXcQ', 'title': 'Rick Astley - Never Gonna Give You Up', 'author': 'Rick Astley', 'thumbnail': 'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg', 'published': '', 'views': '17億 回視聴'},
        {'type': 'video', 'id': 'kJQP7kiw5Fk', 'title': 'Luis Fonsi - Despacito ft. Daddy Yankee', 'author': 'Luis Fonsi', 'thumbnail': 'https://i.ytimg.com/vi/kJQP7kiw5Fk/hqdefault.jpg', 'published': '', 'views': '80億 回視聴'},
        {'type': 'video', 'id': 'JGwWNGJdvx8', 'title': 'Ed Sheeran - Shape of You', 'author': 'Ed Sheeran', 'thumbnail': 'https://i.ytimg.com/vi/JGwWNGJdvx8/hqdefault.jpg', 'published': '', 'views': '64億 回視聴'},
        {'type': 'video', 'id': 'RgKAFK5djSk', 'title': 'Wiz Khalifa - See You Again ft. Charlie Puth', 'author': 'Wiz Khalifa', 'thumbnail': 'https://i.ytimg.com/vi/RgKAFK5djSk/hqdefault.jpg', 'published': '', 'views': '60億 回視聴'},
        {'type': 'video', 'id': 'OPf0YbXqDm0', 'title': 'Mark Ronson - Uptown Funk ft. Bruno Mars', 'author': 'Mark Ronson', 'thumbnail': 'https://i.ytimg.com/vi/OPf0YbXqDm0/hqdefault.jpg', 'published': '', 'views': '50億 回視聴'},
        {'type': 'video', 'id': '9bZkp7q19f0', 'title': 'PSY - Gangnam Style', 'author': 'PSY', 'thumbnail': 'https://i.ytimg.com/vi/9bZkp7q19f0/hqdefault.jpg', 'published': '', 'views': '50億 回視聴'},
        {'type': 'video', 'id': 'XqZsoesa55w', 'title': 'Baby Shark Dance', 'author': 'Pinkfong', 'thumbnail': 'https://i.ytimg.com/vi/XqZsoesa55w/hqdefault.jpg', 'published': '', 'views': '150億 回視聴'},
        {'type': 'video', 'id': 'fJ9rUzIMcZQ', 'title': 'Queen - Bohemian Rhapsody', 'author': 'Queen Official', 'thumbnail': 'https://i.ytimg.com/vi/fJ9rUzIMcZQ/hqdefault.jpg', 'published': '', 'views': '16億 回視聴'},
    ]
    return default_videos

def get_suggestions(keyword):
    try:
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(keyword)}"
        res = session.get(url, headers=get_random_headers(), timeout=2)
        if res.status_code == 200:
            data = res.json()
            return data[1] if len(data) > 1 else []
    except:
        pass
    return []

@app.route('/')
def index():
    theme = request.cookies.get('theme', 'dark')
    trending = get_trending()
    return render_template('index.html', videos=trending, theme=theme)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    page = request.args.get('page', '1')
    vc = request.cookies.get('vc', '1')
    proxy = request.cookies.get('proxy', 'False')
    theme = request.cookies.get('theme', 'dark')

    if not query:
        return render_template('search.html', results=[], query='', vc=vc, proxy=proxy, theme=theme, next='')

    results = get_youtube_search(query) if page == '1' else invidious_search(query, int(page))
    next_page = f"/search?q={urllib.parse.quote(query)}&page={int(page) + 1}"

    return render_template('search.html', results=results, query=query, vc=vc, proxy=proxy, theme=theme, next=next_page)

@app.route('/watch')
def watch():
    video_id = request.args.get('v', '')
    theme = request.cookies.get('theme', 'dark')
    proxy = request.cookies.get('proxy', 'False')

    if not video_id:
        return render_template('index.html', videos=get_trending(), theme=theme)

    video_info = get_video_info(video_id)
    stream_urls = get_stream_url(video_id)
    comments = get_comments(video_id)

    return render_template('watch.html',
                         video_id=video_id,
                         video=video_info,
                         streams=stream_urls,
                         comments=comments,
                         mode='stream',
                         theme=theme,
                         proxy=proxy)

@app.route('/w')
def watch_high_quality():
    video_id = request.args.get('v', '')
    theme = request.cookies.get('theme', 'dark')
    proxy = request.cookies.get('proxy', 'False')

    if not video_id:
        return render_template('index.html', videos=get_trending(), theme=theme)

    video_info = get_video_info(video_id)
    stream_urls = get_stream_url(video_id)
    comments = get_comments(video_id)

    return render_template('watch.html',
                         video_id=video_id,
                         video=video_info,
                         streams=stream_urls,
                         comments=comments,
                         mode='high',
                         theme=theme,
                         proxy=proxy)

@app.route('/ume')
def watch_embed():
    video_id = request.args.get('v', '')
    theme = request.cookies.get('theme', 'dark')
    proxy = request.cookies.get('proxy', 'False')

    if not video_id:
        return render_template('index.html', videos=get_trending(), theme=theme)

    video_info = get_video_info(video_id)
    stream_urls = get_stream_url(video_id)
    comments = get_comments(video_id)

    return render_template('watch.html',
                         video_id=video_id,
                         video=video_info,
                         streams=stream_urls,
                         comments=comments,
                         mode='embed',
                         theme=theme,
                         proxy=proxy)

@app.route('/edu')
def watch_education():
    video_id = request.args.get('v', '')
    theme = request.cookies.get('theme', 'dark')
    proxy = request.cookies.get('proxy', 'False')

    if not video_id:
        return render_template('index.html', videos=get_trending(), theme=theme)

    video_info = get_video_info(video_id)
    stream_urls = get_stream_url(video_id)
    comments = get_comments(video_id)

    return render_template('watch.html',
                         video_id=video_id,
                         video=video_info,
                         streams=stream_urls,
                         comments=comments,
                         mode='education',
                         theme=theme,
                         proxy=proxy)

@app.route('/channel/<channel_id>')
def channel(channel_id):
    theme = request.cookies.get('theme', 'dark')
    vc = request.cookies.get('vc', '1')
    proxy = request.cookies.get('proxy', 'False')

    channel_info = get_channel_info(channel_id)

    if not channel_info:
        return render_template('channel.html', channel=None, videos=[], theme=theme, vc=vc, proxy=proxy)

    return render_template('channel.html',
                         channel=channel_info,
                         videos=channel_info.get('videos', []),
                         theme=theme,
                         vc=vc,
                         proxy=proxy)

@app.route('/help')
def help_page():
    theme = request.cookies.get('theme', 'dark')
    return render_template('help.html', theme=theme)

@app.route('/blog')
def blog_page():
    theme = request.cookies.get('theme', 'dark')
    posts = [
        {
            'date': '2025-11-30',
            'category': 'お知らせ',
            'title': 'チョコTubeへようこそ！',
            'excerpt': 'youtubeサイトを作ってみたよ～',
            'content': '<p>読み込みが遅いだって？しゃーない。これから改善させるよ</p><p>あとはbbs(チャット)とかゲームとか追加したいなぁ<br>ちなみに何か意見とか聞きたいこととかあったら<a href="https://scratch.mit.edu/projects/1249572814/">ここでコメント</a>してね。</p>'
        }
    ]
    return render_template('blog.html', theme=theme, posts=posts)

@app.route('/thumbnail')
def thumbnail():
    video_id = request.args.get('v', '')
    if not video_id:
        return '', 404

    current_time = time.time()
    cache_key = video_id
    if cache_key in _thumbnail_cache:
        cached_data, cached_time = _thumbnail_cache[cache_key]
        if current_time - cached_time < 3600:
            response = Response(cached_data, mimetype='image/jpeg')
            response.headers['Cache-Control'] = 'public, max-age=3600'
            return response

    try:
        url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        res = session.get(url, headers=get_random_headers(), timeout=3)
        if len(_thumbnail_cache) > 500:
            oldest_key = min(_thumbnail_cache.keys(), key=lambda k: _thumbnail_cache[k][1])
            del _thumbnail_cache[oldest_key]
        _thumbnail_cache[cache_key] = (res.content, current_time)
        response = Response(res.content, mimetype='image/jpeg')
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response
    except:
        return '', 404

@app.route('/suggest')
def suggest():
    keyword = request.args.get('keyword', '')
    suggestions = get_suggestions(keyword)
    return jsonify(suggestions)

@app.route('/comments')
def comments_api():
    video_id = request.args.get('v', '')
    comments = get_comments(video_id)

    html = ''
    for comment in comments:
        html += f'''
        <div class="comment">
            <img src="{comment['authorThumbnail']}" alt="{comment['author']}" class="comment-avatar">
            <div class="comment-content">
                <div class="comment-header">
                    <a href="/channel/{comment['authorId']}" class="comment-author">{comment['author']}</a>
                    <span class="comment-date">{comment['published']}</span>
                </div>
                <div class="comment-text">{comment['content']}</div>
                <div class="comment-likes">👍 {comment['likes']}</div>
            </div>
        </div>
        '''

    return html if html else '<p class="no-comments">コメントはありません</p>'

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
