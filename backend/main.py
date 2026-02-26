#!/usr/bin/env python3
"""
在线考试系统部署入口文件
"""

from app import app

if __name__ == '__main__':
    # 确保数据库表已创建
    with app.app_context():
        from models import db
        db.create_all()
        print("数据库表创建完成")
        
        # 创建示例数据
        try:
            from sample_data import create_sample_data
            create_sample_data()
            print("示例数据创建完成")
        except Exception as e:
            print(f"示例数据创建失败: {e}")
    
    # 启动应用
    app.run(host='0.0.0.0', port=5000, debug=False)
