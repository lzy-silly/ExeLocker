"""
ExeLocker 主程序入口
包含 UAC 自动提升和 GUI 启动
"""

import sys
import os
import ctypes
from pathlib import Path


def is_admin() -> bool:
    """检查当前是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin() -> None:
    """请求 UAC 提升并重启程序"""
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])

    # 使用 ShellExecuteEx 请求管理员权限
    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        f'"{script}" {params}',
        None,
        1  # SW_SHOWNORMAL
    )
    sys.exit(0)


def main():
    # 必须以管理员权限运行
    if not is_admin():
        print("请求管理员权限...")
        run_as_admin()
        return

    # 导入并启动 GUI
    from gui import ExeLockerApp
    app = ExeLockerApp()
    app.mainloop()


if __name__ == "__main__":
    main()