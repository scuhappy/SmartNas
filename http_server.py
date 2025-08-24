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

# 从config.json读取缩略图配置
def load_thumbnail_config():
    """从config.json加载缩略图配置"""
    config_data = load_config()
    resources = config_data.get('resources', {})
    
    # 查找photo类别的配置
    for resource_name, resource_info in resources.items():
        if resource_info.get('category') == 'photo':
            return {
                'size': float(resource_info.get('thumbnail_size', 0.2)),
                'path': resource_info.get('thumbnail_path', './thumbnails'),
                'per_page': 50  # 默认分页大小
            }
    
    # 如果没有找到photo类别，返回默认配置
    return {
        'size': 0.2,
        'path': './thumbnails',
        'per_page': 50
    }

# 加载缩略图配置
THUMBNAIL_CONFIG = load_thumbnail_config()

# 原始配置
SHARE_DIR = r"/"   # 你的视频目录
METADATA_FILE = "metadata.json"
COVER_DIR = "covers"
THUMBNAIL_DIR = THUMBNAIL_CONFIG['path']
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

# HTML 模板 - 照片类别(电脑端)
DESKTOP_PHOTO_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ user_name }} SmartNas - {{ path }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .controls { margin: 20px 0; text-align: center; }
        .controls select { padding: 5px; margin: 0 10px; }
        .pagination { margin: 20px 0; text-align: center; }
        .pagination a { margin: 0 5px; padding: 5px 10px; text-decoration: none; border: 1px solid #ddd; }
        .pagination .current { background-color: #4CAF50; color: white; }
        .pagination .disabled { color: #ccc; }
        .photo-grid { display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; }
        .photo-item { width: 200px; text-align: center; }
        .photo-item img { width: 100%; height: 150px; object-fit: cover; cursor: pointer; border-radius: 5px; }
        .photo-item p { margin: 5px 0; font-size: 0.9em; word-wrap: break-word; }
        .dir-item { margin: 10px 0; padding: 10px; background-color: #f0f0f0; border-radius: 4px; }
        .dir-item a { text-decoration: none; color: #333; }
        .file-item { margin: 10px 0; padding: 10px; background-color: #f9f9f9; border-radius: 4px; }
        .breadcrumb { margin-bottom: 20px; }
        .breadcrumb a { margin: 0 5px; }
        .info { text-align: center; margin: 10px 0; color: #666; }
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

    <div class="controls">
        <label>每页显示: 
            <select onchange="changePerPage(this.value)">
                {% for size in valid_per_page %}
                    <option value="{{ size }}" {% if size == per_page %}selected{% endif %}>{{ size }}张</option>
                {% endfor %}
            </select>
        </label>
    </div>

    <div class="info">
        共 {{ total_items }} 项，第 {{ current_page }} / {{ total_pages }} 页
    </div>

    <div class="photo-grid">
    {% for name, is_dir, metadata, category in files %}
        {% if is_dir %}
            <div class="dir-item">📁 <a href="{{ path }}{{ name }}/">{{ name }}</a></div>
        {% elif category == 'photo' and metadata and metadata.type == 'image' %}
            <div class="photo-item">
                <a href="/image/{{ metadata.full_path | replace('/', '|') }}">
                    {% if metadata.thumbnail %}
                        <img src="/thumbnails/{{ metadata.thumbnail }}" alt="{{ name }}">
                    {% else %}
                        <img src="/raw_image/{{ metadata.full_path | replace('/', '|') }}" alt="{{ name }}" style="width: 100%; height: 150px; object-fit: cover;">
                    {% endif %}
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

    <div class="pagination">
        {% if current_page > 1 %}
            <a href="{{ path }}?page={{ current_page - 1 }}{% if per_page != 50 %}&per_page={{ per_page }}{% endif %}">上一页</a>
        {% else %}
            <span class="disabled">上一页</span>
        {% endif %}

        {% for p in range(1, total_pages + 1) %}
            {% if p == current_page %}
                <span class="current">{{ p }}</span>
            {% elif p == 1 or p == total_pages or (p >= current_page - 2 and p <= current_page + 2) %}
                <a href="{{ path }}?page={{ p }}{% if per_page != 50 %}&per_page={{ per_page }}{% endif %}">{{ p }}</a>
            {% elif p == current_page - 3 or p == current_page + 3 %}
                <span>...</span>
            {% endif %}
        {% endfor %}

        {% if current_page < total_pages %}
            <a href="{{ path }}?page={{ current_page + 1 }}{% if per_page != 50 %}&per_page={{ per_page }}{% endif %}">下一页</a>
        {% else %}
            <span class="disabled">下一页</span>
        {% endif %}
    </div>

    <script>
        function changePerPage(size) {
            const url = new URL(window.location);
            url.searchParams.set('per_page', size);
            url.searchParams.set('page', 1);
            window.location = url;
        }
    </script>
</body>
</html>
"""

# HTML 模板 - 照片类别(手机端)
MOBILE_PHOTO_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ user_name }} SmartNas - {{ path }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 10px; padding: 0; }
        .header { text-align: center; margin-bottom: 20px; }
        .controls { margin: 15px 0; text-align: center; }
        .controls select { padding: 8px; margin: 0 5px; }
        .pagination { margin: 15px 0; text-align: center; }
        .pagination a { margin: 0 3px; padding: 8px 12px; text-decoration: none; border: 1px solid #ddd; font-size: 0.9em; }
        .pagination .current { background-color: #4CAF50; color: white; }
        .pagination .disabled { color: #ccc; }
        .photo-grid { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
        .photo-item { width: 120px; text-align: center; }
        .photo-item img { width: 100%; height: 100px; object-fit: cover; cursor: pointer; border-radius: 5px; }
        .photo-item p { margin: 3px 0; font-size: 0.8em; word-wrap: break-word; }
        .dir-item { margin: 8px 0; padding: 8px; background-color: #f0f0f0; border-radius: 4px; }
        .dir-item a { text-decoration: none; color: #333; }
        .file-item { margin: 8px 0; padding: 8px; background-color: #f9f9f9; border-radius: 4px; }
        .breadcrumb { margin-bottom: 15px; font-size: 0.9em; }
        .breadcrumb a { margin: 0 3px; }
        .info { text-align: center; margin: 10px 0; color: #666; font-size: 0.9em; }
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

    <div class="controls">
        <label>每页: 
            <select onchange="changePerPage(this.value)">
                {% for size in valid_per_page %}
                    <option value="{{ size }}" {% if size == per_page %}selected{% endif %}>{{ size }}</option>
                {% endfor %}
            </select>
        </label>
    </div>

    <div class="info">
        {{ total_items }} 项 {{ current_page }}/{{ total_pages }}
    </div>

    <div class="photo-grid">
    {% for name, is_dir, metadata, category in files %}
        {% if is_dir %}
            <div class="dir-item">📁 <a href="{{ path }}{{ name }}/">{{ name }}</a></div>
        {% elif category == 'photo' and metadata and metadata.type == 'image' %}
            <div class="photo-item">
                <a href="/image/{{ metadata.full_path | replace('/', '|') }}">
                    {% if metadata.thumbnail %}
                        <img src="/thumbnails/{{ metadata.thumbnail }}" alt="{{ name }}">
                    {% else %}
                        <img src="/raw_image/{{ metadata.full_path | replace('/', '|') }}" alt="{{ name }}" style="width: 100%; height: 100px; object-fit: cover;">
                    {% endif %}
                </a>
                <p>{{ name[:15] }}{% if name|length > 15 %}...{% endif %}</p>
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

    <div class="pagination">
        {% if current_page > 1 %}
            <a href="{{ path }}?page={{ current_page - 1 }}{% if per_page != 50 %}&per_page={{ per_page }}{% endif %}">‹</a>
        {% else %}
            <span class="disabled">‹</span>
        {% endif %}

        {% for p in range(1, total_pages + 1) %}
            {% if p == current_page %}
                <span class="current">{{ p }}</span>
            {% elif p <= 3 or p >= total_pages - 2 or (p >= current_page - 1 and p <= current_page + 1) %}
                <a href="{{ path }}?page={{ p }}{% if per_page != 50 %}&per_page={{ per_page }}{% endif %}">{{ p }}</a>
            {% endif %}
        {% endfor %}

        {% if current_page < total_pages %}
            <a href="{{ path }}?page={{ current_page + 1 }}{% if per_page != 50 %}&per_page={{ per_page }}{% endif %}">›</a>
        {% else %}
            <span class="disabled">›</span>
        {% endif %}
    </div>

    <script>
        function changePerPage(size) {
            const url = new URL(window.location);
            url.searchParams.set('per_page', size);
            url.searchParams.set('page', 1);
            window.location = url;
        }
    </script>
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

    # 获取分页参数
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', THUMBNAIL_CONFIG['per_page']))
        # 验证per_page选项
        valid_per_page = [20, 50, 100, 200]
        if per_page not in valid_per_page:
            per_page = THUMBNAIL_CONFIG['per_page']
    except ValueError:
        page = 1
        per_page = THUMBNAIL_CONFIG['per_page']

    metadata = load_metadata()
    files, total_items, total_pages = list_files(abs_path, metadata, page, per_page)
    breadcrumb = build_breadcrumb(req_path)
    category = get_file_category(abs_path)

    # 检测设备类型
    user_agent = request.user_agent.string
    is_mobile = is_mobile_device(user_agent)

    # 构建分页URL参数
    base_url = f'/{req_path}' if req_path else '/'
    query_params = []
    if per_page != THUMBNAIL_CONFIG['per_page']:
        query_params.append(f'per_page={per_page}')

    # 选择模板
    if category == 'photo':
        if is_mobile:
            template = MOBILE_PHOTO_TEMPLATE
        else:
            template = DESKTOP_PHOTO_TEMPLATE
    else:
        if is_mobile:
            template = MOBILE_INDEX_TEMPLATE
        else:
            template = DESKTOP_INDEX_TEMPLATE

    return render_template_string(
        template,
        files=files,
        path=base_url,
        breadcrumb=breadcrumb,
        user_name=USER_NAME,
        current_page=page,
        total_pages=total_pages,
        total_items=total_items,
        per_page=per_page,
        valid_per_page=[20, 50, 100, 200],
        category=category
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

@app.route('/thumbnails/<thumb_filename>')
def serve_thumbnail(thumb_filename):
    """提供缩略图"""
    try:
        thumb_path = os.path.join(THUMBNAIL_CONFIG['path'], f"{thumb_filename}.jpg")
        if not os.path.exists(thumb_path):
            return "Thumbnail not found", 404
        return send_from_directory(THUMBNAIL_CONFIG['path'], f"{thumb_filename}.jpg")
    except Exception as e:
        return f"Error serving thumbnail: {str(e)}", 500

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
    thumbnail_path = THUMBNAIL_CONFIG.get('path', './thumbnails')
    os.makedirs(thumbnail_path, exist_ok=True)
    print(f"Serving at http://0.0.0.0:5000")
    print(f"Thumbnail size: {THUMBNAIL_CONFIG.get('size', 0.2)}")
    print(f"Thumbnail path: {thumbnail_path}")
    app.run(host='0.0.0.0', port=5000, debug=True)
