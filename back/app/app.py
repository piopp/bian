"""
应用初始化
注意：此文件保留向后兼容，实际初始化在app/__init__.py中
"""

# 导入真正的初始化函数
from app import create_app

# 创建应用实例，用于直接运行此文件时使用
app = create_app() 