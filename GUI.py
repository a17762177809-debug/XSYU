#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
西安石油大学校园网认证客户端 - 可视化界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import queue
import sys
import os
import json
# 判断配置文件是否存在
if not os.path.isfile("user_profile.json"): # 判断配置文件是否存在
    default_data = {
        "username": "",
        "password": ""
    }
    with open("user_profile.json", "w", encoding="utf-8") as f:
        json.dump(default_data, f, ensure_ascii=False, indent=4)

# 导入核心认证模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import Authentication as drcom


class DrcomGUI:
    """Dr.COM 认证客户端 GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("西安石油大学-校园网认证客户端")
        self.root.geometry("780x680")
        self.root.minsize(650, 550)
        self.root.resizable(True, True)

        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use("vista")
        self.style.configure("Red.TButton", foreground="red")
        self.style.configure("Green.TButton", foreground="green")

        # 运行状态
        self.running = False
        self.auth_thread = None
        self.log_queue = queue.Queue()

        # 构建界面
        self._build_ui()

        # 启动日志队列处理
        self._process_log_queue()

        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        """构建界面布局"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========== 配置区域 ==========
        config_frame = ttk.LabelFrame(main_frame, text="认证配置", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))

        # 网格布局
        for i in range(8):
            config_frame.columnconfigure(i if i < 2 else 0, weight=0 if i < 2 else 0)
        config_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(3, weight=1)
        config_frame.columnconfigure(5, weight=1)

        # 用户名
        ttk.Label(config_frame, text="用户名:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=3)
        self.username_var = tk.StringVar(value=drcom.username)
        ttk.Entry(config_frame, textvariable=self.username_var, width=18).grid(row=1, column=1, sticky=tk.EW, pady=3)

        # 密码
        ttk.Label(config_frame, text="密码:").grid(row=1, column=2, sticky=tk.W, padx=(10, 5), pady=3)
        self.password_var = tk.StringVar(value=drcom.password)
        ttk.Entry(config_frame, textvariable=self.password_var, width=18, show="*").grid(row=1, column=3, sticky=tk.EW, pady=3)

        # ========== 操作按钮区域 ==========
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.saves = ttk.Button(btn_frame, text="保存数据", command=self._save, width=16)
        self.saves.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.start_btn = ttk.Button(btn_frame, text="🚀 开始认证（自动保存）", command=self._start_auth, width=24)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_btn = ttk.Button(btn_frame, text="⏹ 停止", command=self._stop_auth, width=12, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.status_label = ttk.Label(btn_frame, text="⚪ 未连接", foreground="gray")
        self.status_label.pack(side=tk.LEFT, padx=(15, 0))

        # ========== 日志显示区域 ==========
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_area = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Consolas", 10),
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
            relief=tk.FLAT, borderwidth=1
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # 日志标签颜色配置
        self.log_area.tag_config("info", foreground="#6a9955")
        self.log_area.tag_config("warn", foreground="#dcdcaa")
        self.log_area.tag_config("error", foreground="#f44747")
        self.log_area.tag_config("success", foreground="#4ec9b0")
        self.log_area.tag_config("send", foreground="#569cd6")
        self.log_area.tag_config("recv", foreground="#ce9178")
        self.log_area.tag_config("bold", font=("Consolas", 10, "bold"))

        # 底部提示
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(
            footer_frame,
            text="仅供学习与交流，如果使用遇到问题，欢迎反馈邮箱a17762176301@163.com\n目前仅对西安石油大学校园网做了适配，其他学校不确定能否使用，欢迎反馈邮箱做更多适配",
            foreground="gray", font=("微软雅黑", 8)
        ).pack(side=tk.LEFT)

        # 清空日志按钮
        ttk.Button(footer_frame, text="清空日志", command=self._clear_log, width=10).pack(side=tk.RIGHT)

    def _log(self, message, tag=None):
        """添加日志到队列（线程安全）"""
        self.log_queue.put((message, tag))

    def _process_log_queue(self):
        """从队列读取日志并显示到界面"""
        try:
            while True:
                message, tag = self.log_queue.get_nowait()
                self.log_area.insert(tk.END, message + "\n", tag if tag else ())
                self.log_area.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self._process_log_queue)

    def _clear_log(self):
        """清空日志"""
        self.log_area.delete(1.0, tk.END)

    def _update_status(self, text, color):
        """更新状态显示"""
        self.status_label.config(text=text, foreground=color)

    def _save(self):
        """保存数据"""
        profile = {
            "username":self.username_var.get(),
            "password":self.password_var.get()
        }
        with open("user_profile.json", "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=4)

    def _apply_config(self):
        """将界面配置应用到核心模块"""
        drcom.username = self.username_var.get()
        drcom.password = self.password_var.get()

    def _redirect_log(self):
        """重定向 drcom 模块的 log 到 GUI"""
        original_log = drcom.log

        def gui_log(*args, **kwargs):
            s = " ".join(args)
            # 根据内容标记颜色
            tag = None
            if "send" in s.lower():
                tag = "send"
            elif "recv" in s.lower():
                tag = "recv"
            elif "login" in s.lower():
                tag = "success"

            # 添加时间戳
            timestamp = time.strftime("%H:%M:%S")
            self._log(f"[{timestamp}] {s}", tag)

            # 同时调用原始 log
            original_log(*args, **kwargs)

        drcom.log = gui_log


    def _start_auth(self):
        self._save # 保存
        """启动认证（在后台线程中运行）"""
        if self.running:
            return

        # 应用配置
        self._apply_config()
        # 重定向日志
        self._redirect_log()

        # 设置运行标志
        drcom.IS_TEST = True
        drcom.DEBUG = True

        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._update_status("🟡 认证中...", "orange")

        # 清空之前日志
        self._clear_log()
        self._log(f"[系统] Dr.COM 认证客户端启动", "bold")
        self._log(f"[系统] 服务器: {drcom.server}:61440", "info")
        self._log(f"[系统] 用户名: {drcom.username}", "info")
        self._log(f"[系统] MAC 地址: {hex(drcom.mac)[2:].upper()}", "info")
        self._log(f"[系统] 本机 IP: {drcom.host_ip}", "info")
        self._log(f"", None)

        # 后台线程
        self.auth_thread = threading.Thread(target=self._auth_worker, daemon=True)
        self.auth_thread.start()

    def _auth_worker(self):
        """认证工作线程"""
        try:
            self._log("[系统] 开始认证流程...", "bold")

            # 初始化 UDP socket
            drcom.init_socket()

            # 清空缓冲区
            drcom.empty_socket_buffer()

            # 执行登录
            self._log("[系统] 正在获取挑战...", None)
            package_tail = drcom.login(drcom.username, drcom.password, drcom.server)
            self._log("[系统] ✓ 登录成功！", "success")
            self.root.after(0, lambda: self._update_status("🟢 已连接（可能需要等待数十秒，使用期间请保留后台运行）", "green"))

            # 清空缓冲区并开始保活
            drcom.empty_socket_buffer()
            self._log("[系统] 开始保活通信...", None)

            drcom.keep_alive1(drcom.SALT, package_tail, drcom.password, drcom.server)
            self._log("[系统] ✓ 保活阶段 1 完成", "success")

            drcom.keep_alive2(drcom.SALT, package_tail, drcom.password, drcom.server)

        except drcom.ChallengeException:
            self._log("[错误] 挑战握手失败！请检查服务器地址。", "error")
            self.root.after(0, self._auth_failed)
        except Exception as e:
            self._log(f"[错误] {str(e)}", "error")
            self.root.after(0, self._auth_failed)

    def _auth_failed(self):
        """认证失败处理"""
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self._update_status("🔴 连接失败", "red")

    def _stop_auth(self):
        """停止认证"""
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self._update_status("⚪ 已停止", "gray")
        self._log("[系统] 用户手动停止", "warn")

        # 尝试发送注销包
        try:
            drcom.logout(
                drcom.username, drcom.password, drcom.server,
                drcom.mac, drcom.AUTH_INFO
            )
            self._log("[系统] 已发送注销请求", "info")
        except Exception:
            pass

    def _on_close(self):
        """窗口关闭事件"""
        self._stop_auth()
        self.root.destroy()


def main():
    root = tk.Tk()
    # 设置图标（如果有）
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    app = DrcomGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()