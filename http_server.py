from flask import Flask, send_from_directory, render_template_string, abort, request
import os
import json
import re
from PIL import Image

# 检测设备类型
def is_mobile_device(user_agent):
    mobile_keywords = ['Mobile', 'Android', 'iPhone', 'iPad', 'Windows Phone', 'BlackBerry']
    return any(keyword in user_agent for keyword in mobile_keywords)

# 读取配置文件
def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"user_info": {"name": "User"}, "resources": {}}

# 全局配置
config = load_config()
USER_NAME = config.get('user_info', {}).get('name', 'User')
RESOURCES = config.get('resources', {})

# 原始配置
SHARE_DIR = r"/"   # 你的视频目录
METADATA_FILE = "metadata.json"
COVER_DIR = "covers"
THUMBNAIL_DIR = "thumbnails"
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

# 获取文件类别
def get_file_category(file_path):
    """根据文件路径判断其类别"""
    abs_path = os.path.abspath(file_path)
    for resource_name, resource_info in RESOURCES.items():
        paths = resource_info.get('paths', [])
        category = resource_info.get('category', 'av')
        for path in paths:
            abs_resource_path = os.path.abspath(path)
            if abs_path.startswith(abs_resource_path):
                return category
    return 'av'  # 默认类别

# 移除缩略图创建功能，直接使用原图
# 缩略图功能已被移除，改为直接使用原图显示小尺寸

