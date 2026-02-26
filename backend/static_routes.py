"""
静态文件服务路由
为前端应用提供静态文件服务
"""

from flask import send_from_directory, send_file
import os

def register_static_routes(app):
    """注册静态文件路由"""
    
    @app.route('/')
    def serve_index():
        """服务主页"""
        return send_file('static/index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        """服务静态文件"""
        # 检查文件是否存在
        static_path = os.path.join(app.root_path, 'static', path)
        if os.path.exists(static_path):
            return send_from_directory('static', path)
        else:
            # 如果文件不存在，返回index.html（用于React Router）
            return send_file('static/index.html')
