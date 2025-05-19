#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启动应用的入口脚本
"""
import os
import logging
from app import create_app

# 确保data目录存在
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(data_dir, exist_ok=True)

# 设置环境变量
os.environ['DATA_DIR'] = data_dir

# 设置日志级别环境变量
os.environ['FLASK_LOG_LEVEL'] = 'DEBUG'

# 设置开发环境以启用热加载
os.environ['FLASK_ENV'] = 'development'

# 配置根日志记录器
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建应用实例
app = create_app()
 
if __name__ == '__main__':
    # 运行应用，启用调试模式和热加载
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=True) 