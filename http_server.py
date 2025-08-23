from flask import Flask, send_from_directory, render_template_string, abort, request
import os
import json
import re

# 检测设备类型
def is_mobile_device(user_agent):
    mobile_keywords = ['Mobile', 'Android', 'iPhone', 'iPad', 'Windows Phone', 'BlackBerry']
    return any(keyword in user_agent for keyword in mobile_keywords)

# 配置
SHARE_DIR = r"G:\\Videos"   # 你的视频目录
METADATA_FILE = "metadata.json"
COVER_DIR = "covers"
app = Flask(__name__)

# 加载元数据
def load_metadata():
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# 提取番号
def extract_fanhao(filename):
    match = re.search(r"[A-Z]{2,5}-\d{2,5}", filename, re.I)
    return match.group(0).upper() if match else None

# 遍历目录
def list_files(directory, metadata):
    entries = []
    for name in os.listdir(directory):
        full_path = os.path.join(directory, name)
        is_dir = os.path.isdir(full_path)
        fanhao = extract_fanhao(name) if not is_dir else None
        file_metadata = None
        if fanhao and fanhao in metadata:
            file_metadata = {
                "fanhao": fanhao,
                "title": metadata[fanhao]["title"],
                "cover_path": metadata[fanhao].get("cover_path", f"{fanhao}.jpg"),
                "video_path": full_path
            }
        entries.append((name, is_dir, file_metadata))
    return entries

# 构建面包屑导航
def build_breadcrumb(req_path):
    parts = req_path.strip("/").split("/") if req_path else []
    breadcrumb = []
    current_path = ""
    for part in parts:
        current_path = f"{current_path}{part}/"
        breadcrumb.append((part, f"/{current_path}"))
    return breadcrumb

