# -*- coding: utf-8 -*-
"""
CIW 智能办公平台 V2.07 - 启动入口

运行：双击 start.bat  或  python main.py
依赖：pip install -r requirements.txt（start.bat 会自动处理）
Embedding 请启动 LM Studio；生成可本地 Chat 或云端 OpenAI 兼容（见设置）。
"""

import sys
import json
import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from office.monitor import setup_logger
from ui.main_window import MainWindow

_APP_ROOT = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(_APP_ROOT, "settings.json")


def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "theme": "theme_male",
        "language": "zh_CN",
        "llm_base_url": "http://localhost:1234/v1",
        "llm_model": "auto",
        "chat_backend": "local",
        "local_chat_enabled": True,
        "cloud_base_url": "",
        "cloud_api_key": "",
        "cloud_model": "",
        "model_n_ctx": 12288,
        "max_tokens": 0,
        "thread_max_turns": 6,
        "thread_max_chars": 5000,
        "kb_char_budget": 0,
        "translate_chunk_chars": 0,
        "translate_single_max_chars": 6000,
        "keep_runtime_config": True,
    }


def apply_theme(app, theme_name):
    path = os.path.join("themes", f"{theme_name}.qss")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main():
    logger = setup_logger()
    settings = load_settings()
    logger.info(f"已加载配置：{settings}")

    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("CIW")
    app.setOrganizationName("Chinese tiger")

    apply_theme(app, settings.get("theme", "theme_male"))

    try:
        from office.environment import run_startup_self_check
        base = settings.get("llm_base_url", "http://localhost:1234/v1")
        result = run_startup_self_check(base)
        logger.info(result.get("summary", "自检完成"))
        for it in result.get("items") or []:
            logger.info(f"  [{it.get('status')}] {it.get('name')}: {it.get('detail')}")
    except Exception as e:
        logger.warning(f"启动自检异常：{e}")

    window = MainWindow(settings)
    window.setMinimumSize(1024, 680)
    window.show()
    logger.info("主窗口已显示，进入事件循环")

    exit_code = app.exec()
    logger.info(f"应用退出，退出码：{exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
