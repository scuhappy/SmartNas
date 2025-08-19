from flask import Flask, send_from_directory, render_template_string
import os

# 配置共享目录
SHARE_DIR = "H:/"
app = Flask(__name__)

# HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>File Server</title>
</head>
<body>
    <h1>File Server - {{ path }}</h1>
    <ul>
    {% for name, is_dir in files %}
        {% if is_dir %}
            <li>[DIR] <a href="{{ path }}{{ name }}/">{{ name }}</a></li>
        {% elif name.lower().endswith(('.mp4', '.webm', '.ogg')) %}
            <li>[VIDEO] {{ name }}
                <br>
                <video width="480" controls>
                    <source src="{{ path }}{{ name }}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </li>
        {% else %}
            <li>[FILE] <a href="{{ path }}{{ name }}">{{ name }}</a></li>
        {% endif %}
    {% endfor %}
    </ul>
</body>
</html>
"""

def list_files(directory):
    entries = []
    for name in os.listdir(directory):
        full_path = os.path.join(directory, name)
        entries.append((name, os.path.isdir(full_path)))
    return entries

@app.route('/', defaults={'req_path': ''})
@app.route('/<path:req_path>')
def dir_listing(req_path):
    abs_path = os.path.join(SHARE_DIR, req_path)

    if not os.path.exists(abs_path):
        return "Not Found", 404

    if os.path.isfile(abs_path):
        # 返回文件内容
        return send_from_directory(SHARE_DIR, req_path)

    # 返回目录列表
    files = list_files(abs_path)
    return render_template_string(HTML_TEMPLATE, files=files, path=f'/{req_path}' if req_path else '/')

if __name__ == '__main__':
    os.makedirs(SHARE_DIR, exist_ok=True)
    print(f"Serving files from {os.path.abspath(SHARE_DIR)} at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