# 检查是否为图片文件
def is_image_file(filename):
    """检查是否为支持的图片格式"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    return any(filename.lower().endswith(ext) for ext in image_extensions)

# 检查是否为视频文件
def is_video_file(filename):
    """检查是否为支持的视频格式"""
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
    return any(filename.lower().endswith(ext) for ext in video_extensions)

# 遍历目录
def list_files(directory, metadata):
    entries = []
    category = get_file_category(directory)
    
    for name in os.listdir(directory):
        full_path = os.path.join(directory, name)
        is_dir = os.path.isdir(full_path)
        
        if is_dir:
            entries.append((name, is_dir, None, category))
        else:
            if category == 'av':
                # AV类别的原有逻辑
                fanhao = extract_fanhao(name)
                file_metadata = None
                if fanhao and fanhao in metadata:
                    file_metadata = {
                        "fanhao": fanhao,
                        "title": metadata[fanhao]["title"],
                        "cover_path": metadata[fanhao].get("cover_path", f"{fanhao}.jpg"),
                        "video_path": full_path
                    }
                entries.append((name, is_dir, file_metadata, category))
            elif category == 'photo':
                # 照片类别的逻辑
                if is_image_file(name):
                    # 直接使用原图，无需缩略图
                    abs_full_path = os.path.abspath(full_path)
                    
                    entries.append((name, is_dir, {
                        "type": "image",
                        "full_path": abs_full_path
                    }, category))
                elif is_video_file(name):
                    # 照片类别中的视频文件
                    entries.append((name, is_dir, {
                        "type": "video",
                        "video_path": full_path
                    }, category))
                else:
                    # 其他文件
                    entries.append((name, is_dir, None, category))
            else:
                # 其他类别
                entries.append((name, is_dir, None, category))
    
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
    <title>{{ user_name }} SmartNas - {{ path }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .file-list { display: flex; flex-wrap: wrap; gap: 20px; }
        .video-item { width: 200px; text-align: center; }
        .video-item img { width: 100%; height: auto; cursor: pointer; }
        .video-item p { margin: 5px 0; word-wrap: break-word; }
        .photo-item { width: 150px; text-align: center; }
         .photo-item img { width: 100%; height: 150px; object-fit: cover; cursor: pointer; }
         .dir-item { margin: 10px 0; }
         .file-item { margin: 10px 0; }
         .breadcrumb { margin-bottom: 20px; }
         .breadcrumb a { margin: 0 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ user_name }} SmartNas</h1>
        <div class="breadcrumb">
            当前位置: <a href="/">首页</a>
            {% for part, url in breadcrumb %}
                / <a href="{{ url }}">{{ part }}</a>
            {% endfor %}
        </div>
    </div>
    
    <div class="file-list">
    {% for name, is_dir, metadata, category in files %}
        {% if is_dir %}
            <div class="dir-item">📁 <a href="{{ path }}{{ name }}/">{{ name }}</a></div>
        {% elif category == 'av' and metadata %}
            <div class="video-item">
                <a href="/play/{{ metadata.fanhao }}">
                    <img src="/covers/{{ metadata.cover_path | replace('covers\\\\', '') | replace('covers/', '') }}" alt="{{ name }}">
                </a>
                <p><a href="/play/{{ metadata.fanhao }}">{{ metadata.title }}</a></p>
            </div>
        {% elif category == 'photo' and metadata and metadata.type == 'image' %}
             <div class="photo-item">
                 <a href="/image/{{ metadata.full_path | replace('/', '|') }}">
                     <img src="/raw_image/{{ metadata.full_path | replace('/', '|') }}" alt="{{ name }}">
                 </a>
                 <p>{{ name }}</p>
             </div>
        {% elif category == 'photo' and metadata and metadata.type == 'video' %}
            <div class="file-item">
                🎬 <a href="/play_video/{{ metadata.video_path | replace('/', '|') }}">{{ name }}</a>
            </div>
        {% else %}
            <div class="file-item">📄 <a href="{{ path }}{{ name }}">{{ name }}</a></div>
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
    <title>{{ user_name }} SmartNas - {{ path }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 10px; padding: 0; }
        .header { text-align: center; margin-bottom: 20px; }
        h1 { font-size: 1.5em; margin: 10px 0; }
        .file-list { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
        .video-item { width: 140px; text-align: center; }
        .video-item img { width: 100%; height: auto; cursor: pointer; border-radius: 5px; }
        .video-item p { margin: 5px 0; font-size: 0.9em; word-wrap: break-word; }
        .photo-item { width: 120px; text-align: center; }
        .photo-item img { width: 100%; height: 120px; object-fit: cover; cursor: pointer; border-radius: 5px; }
        .dir-item { margin: 8px 0; padding: 8px; background-color: #f0f0f0; border-radius: 4px; }
        .dir-item a { text-decoration: none; color: #333; }
        .file-item { margin: 8px 0; padding: 8px; background-color: #f9f9f9; border-radius: 4px; }
        .back-button { display: inline-block; padding: 8px 15px; margin: 10px 0; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; }
        .breadcrumb { margin-bottom: 15px; font-size: 0.9em; }
        .breadcrumb a { margin: 0 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ user_name }} SmartNas</h1>
        <div class="breadcrumb">
            当前位置: <a href="/">首页</a>
            {% for part, url in breadcrumb %}
                / <a href="{{ url }}">{{ part }}</a>
            {% endfor %}
        </div>
    </div>
    
    {% if path != '/' %}
        <a href="/" class="back-button">返回首页</a>
    {% endif %}
    
    <div class="file-list">
    {% for name, is_dir, metadata, category in files %}
        {% if is_dir %}
            <div class="dir-item">📁 <a href="{{ path }}{{ name }}/">{{ name }}</a></div>
        {% elif category == 'av' and metadata %}
            <div class="video-item">
                <a href="/play/{{ metadata.fanhao }}">
                    <img src="/covers/{{ metadata.cover_path | replace('covers\\\\', '') | replace('covers/', '') }}" alt="{{ name }}">
                </a>
                <p><a href="/play/{{ metadata.fanhao }}">{{ metadata.title }}</a></p>
            </div>
        {% elif category == 'photo' and metadata and metadata.type == 'image' %}
             <div class="photo-item">
                 <a href="/image/{{ metadata.full_path | replace('/', '|') }}">
                     <img src="/raw_image/{{ metadata.full_path | replace('/', '|') }}" alt="{{ name }}">
                 </a>
                 <p style="font-size: 0.8em;">{{ name }}</p>
             </div>
        {% elif category == 'photo' and metadata and metadata.type == 'video' %}
            <div class="file-item">
                🎬 <a href="/play_video/{{ metadata.video_path | replace('/', '|') }}">{{ name }}</a>
            </div>
        {% else %}
            <div class="file-item">📄 <a href="{{ path }}{{ name }}">{{ name }}</a></div>
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
            breadcrumb=breadcrumb,
            user_name=USER_NAME
        )
    else:
        return render_template_string(
            DESKTOP_INDEX_TEMPLATE,
            files=files,
            path=f'/{req_path}' if req_path else '/',
            breadcrumb=breadcrumb,
            user_name=USER_NAME
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

@app.route('/image/<path:filename>')
def view_image(filename):
    """查看大图"""
    image_path = filename.replace('|', '/')
    abs_path = os.path.join(SHARE_DIR, image_path)
    if not os.path.exists(abs_path):
        return "Image not found", 404
    
    user_agent = request.user_agent.string
    is_mobile = is_mobile_device(user_agent)
    
    template = """
