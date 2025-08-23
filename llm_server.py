from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

# 服务器端口，可根据需要修改
PORT = 8080

# 设置工作目录为当前脚本所在目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 创建并启动服务器
with HTTPServer(("", PORT), SimpleHTTPRequestHandler) as server:
    print(f"服务器已启动，访问地址: http://localhost:{PORT}")
    print("按 Ctrl+C 停止服务器")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
