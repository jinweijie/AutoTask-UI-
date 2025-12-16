import os
import sys


def resource_path(relative_path: str) -> str:
    """打包 / 开发环境下通用的资源路径解析"""
    try:
        base_path = sys._MEIPASS  # PyInstaller 运行时
    except AttributeError:
        base_path = os.path.abspath(".")  # 开发环境
    return os.path.join(base_path, relative_path)
