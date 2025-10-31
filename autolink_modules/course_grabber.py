"""
抢课模块 - 自动化抢课功能

功能：
- 定时抢课
- 多课程并发抢课
- 抢课成功/失败通知
- 课程配置管理
"""
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from datetime import datetime
import json
from pathlib import Path


class CourseConfig:
    """课程配置类"""
    def __init__(self, course_id=None, course_name="", teacher_name="", 
                 priority=1, start_time=None, notes=""):
        self.course_id = course_id
        self.course_name = course_name
        self.teacher_name = teacher_name
        self.priority = priority  # 优先级 1-10，数字越小优先级越高
        self.start_time = start_time  # 开始抢课的时间
        self.notes = notes
        self.status = "pending"  # pending, success, failed
        
    def to_dict(self):
        return {
            "course_id": self.course_id,
            "course_name": self.course_name,
            "teacher_name": self.teacher_name,
            "priority": self.priority,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "notes": self.notes,
            "status": self.status
        }
    
    @staticmethod
    def from_dict(data):
        config = CourseConfig(
            course_id=data.get("course_id"),
            course_name=data.get("course_name", ""),
            teacher_name=data.get("teacher_name", ""),
            priority=data.get("priority", 1),
            notes=data.get("notes", "")
        )
        start_time_str = data.get("start_time")
        if start_time_str:
            config.start_time = datetime.fromisoformat(start_time_str)
        config.status = data.get("status", "pending")
        return config


class CourseGrabber(QThread):
    """抢课工作线程"""
    
    # 信号定义
    course_selected = pyqtSignal(str, str)  # (course_name, status)
    log_message = pyqtSignal(str)  # 日志消息
    progress_update = pyqtSignal(int, int)  # (current, total)
    
    def __init__(self, webview, courses: list[CourseConfig], config: dict):
        super().__init__()
        self.webview = webview
        self.courses = courses
        self.config = config
        self.running = False
        
    def run(self):
        """执行抢课"""
        self.running = True
        self.log_message.emit("🚀 开始自动抢课...")
        
        # 按优先级排序
        sorted_courses = sorted(self.courses, key=lambda x: x.priority)
        total = len(sorted_courses)
        
        for idx, course in enumerate(sorted_courses):
            if not self.running:
                break
                
            self.progress_update.emit(idx + 1, total)
            self.log_message.emit(f"正在抢课: {course.course_name} ({course.teacher_name})")
            
            # TODO: 实际的抢课逻辑
            # 1. 搜索课程
            # 2. 点击选课
            # 3. 确认选课
            # 4. 检查结果
            
            # 这里暂时只是框架，等选课页面开放后填入实际代码
            self.msleep(self.config.get("attempt_interval", 100))
        
        self.log_message.emit("✅ 抢课任务完成！")
        self.running = False
    
    def stop(self):
        """停止抢课"""
        self.running = False
        self.log_message.emit("⏸ 已停止抢课")


class CourseGrabberManager:
    """抢课管理器 - 主控制器"""
    
    def __init__(self, webview):
        self.webview = webview
        self.courses: list[CourseConfig] = []
        self.config = {
            "enabled": False,
            "auto_refresh_interval": 1,  # 秒
            "max_attempts": 1000,
            "attempt_interval": 100,  # 毫秒
            "notify_on_success": True,
            "notify_on_failure": True
        }
        self.config_file = Path.cwd() / "scripts" / "course_grabber_config.json"
        self.grabber_thread = None
        
        # 定时器（用于定时开始抢课）
        self.start_timer = QTimer()
        self.start_timer.timeout.connect(self.on_timer_start)
        
    def load_config(self):
        """加载抢课配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config.update(data.get("settings", {}))
                    courses_data = data.get("courses", [])
                    self.courses = [CourseConfig.from_dict(c) for c in courses_data]
                return True
        except Exception as e:
            print(f"加载抢课配置失败: {e}")
        return False
    
    def save_config(self):
        """保存抢课配置"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "settings": self.config,
                "courses": [c.to_dict() for c in self.courses]
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存抢课配置失败: {e}")
        return False
    
    def add_course(self, course_config):
        """添加课程到抢课列表"""
        self.courses.append(course_config)
        self.save_config()
    
    def remove_course(self, course_name):
        """移除课程"""
        self.courses = [c for c in self.courses if c.course_name != course_name]
        self.save_config()
    
    def start_grabbing(self, callback=None):
        """开始抢课"""
        if not self.config.get("enabled"):
            return False, "抢课功能未启用"
        
        if not self.courses:
            return False, "没有配置要抢的课程"
        
        # 创建并启动抢课线程
        self.grabber_thread = CourseGrabber(self.webview, self.courses, self.config)
        
        if callback:
            self.grabber_thread.log_message.connect(callback)
        
        self.grabber_thread.start()
        return True, "已启动抢课"
    
    def stop_grabbing(self):
        """停止抢课"""
        if self.grabber_thread and self.grabber_thread.running:
            self.grabber_thread.stop()
            self.grabber_thread.wait()
    
    def schedule_start(self, start_datetime):
        """定时开始抢课"""
        now = datetime.now()
        if start_datetime <= now:
            return False, "开始时间必须在未来"
        
        delay_ms = int((start_datetime - now).total_seconds() * 1000)
        self.start_timer.start(delay_ms)
        return True, f"已设置定时抢课，将在 {start_datetime.strftime('%Y-%m-%d %H:%M:%S')} 开始"
    
    def on_timer_start(self):
        """定时器触发，开始抢课"""
        self.start_timer.stop()
        self.start_grabbing()