<!DOCTYPE html>
<html>
<head>
    <title>查看图片 - {{ name }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; text-align: center; background: #000; }
        img { max-width: 100%; max-height: 100vh; margin: 20px auto; display: block; }
        .back-button { position: fixed; top: 10px; left: 10px; padding: 8px 15px; background-color: rgba(0,0,0,0.7); color: white; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <a href="javascript:history.back()" class="back-button">返回</a>
    <img src="/raw_image/{{ filename | replace('/', '|') }}" alt="{{ name }}">
</body>
</html>
    """
    return render_template_string(template, filename=filename, name=os.path.basename(abs_path))

@app.route('/raw_image/<path:filename>')
def serve_raw_image(filename):
    """提供原始图片"""
    try:
        # 解码路径：将|替换回/
        decoded_path = filename.replace('|', '/')
        
        # 确保路径在SHARE_DIR范围内，防止目录遍历攻击
        abs_path = os.path.abspath(os.path.join(SHARE_DIR, decoded_path.lstrip('/')))
        share_dir_abs = os.path.abspath(SHARE_DIR)
        
        if not abs_path.startswith(share_dir_abs):
            return "Invalid path", 403
            
        if not os.path.exists(abs_path):
            return f"Image not found: {decoded_path}", 404
            
        if not os.path.isfile(abs_path):
            return "Path is not a file", 404
            
        return send_from_directory(os.path.dirname(abs_path), os.path.basename(abs_path))
    except Exception as e:
        return f"Error serving image: {str(e)}", 500

@app.route('/play_video/<path:filename>')
def play_video_file(filename):
    """播放视频文件"""
    video_path = filename.replace('|', '/')
    abs_path = os.path.join(SHARE_DIR, video_path)
    if not os.path.exists(abs_path):
        return "Video not found", 404
    
    user_agent = request.user_agent.string
    is_mobile = is_mobile_device(user_agent)
    
    template = """
<!DOCTYPE html>
<html>
<head>
    <title>播放视频 - {{ name }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 10px; text-align: center; }
        video { width: 100%; max-width: 800px; margin: 20px auto; }
        .back-button { display: inline-block; padding: 8px 15px; margin: 10px 0; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <h2>{{ name }}</h2>
    <video controls autoplay>
        <source src="/raw_video/{{ filename | replace('/', '|') }}" type="video/mp4">
        Your browser does not support the video tag.
    </video>
    <div><a href="javascript:history.back()" class="back-button">返回</a></div>
</body>
</html>
    """
    return render_template_string(template, filename=filename, name=os.path.basename(abs_path))

@app.route('/raw_video/<path:filename>')
def serve_raw_video(filename):
    """提供原始视频"""
    try:
        # 解码路径：将|替换回/
        decoded_path = filename.replace('|', '/')
        
        # 确保路径在SHARE_DIR范围内，防止目录遍历攻击
        abs_path = os.path.abspath(os.path.join(SHARE_DIR, decoded_path.lstrip('/')))
        share_dir_abs = os.path.abspath(SHARE_DIR)
        
        if not abs_path.startswith(share_dir_abs):
            return "Invalid path", 403
            
        if not os.path.exists(abs_path):
            return f"Video not found: {decoded_path}", 404
            
        if not os.path.isfile(abs_path):
            return "Path is not a file", 404
            
        return send_from_directory(os.path.dirname(abs_path), os.path.basename(abs_path))
    except Exception as e:
        return f"Error serving video: {str(e)}", 500

if __name__ == '__main__':
    os.makedirs(SHARE_DIR, exist_ok=True)
    os.makedirs(COVER_DIR, exist_ok=True)
    print(f"Serving at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