# HTML 模板 - 首页(电脑端)
DESKTOP_INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>File Server - {{ path }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .file-list { display: flex; flex-wrap: wrap; gap: 20px; }
        .video-item { width: 200px; text-align: center; }
        .video-item img { width: 100%; height: auto; cursor: pointer; }
        .video-item p { margin: 5px 0; word-wrap: break-word; }
        .dir-item { margin: 10px 0; }
    </style>
</head>
<body>
    <h1>File Server</h1>
    <div class="file-list">
    {% for name, is_dir, metadata in files %}
        {% if is_dir %}
            <div class="dir-item">[DIR] <a href="{{ path }}{{ name }}/">{{ name }}</a></div>
        {% elif metadata %}
            <div class="video-item">
                <a href="/play/{{ metadata.fanhao }}">
                    <img src="/covers/{{ metadata.cover_path | replace('covers\\', '') | replace('covers/', '') }}" alt="{{ name }}">
                </a>
                <p><a href="/play/{{ metadata.fanhao }}">{{ metadata.title }}</a></p>
            </div>
        {% else %}
            <div class="dir-item">[FILE] <a href="{{ path }}{{ name }}">{{ name }}</a></div>
        {% endif %}
    {% endfor %}
    </div>
</body>
</html>
"""

# HTML 模板 - 首页(手机端)
MOBILE_INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>File Server - {{ path }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 10px; padding: 0; }
        h1 { font-size: 1.5em; margin: 10px 0; text-align: center; }
        .file-list { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
        .video-item { width: 140px; text-align: center; }
        .video-item img { width: 100%; height: auto; cursor: pointer; border-radius: 5px; }
        .video-item p { margin: 5px 0; font-size: 0.9em; word-wrap: break-word; }
        .dir-item { margin: 8px 0; padding: 8px; background-color: #f0f0f0; border-radius: 4px; }
        .dir-item a { text-decoration: none; color: #333; }
        .back-button { display: inline-block; padding: 8px 15px; margin: 10px 0; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>File Server</h1>
    {% if path != '/' %}
        <a href="/" class="back-button">返回首页</a>
    {% endif %}
    <div class="file-list">
    {% for name, is_dir, metadata in files %}
        {% if is_dir %}
            <div class="dir-item">[DIR] <a href="{{ path }}{{ name }}/">{{ name }}</a></div>
        {% elif metadata %}
            <div class="video-item">
                <a href="/play/{{ metadata.fanhao }}">
                    <img src="/covers/{{ metadata.cover_path | replace('covers\\', '') | replace('covers/', '') }}" alt="{{ name }}">
                </a>
                <p><a href="/play/{{ metadata.fanhao }}">{{ metadata.title }}</a></p>
            </div>
        {% else %}
            <div class="dir-item">[FILE] <a href="{{ path }}{{ name }}">{{ name }}</a></div>
        {% endif %}
    {% endfor %}
    </div>
</body>
</html>
"""

# HTML 模板 - 播放页(电脑端)
DESKTOP_PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Playing {{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; text-align: center; }
        video, audio { max-width: 80%; height: auto; margin-top: 20px; }
    </style>
</head>
<body>
    <h2>{{ title }}</h2>
    {% if video_path.endswith(".mp3") or video_path.endswith(".wav") %}
        <audio controls>
            <source src="/video/{{ fanhao }}" type="audio/mpeg">
            Your browser does not support the audio tag.
        </audio>
    {% else %}
        <video controls autoplay>
            <source src="/video/{{ fanhao }}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
    {% endif %}
    <div><a href="/">返回首页</a></div>
</body>
</html>
"""

# HTML 模板 - 播放页(手机端)
MOBILE_PLAYER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Playing {{ title }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 10px; padding: 0; text-align: center; }
        h2 { font-size: 1.2em; margin: 10px 0; }
        video, audio { width: 100%; height: auto; margin-top: 10px; }
        .back-button { display: inline-block; padding: 8px 15px; margin: 15px 0; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <h2>{{ title }}</h2>
    {% if video_path.endswith(".mp3") or video_path.endswith(".wav") %}
        <audio controls style="width: 100%;">
            <source src="/video/{{ fanhao }}" type="audio/mpeg">
            Your browser does not support the audio tag.
        </audio>
    {% else %}
        <video controls autoplay style="width: 100%;">
            <source src="/video/{{ fanhao }}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
    {% endif %}
    <div><a href="/" class="back-button">返回首页</a></div>
</body>
</html>
"""

@app.route('/', defaults={'req_path': ''})
@app.route('/<path:req_path>')
def dir_listing(req_path):
    abs_path = os.path.join(SHARE_DIR, req_path)
    if not os.path.exists(abs_path):
        return "Not Found", 404
    if os.path.isfile(abs_path):
        return send_from_directory(SHARE_DIR, req_path)

    metadata = load_metadata()
    files = list_files(abs_path, metadata)
    breadcrumb = build_breadcrumb(req_path)

    # 检测设备类型
    user_agent = request.user_agent.string
    is_mobile = is_mobile_device(user_agent)

    if is_mobile:
        return render_template_string(
            MOBILE_INDEX_TEMPLATE,
            files=files,
            path=f'/{req_path}' if req_path else '/',
            breadcrumb=breadcrumb
        )
    else:
        return render_template_string(
            DESKTOP_INDEX_TEMPLATE,
            files=files,
            path=f'/{req_path}' if req_path else '/',
            breadcrumb=breadcrumb
        )

@app.route('/play/<fanhao>')
def play_video(fanhao):
    metadata = load_metadata()
    if fanhao not in metadata:
        return "Video not found", 404
    title = metadata[fanhao]["title"]

    # 检测设备类型
    user_agent = request.user_agent.string
    is_mobile = is_mobile_device(user_agent)

    if is_mobile:
        return render_template_string(
            MOBILE_PLAYER_TEMPLATE,
            fanhao=fanhao,
            video_path=metadata[fanhao].get("video_file", ""),
            title=title
        )
    else:
        return render_template_string(
            DESKTOP_PLAYER_TEMPLATE,
            fanhao=fanhao,
            video_path=metadata[fanhao].get("video_file", ""),
            title=title
        )

@app.route('/video/<fanhao>')
def serve_video(fanhao):
    metadata = load_metadata()
    if fanhao not in metadata:
        return "Not Found", 404
    # 本地真实路径
    abs_path = metadata[fanhao]["video_file"]
    if not os.path.exists(abs_path):
        return "File Missing", 404
    return send_from_directory(os.path.dirname(abs_path), os.path.basename(abs_path))

@app.route('/covers/<path:filename>')
def serve_cover(filename):
    return send_from_directory(COVER_DIR, filename)

if __name__ == '__main__':
    os.makedirs(SHARE_DIR, exist_ok=True)
    os.makedirs(COVER_DIR, exist_ok=True)
    print(f"Serving at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
