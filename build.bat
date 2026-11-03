@echo off
REM ExeLocker 打包脚本
REM 需要先安装依赖: pip install -r requirements.txt
REM 然后安装 pyinstaller: pip install pyinstaller

echo 正在清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist ExeLocker.spec del ExeLocker.spec

echo 正在打包为单文件 exe...
pyinstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name ExeLocker ^
    --add-data "acl_core.py;." ^
    --add-data "gui.py;." ^
    --hidden-import win32security ^
    --hidden-import win32file ^
    --hidden-import win32con ^
    --hidden-import ntsecuritycon ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import tkinter.filedialog ^
    --hidden-import tkinter.messagebox ^
    main.py

echo.
echo 打包完成！
echo 输出文件: dist\ExeLocker.exe
echo.
pause