import itertools
import json
import os
import random
import time
from datetime import date, datetime, timedelta
from datetime import time as dt_time

import openpyxl
import pyautogui
import pyperclip
from PySide6.QtCore import QObject, Signal

from app.services.chatbot import ChatBot


class TaskRunner(QObject):
    task_completed = Signal(str, bool, str)
    task_progress = Signal(str, int, int)
    task_stopped = Signal(str)
    log_message = Signal(str, str)  # 新增日志信号

    def __init__(
        self,
        task_name,
        steps,
        auto_skip_image_timeout=False,
        timeout=10,
        instant_click=False,
        move_duration=0.1,
        parent=None,
    ):
        super().__init__()
        self.task_name = task_name
        self.steps = steps
        self.is_running = False
        self.current_step = 0
        self.repeat_count = 0
        self.max_repeat = 1  # 默认执行1次
        self.repeat_interval = 0

        self.auto_skip_image_timeout = auto_skip_image_timeout
        self.timeout = timeout  # 用户设置的超时时间

        self.instant_click = instant_click  # 是否跳过移动动画
        self.default_move_duration = move_duration  # 全局移动动画时长

        self._excel_cycle = None
        self._excel_cache = {}  # 路径->(wb, ws, rows)

        self.parent = parent

    def set_repeat_interval(self, interval_minutes):
        """
        设置重复间隔时间

        Args:
            interval_minutes (int): 间隔时间（分钟）
        """
        self.repeat_interval = interval_minutes

    def set_repeat_count(self, count):
        self.max_repeat = count

    def execute_mouse_click(self, params):
        """
        执行鼠标点击操作
        支持图片识别点击和坐标直接点击两种模式
        """
        use_image = params.get("use_image", True)
        use_coordinates = params.get("use_coordinates", False)

        # 检查参数有效性
        if use_image and use_coordinates:
            if self.auto_skip_image_timeout:
                self.log_message.emit(
                    self.task_name, "⚠️ 图片和坐标模式不能同时启用，跳过此步骤"
                )
                return
            else:
                raise ValueError("图片和坐标模式不能同时启用")

        if not use_image and not use_coordinates:
            if self.auto_skip_image_timeout:
                self.log_message.emit(
                    self.task_name, "⚠️ 未启用图片模式也未启用坐标模式，跳过此步骤"
                )
                return
            else:
                raise ValueError("必须启用图片模式或坐标模式")

        # 获取通用参数
        click_type = params.get("click_type", "左键单击")
        offset_x = params.get("offset_x", 0)
        offset_y = params.get("offset_y", 0)
        move_duration = params.get("move_duration", self.default_move_duration)

        # 点击类型映射
        click_map = {
            "左键单击": pyautogui.click,
            "左键双击": pyautogui.doubleClick,
            "右键单击": pyautogui.rightClick,
            "中键单击": pyautogui.middleClick,
        }

        if click_type not in click_map:
            if self.auto_skip_image_timeout:
                self.log_message.emit(
                    self.task_name, f"⚠️ 不支持的点击类型: {click_type}，跳过"
                )
                return
            else:
                raise ValueError(f"不支持的 click_type: {click_type}")

        # 模式1: 使用坐标直接点击
        if use_coordinates:
            x_coordinate = params.get("x_coordinate", 0)
            y_coordinate = params.get("y_coordinate", 0)

            if x_coordinate == 0 and y_coordinate == 0:
                if self.auto_skip_image_timeout:
                    self.log_message.emit(self.task_name, "⚠️ 坐标不能都为0，跳过此步骤")
                    return
                else:
                    raise ValueError("坐标不能都为0")

            target_x = x_coordinate + offset_x
            target_y = y_coordinate + offset_y

            self.log_message.emit(
                self.task_name,
                f"📌 使用坐标模式: ({x_coordinate}, {y_coordinate}) + 偏移({offset_x}, {offset_y}) = 目标({target_x}, {target_y})",
            )

            # 移动鼠标
            if not self.instant_click:
                try:
                    pyautogui.moveTo(target_x, target_y, duration=move_duration)
                except Exception as e:
                    if self.auto_skip_image_timeout:
                        self.log_message.emit(
                            self.task_name, f"⚠️ 鼠标移动失败，跳过: {e}"
                        )
                        return
                    raise
            else:
                pyautogui.moveTo(target_x, target_y, duration=0)  # 瞬移

            # 执行点击
            click_map[click_type](target_x, target_y)
            self.log_message.emit(self.task_name, f"✅ 已完成坐标 {click_type} 操作")
            return

        # 模式2: 使用图片识别点击
        image_path = params.get("image_path", "")
        scan_direction = params.get("scan_direction", "默认")
        confidence = params.get("confidence", 0.8)
        timeout = params.get("timeout", self.timeout)

        if not image_path:
            if self.auto_skip_image_timeout:
                self.log_message.emit(self.task_name, "⚠️ 图片路径为空，跳过此步骤")
                return
            else:
                raise ValueError("image_path 不能为空")

        if not os.path.exists(image_path):
            if self.auto_skip_image_timeout:
                self.log_message.emit(
                    self.task_name, f"⚠️ 图片文件不存在: {image_path}，跳过此步骤"
                )
                return
            else:
                raise FileNotFoundError(f"图片文件不存在: {image_path}")

        self.log_message.emit(
            self.task_name, f"🔍 开始定位图片: {os.path.basename(image_path)}"
        )
        self.log_message.emit(
            self.task_name,
            f"📊 扫描方向: {scan_direction}, 置信度: {confidence}, 超时: {timeout}s",
        )

        def find_image_center():
            """默认查找图片中心"""
            start = time.time()
            while True:
                pos = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
                if pos:
                    return pos
                if time.time() - start > timeout:
                    return None
                time.sleep(0.2)

        def find_image_center_with_direction():
            """
            按指定方向返回第一个匹配图的中心坐标。
            direction: "从左到右" | "从右到左" | "从上到下" | "从下到上"
            """
            start = time.time()
            while True:
                # 1. 拿到所有匹配框
                boxes = list(
                    pyautogui.locateAllOnScreen(image_path, confidence=confidence)
                )
                if boxes:
                    # 2. 按方向排序
                    if scan_direction == "从左到右":
                        boxes.sort(key=lambda b: b.left)  # left 升序
                    elif scan_direction == "从右到左":
                        boxes.sort(key=lambda b: -(b.left + b.width))  # 最右在前
                    elif scan_direction == "从上到下":
                        boxes.sort(key=lambda b: b.top)  # top 升序
                    elif scan_direction == "从下到上":
                        boxes.sort(key=lambda b: -(b.top + b.height))  # 最下在前
                    else:
                        # 防呆，回到默认（最左上）
                        boxes.sort(key=lambda b: (b.top, b.left))

                    # 3. 取第一个框的中心
                    target = boxes[0]
                    x, y = pyautogui.center(target)
                    return (x, y)
                # 4. 超时判定
                if time.time() - start > timeout:
                    return None
                time.sleep(0.2)

        # 执行图片查找
        if scan_direction == "默认":
            center = find_image_center()
        else:
            center = find_image_center_with_direction()

        if center is None:
            if self.auto_skip_image_timeout:
                self.log_message.emit(
                    self.task_name,
                    f"⚠️ 在 {timeout}s 内未找到图片: {os.path.basename(image_path)}，自动跳过",
                )
                return  # ✅ 跳过，不抛异常
            else:
                raise RuntimeError(f"在 {timeout}s 内未找到图片: {image_path}")

        # 计算目标坐标（考虑偏移）
        if scan_direction == "默认":
            target_x = center.x + offset_x
            target_y = center.y + offset_y
        else:
            target_x = center[0] + offset_x
            target_y = center[1] + offset_y

        self.log_message.emit(
            self.task_name,
            f"🎯 找到图片位置: ({center.x if scan_direction == '默认' else center[0]}, {center.y if scan_direction == '默认' else center[1]}) + 偏移({offset_x}, {offset_y}) = 目标({target_x}, {target_y})",
        )

        # 移动鼠标
        if not self.instant_click:
            try:
                pyautogui.moveTo(target_x, target_y, duration=move_duration)
            except Exception as e:
                if self.auto_skip_image_timeout:
                    self.log_message.emit(self.task_name, f"⚠️ 鼠标移动失败，跳过: {e}")
                    return
                raise
        else:
            pyautogui.moveTo(target_x, target_y, duration=0)  # 瞬移

        # 执行点击
        click_map[click_type](target_x, target_y)
        self.log_message.emit(self.task_name, f"✅ 已完成图片 {click_type} 操作")

    def run(self):
        self.is_running = True
        self.current_step = 0
        total_steps = len(self.steps)
        self.repeat_count = 0

        self.log_message.emit(
            self.task_name,
            f"🚀 开始执行任务: {self.task_name}, 共 {total_steps} 个步骤",
        )

        try:
            while self.repeat_count < self.max_repeat and self.is_running:
                self.repeat_count += 1
                if self.max_repeat > 1:
                    self.log_message.emit(
                        self.task_name,
                        f"🔄 第 {self.repeat_count}/{self.max_repeat} 次执行",
                    )
                    if self.parent:
                        self.parent.statusBar().showMessage(
                            f"【{self.task_name}】第 {self.repeat_count}/{self.max_repeat} 次执行"
                        )
                for i, step in enumerate(self.steps):
                    if not self.is_running:
                        self.log_message.emit(self.task_name, "⏹️ 任务被中断")
                        break

                    self.current_step = i
                    self.task_progress.emit(self.task_name, i + 1, total_steps)

                    # 执行步骤
                    step_type = step.get("type", "")
                    params = step.get("params", {})
                    delay = step.get("delay", 0)

                    # 简化日志显示
                    if step_type == "鼠标点击":
                        use_image = params.get("use_image", True)
                        use_coordinates = params.get("use_coordinates", False)

                        self.log_message.emit(
                            self.task_name,
                            f"📝 执行步骤 {i + 1}/{total_steps}: {step_type}",
                        )

                        if use_image:
                            image_name = (
                                os.path.basename(params.get("image_path", ""))
                                if params.get("image_path")
                                else "未设置"
                            )
                            click_type = params.get("click_type", "左键单击")
                            scan_direction = params.get("scan_direction", "默认")
                            offset_x = params.get("offset_x", 0)
                            offset_y = params.get("offset_y", 0)

                            log_text = f"🖼️ 图片模式: {image_name}, 点击: {click_type}, 方向: {scan_direction}"
                            if offset_x != 0 or offset_y != 0:
                                log_text += f", 偏移: ({offset_x}, {offset_y})"
                            self.log_message.emit(self.task_name, log_text)

                        elif use_coordinates:
                            x_coord = params.get("x_coordinate", 0)
                            y_coord = params.get("y_coordinate", 0)
                            click_type = params.get("click_type", "左键单击")
                            offset_x = params.get("offset_x", 0)
                            offset_y = params.get("offset_y", 0)

                            log_text = f"📍 坐标模式: ({x_coord}, {y_coord}), 点击: {click_type}"
                            if offset_x != 0 or offset_y != 0:
                                log_text += f", 偏移: ({offset_x}, {offset_y})"
                            self.log_message.emit(self.task_name, log_text)

                        else:
                            self.log_message.emit(
                                self.task_name, "⚠️ 未启用图片或坐标模式"
                            )
                    else:
                        self.log_message.emit(
                            self.task_name,
                            f"📝 执行步骤 {i + 1}/{total_steps}: {step_type}",
                        )
                        self.log_message.emit(
                            self.task_name,
                            f"⚙️ 参数: {json.dumps(params, ensure_ascii=False)}",
                        )
                    if step_type == "鼠标点击":
                        self.execute_mouse_click(params)
                    elif step_type == "文本输入":
                        self.execute_keyboard_input(params)
                    elif step_type == "等待":
                        self.execute_wait(params)
                    elif step_type == "截图":
                        self.execute_screenshot(params)
                    elif step_type == "拖拽":
                        self.execute_drag(params)
                    elif step_type == "鼠标滚轮":
                        self.execute_mouse_scroll(params)
                    elif step_type == "键盘热键":
                        self.execute_hotkey(params)
                    elif step_type == "AI 自动回复":
                        self.execute_ai_reply(params)
                    else:
                        self.log_message.emit(
                            self.task_name, f"⚠️ 未知步骤类型: {step_type}"
                        )

                    # 步骤间延时
                    if delay > 0:
                        self.log_message.emit(self.task_name, f"⏱️ 步骤延时: {delay}秒")
                        time.sleep(delay)

                # 检查是否需要等待下次重复执行
                if (
                    self.repeat_count < self.max_repeat
                    and self.is_running
                    and self.repeat_interval > 0
                ):
                    wait_seconds = self.repeat_interval * 60  # 转换为秒
                    countdown_start = wait_seconds - 10  # 提前10秒开始倒计时
                    self.log_message.emit(
                        self.task_name, f"⏳ 间隔等待: {self.repeat_interval}分钟"
                    )
                    if self.parent:
                        self.parent.statusBar().showMessage(
                            f"【{self.task_name}】⏳ 间隔等待: {self.repeat_interval}分钟"
                        )
                    # 分段等待，每秒检查一次是否停止
                    for _ in range(int(countdown_start)):
                        if not self.is_running:
                            self.log_message.emit(self.task_name, "⏹️ 任务被中断")
                            break
                        time.sleep(1)
                    # 开始10秒倒计时
                    countdown_seconds = 10
                    while countdown_seconds > 0 and self.is_running:
                        current_time = time.strftime("%H:%M:%S")  # 获取当前时间
                        if self.parent:
                            self.parent.statusBar().showMessage(
                                f"[{current_time}]【{self.task_name}】⏳ 倒计时: {countdown_seconds} 秒"
                            )
                        time.sleep(1)
                        countdown_seconds -= 1
                if not self.is_running:
                    break
            success = self.is_running
            message = "✅ 任务完成" if success else "⏹️ 任务被中断"
            self.log_message.emit(self.task_name, message)
            if self.parent:
                self.parent.statusBar().showMessage(message)
            self.task_completed.emit(self.task_name, success, message)
        except Exception as e:
            error_msg = f"❌ 任务执行出错: {str(e)}"
            self.log_message.emit(self.task_name, error_msg)
            self.task_completed.emit(self.task_name, False, error_msg)
        finally:
            self.is_running = False

    def stop(self):
        self.log_message.emit(self.task_name, "⏹️ 停止任务")
        self.is_running = False
        self.task_stopped.emit(self.task_name)

    def chinese_qixi(self, year: int) -> date:
        """
        计算指定年份的七夕节（农历七月初七）的公历日期
        使用近似算法，误差在±1天内

        Args:
            year: 要计算的年份

        Returns:
            该年份七夕节的公历日期
        """
        # 扩展的年份对照表（2000-2030年）
        table = {
            2000: date(2000, 8, 6),
            2001: date(2001, 8, 25),
            2002: date(2002, 8, 15),
            2003: date(2003, 8, 4),
            2004: date(2004, 8, 22),
            2005: date(2005, 8, 11),
            2006: date(2006, 7, 31),
            2007: date(2007, 8, 19),
            2008: date(2008, 8, 7),
            2009: date(2009, 8, 26),
            2010: date(2010, 8, 16),
            2011: date(2011, 8, 6),
            2012: date(2012, 8, 23),
            2013: date(2013, 8, 13),
            2014: date(2014, 8, 2),
            2015: date(2015, 8, 20),
            2016: date(2016, 8, 9),
            2017: date(2017, 8, 28),
            2018: date(2018, 8, 17),
            2019: date(2019, 8, 7),
            2020: date(2020, 8, 25),
            2021: date(2021, 8, 14),
            2022: date(2022, 8, 4),
            2023: date(2023, 8, 22),
            2024: date(2024, 8, 10),
            2025: date(2025, 8, 1),
            2026: date(2026, 8, 19),
            2027: date(2027, 8, 8),
            2028: date(2028, 7, 28),
            2029: date(2029, 8, 16),
            2030: date(2030, 8, 5),
        }

        # 如果在已知年份范围内，直接返回表中日期
        if year in table:
            return table[year]

        # 对于表外的年份，使用近似算法计算
        # 基础年份选择2023年，七夕日期为8月22日
        base_year = 2023
        base_date = date(base_year, 8, 22)

        # 计算与基础年份的差异（考虑农历年的平均长度）
        year_diff = year - base_year
        # 农历年平均长度约为29.53天×12个月 = 354.36天
        days_diff = round(year_diff * 354.36 - year_diff * 365.25)

        # 计算预估日期
        estimated_date = base_date + timedelta(days=days_diff)

        # 调整到8月附近（七夕通常在7月底到8月底之间）
        if estimated_date.month < 7:
            estimated_date += timedelta(days=30)
        elif estimated_date.month > 9:
            estimated_date -= timedelta(days=30)

        return estimated_date

    def execute_mouse_scroll(self, params):
        direction = params.get("direction", "向下滚动")
        clicks = params.get("clicks", 3)

        self.log_message.emit(
            self.task_name, f"🖱 鼠标滚轮 {direction} {clicks} 格（当前位置）"
        )

        try:
            scroll_amount = clicks * 120 if direction == "向下滚动" else -clicks * 120
            pyautogui.scroll(scroll_amount)
            self.log_message.emit(self.task_name, "✅ 滚轮完成")
        except Exception as e:
            self.log_message.emit(self.task_name, f"❌ 滚轮出错: {str(e)}")
            raise

    def execute_ai_reply(self, params):
        try:
            # 获取剪贴板内容作为消息
            clipboard_content = pyperclip.paste()
            if not clipboard_content:
                self.log_message.emit(self.task_name, "⚠️ 剪贴板为空，无法进行 AI 回复")
                return

            # 获取参数
            provider = params.get("provider", "kimi")
            system_prompt = params.get("system_prompt", "")
            use_history = params.get("use_history", True)
            stream = params.get("stream", False)

            # 初始化 ChatBot
            bot = ChatBot(provider=provider, token_json_path="./config/token.json")

            # 发送消息并获取回复
            reply = bot.reply(
                message=clipboard_content,
                system=system_prompt,
                use_history=use_history,
                stream=stream,
            )

            # 将回复复制到剪贴板
            pyperclip.copy(reply)

            self.log_message.emit(self.task_name, f"✅ AI 回复成功: {reply}")
        except Exception as e:
            self.log_message.emit(self.task_name, f"❌ AI 回复出错: {str(e)}")
            raise

    def execute_hotkey(self, params):
        hotkey = params.get("hotkey", "")
        delay = params.get("delay_ms", 100)

        if not hotkey:
            self.log_message.emit(self.task_name, "⚠️ 未设置热键")
            return

        self.log_message.emit(self.task_name, f"⌨ 热键 {hotkey} 执行")

        try:
            # 解析热键字符串
            keys = hotkey.lower().split("+")

            # 转换为pyautogui可识别的键名
            pyautogui_keys = []
            for key in keys:
                # 处理特殊键名映射
                key_map = {
                    "ctrl": "ctrl",
                    "alt": "alt",
                    "shift": "shift",
                    "win": "win",
                    "cmd": "cmd",
                    "enter": "enter",
                    "return": "enter",
                    "space": "space",
                    "tab": "tab",
                    "esc": "esc",
                    "escape": "esc",
                    "backspace": "backspace",
                    "delete": "delete",
                    "insert": "insert",
                    "home": "home",
                    "end": "end",
                    "pageup": "pageup",
                    "pagedown": "pagedown",
                    "up": "up",
                    "down": "down",
                    "left": "left",
                    "right": "right",
                    "capslock": "capslock",
                    "numlock": "numlock",
                    "scrolllock": "scrolllock",
                }

                if key in key_map:
                    pyautogui_keys.append(key_map[key])
                else:
                    pyautogui_keys.append(key)

            # 执行热键
            if len(pyautogui_keys) == 1:
                pyautogui.press(pyautogui_keys[0])
            else:
                pyautogui.hotkey(*pyautogui_keys)

            if delay > 0:
                time.sleep(delay / 1000.0)
            self.log_message.emit(self.task_name, "✅ 热键完成")
        except Exception as e:
            self.log_message.emit(self.task_name, f"❌ 热键出错: {str(e)}")
            raise

    def execute_keyboard_input(self, params):
        # 1. 纯文本优先
        text = params.get("text", "").strip()
        if not text or "未来也要一起闪耀" in text:
            # 2. 动态纪念日文案
            love_str = params.get("love_date")
            if love_str:
                love_dt = datetime.fromisoformat(love_str)
                today = date.today()
                today_1314 = datetime.combine(today, dt_time(13, 14))

                delta = today_1314 - love_dt
                days, sec = delta.days, delta.seconds
                hours, rem = divmod(sec, 3600)
                minutes, secs = divmod(rem, 60)
                duration = f"{days}天{hours}时{minutes}分{secs}秒"

                year_start = datetime(today.year, 1, 1, 13, 14)
                count = (today_1314 - year_start).days + 1

                # 特殊节日
                is_xmas = (love_dt.month, love_dt.day) == (12, 25)
                special = ""
                if today == date(today.year, 12, 25):
                    special = "\n圣诞快乐，Merry Christmas！"
                elif today == date(today.year, 2, 14):
                    special = "\n情人节快乐！"
                elif today == self.chinese_qixi(today.year):
                    special = "\n七夕快乐，鹊桥相会！"

                today_str = today.strftime("%Y年%m月%d日")
                if is_xmas:
                    text = (
                        f"宝宝，今天是{today_str}第{count}个1314，我们已相恋{duration}，"
                        f"从圣诞夜一直走到今天，未来也要一起闪耀！🎄❤{special}"
                    )
                else:
                    text = (
                        f"宝宝，今天是{today_str}第{count}个1314，"
                        f"我们已经相恋了{duration}，爱你❤{special}"
                    )
            else:
                # 3. 否则从 Excel 取
                excel_path = params.get("excel_path", "").strip()
                if not excel_path or not os.path.isfile(excel_path):
                    raise FileNotFoundError("未指定或找不到 Excel 文件")

                sheet_id = params.get("sheet", "0")
                col_index = int(params.get("col", 0))
                mode = params.get("mode", "顺序")

                # === 关键：使用 (文件, 表, 列) 作为缓存键 ===
                cache_key = (excel_path, str(sheet_id), col_index)

                # 1. 检查是否已缓存 workbook（避免重复打开）
                wb_cache_key = excel_path
                if wb_cache_key not in self._excel_cache:
                    wb = openpyxl.load_workbook(excel_path, data_only=True)
                    try:
                        ws = (
                            wb[int(sheet_id)]
                            if str(sheet_id).isdigit()
                            else wb[sheet_id]
                        )
                    except Exception:
                        ws = wb.worksheets[0]
                    rows = list(ws.iter_rows(values_only=True))
                    self._excel_cache[wb_cache_key] = (wb, ws, rows)
                _, _, rows = self._excel_cache[wb_cache_key]

                if not rows:
                    raise ValueError("Excel 表无数据")

                cells = [
                    row[col_index]
                    for row in rows
                    if len(row) > col_index and row[col_index] is not None
                ]
                if not cells:
                    raise ValueError("指定列为空")

                # === 2. 使用 cache_key 管理 cycle ===
                if mode == "顺序":
                    # 初始化类变量（如果还没创建）
                    if not hasattr(self, "_excel_cycle_dict"):
                        self._excel_cycle_dict = {}

                    # 如果该 (文件, 表, 列) 组合没有 cycle，创建一个
                    if cache_key not in self._excel_cycle_dict:
                        self._excel_cycle_dict[cache_key] = itertools.cycle(cells)

                    text = next(self._excel_cycle_dict[cache_key])

                else:  # 随机
                    text = random.choice(cells)
        self._send_text(str(text))

    def _send_text(self, text: str):
        """真正执行文本输入的公共逻辑"""
        self.log_message.emit(self.task_name, f"⌨️ 文本输入: '{text}'")
        try:
            import pyperclip

            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)
            self.log_message.emit(self.task_name, "✅ 文本输入完成")
        except Exception as e:
            self.log_message.emit(self.task_name, f"❌ 文本输入出错: {str(e)}")
            raise

    def execute_wait(self, params):
        seconds = params.get("seconds", 0)
        if seconds > 0:
            self.log_message.emit(self.task_name, f"⏱️ 等待 {seconds}秒")
            try:
                time.sleep(seconds)
            except Exception as e:
                self.log_message.emit(self.task_name, f"❌ 等待操作出错: {str(e)}")
                raise

    def execute_screenshot(self, params):
        save_path = params.get("save_path", "")
        region = params.get("region", None)

        self.log_message.emit(self.task_name, f"📸 截图保存到: {save_path}")

        try:
            if region:
                x, y, width, height = region
                self.log_message.emit(
                    self.task_name,
                    f"🖼️ 截图区域: x={x}, y={y}, width={width}, height={height}",
                )
                screenshot = pyautogui.screenshot(region=(x, y, width, height))
            else:
                self.log_message.emit(self.task_name, "🖼️ 全屏截图")
                screenshot = pyautogui.screenshot()

            screenshot.save(save_path)
            self.log_message.emit(self.task_name, "✅ 截图保存成功")
        except Exception as e:
            self.log_message.emit(self.task_name, f"❌ 截图操作出错: {str(e)}")
            raise

    def execute_drag(self, params):
        use_image = params.get("use_image", True)
        duration = params.get("duration", 1.0)

        if use_image:
            # 使用图像识别定位起始点
            image_path = params.get("image_path", "")
            offset_x = params.get("offset_x", 0)
            offset_y = params.get("offset_y", 0)
            drag_x = params.get("drag_x", 0)  # 相对拖拽距离
            drag_y = params.get("drag_y", 100)  # 默认向下拖拽100像素
            confidence = params.get("confidence", 0.8)
            timeout = self.timeout

            if not image_path:
                raise ValueError("图像路径不能为空")

            def find_image_center():
                start = time.time()
                while True:
                    pos = pyautogui.locateCenterOnScreen(
                        image_path, confidence=confidence
                    )
                    if pos:
                        return pos
                    if time.time() - start > timeout:
                        return None
                    time.sleep(0.2)

            center = find_image_center()
            if center is None:
                if self.auto_skip_image_timeout:
                    self.log_message.emit(
                        self.task_name,
                        f"⚠️ 在 {timeout}s 内未找到图片: {os.path.basename(image_path)}，自动跳过",
                    )
                    return  # ✅ 跳过，不抛异常
                else:
                    raise RuntimeError(f"在 {timeout}s 内未找到图片: {image_path}")

            start_x = center.x + offset_x
            start_y = center.y + offset_y
            end_x = start_x + drag_x
            end_y = start_y + drag_y

        else:
            # 使用直接坐标
            start_x = params.get("start_x", 0)
            start_y = params.get("start_y", 0)
            end_x = params.get("end_x", 0)
            end_y = params.get("end_y", 0)

        self.log_message.emit(
            self.task_name,
            f"↔️ 从 ({start_x}, {start_y}) 拖拽到 ({end_x}, {end_y}), 时长: {duration}秒",
        )

        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=duration, button="left")
            self.log_message.emit(self.task_name, "✅ 拖拽操作完成")
        except Exception as e:
            self.log_message.emit(self.task_name, f"❌ 拖拽操作出错: {str(e)}")
            raise
