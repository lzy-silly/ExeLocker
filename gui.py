"""
ExeLocker GUI 界面
使用 tkinter 实现
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from acl_core import (
    lock_path, unlock_path, is_locked,
    lock_folder_recursive, unlock_folder_recursive
)


class ExeLockerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ExeLocker - 文件/文件夹权限锁定工具")
        self.geometry("600x400")
        self.minsize(550, 350)

        # 状态变量
        self.target_path = tk.StringVar()
        self.mode = tk.StringVar(value="file")  # "file" 或 "folder"
        self.status_text = tk.StringVar(value="就绪")
        self.locked_status = tk.StringVar(value="未检测")

        self._setup_ui()
        self._center_window()

    def _center_window(self):
        """窗口居中显示"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _setup_ui(self):
        # 主容器
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== 目标选择区域 =====
        target_frame = ttk.LabelFrame(main_frame, text="目标路径", padding="10")
        target_frame.pack(fill=tk.X, pady=(0, 15))

        # 路径输入框
        path_entry = ttk.Entry(target_frame, textvariable=self.target_path, font=("微软雅黑", 10))
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # 浏览按钮
        btn_frame = ttk.Frame(target_frame)
        btn_frame.pack(side=tk.LEFT)

        ttk.Button(btn_frame, text="选择文件", command=self._browse_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="选择文件夹", command=self._browse_folder).pack(side=tk.LEFT)

        # ===== 模式选择区域 =====
        mode_frame = ttk.LabelFrame(main_frame, text="锁定模式", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Radiobutton(
            mode_frame,
            text="文件模式（仅锁定选中的单个文件）",
            variable=self.mode,
            value="file",
            command=self._on_mode_change
        ).pack(anchor=tk.W, pady=2)

        ttk.Radiobutton(
            mode_frame,
            text="文件夹模式（递归锁定文件夹及其所有内容）",
            variable=self.mode,
            value="folder",
            command=self._on_mode_change
        ).pack(anchor=tk.W, pady=2)

        # ===== 操作按钮区域 =====
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 15))

        self.btn_lock = ttk.Button(
            action_frame,
            text="🔒 锁定（拒绝读/写/执行）",
            command=self._do_lock,
            style="Accent.TButton"
        )
        self.btn_lock.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.btn_unlock = ttk.Button(
            action_frame,
            text="🔓 解除锁定",
            command=self._do_unlock,
        )
        self.btn_unlock.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ===== 状态显示区域 =====
        status_frame = ttk.LabelFrame(main_frame, text="状态", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True)

        # 当前路径状态
        info_frame = ttk.Frame(status_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_frame, text="目标状态:").pack(side=tk.LEFT)
        self.lbl_locked = ttk.Label(info_frame, textvariable=self.locked_status, foreground="blue", font=("微软雅黑", 10, "bold"))
        self.lbl_locked.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Separator(status_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # 操作日志
        ttk.Label(status_frame, text="操作日志:").pack(anchor=tk.W)

        log_frame = ttk.Frame(status_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=8, font=("Consolas", 9), state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # 底部状态栏
        self.status_bar = ttk.Label(self, textvariable=self.status_text, relief=tk.SUNKEN, anchor=tk.W, padding="5 2")
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # 初始检查
        self._check_current_status()

    def _on_mode_change(self):
        """模式切换时清空路径并重新检查"""
        self.target_path.set("")
        self._check_current_status()

    def _browse_file(self):
        """选择文件"""
        path = filedialog.askopenfilename(
            title="选择要锁定的 EXE 文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if path:
            self.target_path.set(path)
            self.mode.set("file")
            self._check_current_status()

    def _browse_folder(self):
        """选择文件夹"""
        path = filedialog.askdirectory(title="选择要锁定的文件夹")
        if path:
            self.target_path.set(path)
            self.mode.set("folder")
            self._check_current_status()

    def _check_current_status(self):
        """检查当前目标的锁定状态"""
        path = self.target_path.get().strip()
        if not path or not os.path.exists(path):
            self.locked_status.set("路径不存在")
            self.lbl_locked.config(foreground="gray")
            return

        try:
            locked = is_locked(path)
            if locked:
                self.locked_status.set("🔒 已锁定")
                self.lbl_locked.config(foreground="red")
            else:
                self.locked_status.set("🔓 未锁定")
                self.lbl_locked.config(foreground="green")
        except Exception as e:
            self.locked_status.set(f"检查失败: {e}")
            self.lbl_locked.config(foreground="orange")

    def _log(self, message: str):
        """添加日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _set_status(self, message: str):
        """设置状态栏"""
        self.status_text.set(message)
        self.update_idletasks()

    def _set_buttons_enabled(self, enabled: bool):
        """启用/禁用按钮"""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.btn_lock.config(state=state)
        self.btn_unlock.config(state=state)

    def _do_lock(self):
        """执行锁定操作"""
        path = self.target_path.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择文件或文件夹")
            return

        if not os.path.exists(path):
            messagebox.showerror("错误", "路径不存在")
            return

        self._set_buttons_enabled(False)
        self._set_status("正在锁定...")
        self._log(f"开始锁定: {path}")

        # 在后台线程执行
        threading.Thread(target=self._lock_worker, args=(path,), daemon=True).start()

    def _lock_worker(self, path: str):
        """锁定工作线程"""
        try:
            if self.mode.get() == "file":
                success = lock_path(path)
                if success:
                    self.after(0, lambda: self._on_lock_success(path, "文件"))
                else:
                    self.after(0, lambda: self._on_lock_failed(path, "文件", "锁定失败，请检查权限"))
            else:
                success_count, failed_count = lock_folder_recursive(path)
                self.after(0, lambda: self._on_folder_lock_done(path, success_count, failed_count))
        except Exception as e:
            self.after(0, lambda: self._on_lock_failed(path, "目标", str(e)))

    def _on_lock_success(self, path: str, type_name: str):
        self._log(f"✅ {type_name}锁定成功: {path}")
        self._check_current_status()
        self._set_status("锁定成功")
        self._set_buttons_enabled(True)
        messagebox.showinfo("成功", f"{type_name}已锁定\n\n其他程序将无法读取、写入、执行此{type_name}")

    def _on_folder_lock_done(self, path: str, success: int, failed: int):
        if failed == 0:
            self._log(f"✅ 文件夹递归锁定成功: {path} (共 {success} 项)")
            self._set_status("文件夹锁定成功")
            messagebox.showinfo("成功", f"文件夹及其所有内容已锁定\n成功: {success} 项")
        else:
            self._log(f"⚠️ 文件夹锁定部分失败: {path} (成功: {success}, 失败: {failed})")
            self._set_status("锁定完成（部分失败）")
            messagebox.showwarning("部分成功", f"文件夹锁定完成\n成功: {success} 项\n失败: {failed} 项\n\n失败通常是因为文件正在被占用或权限不足")
        self._check_current_status()
        self._set_buttons_enabled(True)

    def _on_lock_failed(self, path: str, type_name: str, error: str):
        self._log(f"❌ {type_name}锁定失败: {error}")
        self._set_status("锁定失败")
        self._set_buttons_enabled(True)
        messagebox.showerror("失败", f"{type_name}锁定失败:\n{error}")

    def _do_unlock(self):
        """执行解锁操作"""
        path = self.target_path.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择文件或文件夹")
            return

        if not os.path.exists(path):
            messagebox.showerror("错误", "路径不存在")
            return

        self._set_buttons_enabled(False)
        self._set_status("正在解锁...")
        self._log(f"开始解锁: {path}")

        threading.Thread(target=self._unlock_worker, args=(path,), daemon=True).start()

    def _unlock_worker(self, path: str):
        """解锁工作线程"""
        try:
            if self.mode.get() == "file":
                success = unlock_path(path)
                if success:
                    self.after(0, lambda: self._on_unlock_success(path, "文件"))
                else:
                    self.after(0, lambda: self._on_unlock_failed(path, "文件", "解锁失败"))
            else:
                success_count, failed_count = unlock_folder_recursive(path)
                self.after(0, lambda: self._on_folder_unlock_done(path, success_count, failed_count))
        except Exception as e:
            self.after(0, lambda: self._on_unlock_failed(path, "目标", str(e)))

    def _on_unlock_success(self, path: str, type_name: str):
        self._log(f"✅ {type_name}解锁成功: {path}")
        self._check_current_status()
        self._set_status("解锁成功")
        self._set_buttons_enabled(True)
        messagebox.showinfo("成功", f"{type_name}已解除锁定\n恢复正常读写执行权限")

    def _on_folder_unlock_done(self, path: str, success: int, failed: int):
        if failed == 0:
            self._log(f"✅ 文件夹递归解锁成功: {path} (共 {success} 项)")
            self._set_status("文件夹解锁成功")
            messagebox.showinfo("成功", f"文件夹及其所有内容已解锁\n成功: {success} 项")
        else:
            self._log(f"⚠️ 文件夹解锁部分失败: {path} (成功: {success}, 失败: {failed})")
            self._set_status("解锁完成（部分失败）")
            messagebox.showwarning("部分成功", f"文件夹解锁完成\n成功: {success} 项\n失败: {failed} 项")
        self._check_current_status()
        self._set_buttons_enabled(True)

    def _on_unlock_failed(self, path: str, type_name: str, error: str):
        self._log(f"❌ {type_name}解锁失败: {error}")
        self._set_status("解锁失败")
        self._set_buttons_enabled(True)
        messagebox.showerror("失败", f"{type_name}解锁失败:\n{error}")


if __name__ == "__main__":
    app = ExeLockerApp()
    app.mainloop()