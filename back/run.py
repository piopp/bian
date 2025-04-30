#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启动应用的入口脚本
"""
import os
from app import create_app

# 确保data目录存在
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(data_dir, exist_ok=True)

# 设置环境变量
os.environ['DATA_DIR'] = data_dir

# 创建应用实例
app = create_app()
 
if __name__ == '__main__':
    # 在开发环境中启动应用，生产环境应使用Gunicorn等WSGI服务器
    app.run(host='0.0.0.0', port=5000, debug=True) 