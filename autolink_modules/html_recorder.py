"""
HTML 录制器 - 用于录制选课操作和保存页面 HTML
"""
from PyQt5.QtCore import QObject, pyqtSignal, QDateTime
from pathlib import Path
import json


class HTMLRecorder(QObject):
    """HTML 录制器 - 保存页面 HTML 和用户操作"""
    
    log_message = pyqtSignal(str)
    
    def __init__(self, webview):
        super().__init__()
        self.webview = webview
        self.recording = False
        self.actions = []  # 记录用户操作
        self.output_dir = Path.cwd() / "recorded_sessions"
        self.output_dir.mkdir(exist_ok=True)
        
    def save_current_html(self, callback=None):
        """保存当前页面的 HTML"""
        def on_html_received(html):
            timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
            filename = self.output_dir / f"page_{timestamp}.html"
            
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html)
                
                # 同时保存一份带注释的版本，方便分析
                annotated_filename = self.output_dir / f"page_{timestamp}_annotated.html"
                annotated_html = self._add_annotations(html)
                with open(annotated_filename, 'w', encoding='utf-8') as f:
                    f.write(annotated_html)
                
                self.log_message.emit(f"✅ 已保存页面 HTML: {filename.name}")
                self.log_message.emit(f"📝 带注释版本: {annotated_filename.name}")
                
                if callback:
                    callback(True, str(filename))
                    
            except Exception as e:
                self.log_message.emit(f"❌ 保存 HTML 失败: {e}")
                if callback:
                    callback(False, str(e))
        
        self.webview.page().toHtml(on_html_received)
    
    def _add_annotations(self, html):
        """添加注释标记常见的选课元素"""
        annotations = """
<!-- ============================================ -->
<!-- 自动生成的注释 - 帮助识别选课关键元素 -->
<!-- ============================================ -->
<!--
常见选择器模式：
1. 课程列表容器: table, .course-list, #courseTable
2. 课程行: tr, .course-row, .course-item
3. 选课按钮: .btn-select, .select-btn, button[onclick*="select"]
4. 确认按钮: .confirm, .btn-ok, #confirmBtn
5. 课程ID: [data-course-id], .course-id
6. 课程名称: .course-name, .title
7. 教师名称: .teacher, .teacher-name
8. 剩余名额: .remain, .quota

请在下面的 HTML 中查找这些元素！
-->
<!-- ============================================ -->

"""
        return annotations + html
    
    def start_recording_actions(self):
        """开始录制用户操作"""
        self.recording = True
        self.actions = []
        
        # 注入监听脚本
        monitor_js = """
        (function() {
            window.recordedActions = [];
            
            // 监听所有点击事件
            document.addEventListener('click', function(e) {
                const target = e.target;
                const action = {
                    type: 'click',
                    timestamp: new Date().toISOString(),
                    tagName: target.tagName,
                    className: target.className,
                    id: target.id,
                    innerText: target.innerText ? target.innerText.substring(0, 50) : '',
                    xpath: getXPath(target),
                    selector: getUniqueSelector(target)
                };
                window.recordedActions.push(action);
                console.log('🎬 录制点击:', action);
            }, true);
            
            // 监听输入事件
            document.addEventListener('input', function(e) {
                const target = e.target;
                const action = {
                    type: 'input',
                    timestamp: new Date().toISOString(),
                    tagName: target.tagName,
                    className: target.className,
                    id: target.id,
                    name: target.name,
                    value: target.value.substring(0, 20) + '...',  // 不记录完整密码
                    xpath: getXPath(target),
                    selector: getUniqueSelector(target)
                };
                window.recordedActions.push(action);
                console.log('⌨️ 录制输入:', action);
            }, true);
            
            // 获取元素的 XPath
            function getXPath(element) {
                if (element.id) {
                    return '//*[@id="' + element.id + '"]';
                }
                if (element === document.body) {
                    return '/html/body';
                }
                let ix = 0;
                const siblings = element.parentNode.childNodes;
                for (let i = 0; i < siblings.length; i++) {
                    const sibling = siblings[i];
                    if (sibling === element) {
                        return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                    }
                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                        ix++;
                    }
                }
            }
            
            // 获取唯一的 CSS 选择器
            function getUniqueSelector(element) {
                if (element.id) {
                    return '#' + element.id;
                }
                
                let path = [];
                while (element.nodeType === Node.ELEMENT_NODE) {
                    let selector = element.nodeName.toLowerCase();
                    if (element.className) {
                        selector += '.' + element.className.trim().replace(/\\s+/g, '.');
                    }
                    path.unshift(selector);
                    element = element.parentNode;
                    if (path.length > 5) break;  // 限制深度
                }
                return path.join(' > ');
            }
            
            console.log('🎬 操作录制已启动！');
            return 'recording_started';
        })();
        """
        
        self.webview.page().runJavaScript(monitor_js)
        self.log_message.emit("🎬 已启动操作录制（点击和输入将被记录）")
    
    def stop_recording_and_save(self):
        """停止录制并保存操作记录"""
        if not self.recording:
            self.log_message.emit("⚠️ 未在录制中")
            return
        
        self.recording = False
        
        # 获取录制的操作
        get_actions_js = "JSON.stringify(window.recordedActions || []);"
        
        def on_actions_received(actions_json):
            try:
                actions = json.loads(actions_json)
                
                timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
                actions_file = self.output_dir / f"actions_{timestamp}.json"
                
                # 保存操作记录
                with open(actions_file, 'w', encoding='utf-8') as f:
                    json.dump(actions, f, ensure_ascii=False, indent=2)
                
                # 生成可读的操作摘要
                summary_file = self.output_dir / f"actions_{timestamp}_summary.txt"
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write("=" * 60 + "\n")
                    f.write("操作录制摘要\n")
                    f.write("=" * 60 + "\n\n")
                    
                    for idx, action in enumerate(actions, 1):
                        f.write(f"[{idx}] {action['type'].upper()} - {action['timestamp']}\n")
                        f.write(f"    元素: <{action['tagName']}> ")
                        if action.get('id'):
                            f.write(f"#{action['id']} ")
                        if action.get('className'):
                            f.write(f".{action['className']} ")
                        f.write("\n")
                        if action.get('innerText'):
                            f.write(f"    文本: {action['innerText']}\n")
                        f.write(f"    选择器: {action.get('selector', 'N/A')}\n")
                        f.write(f"    XPath: {action.get('xpath', 'N/A')}\n")
                        f.write("\n")
                
                self.log_message.emit(f"✅ 已保存 {len(actions)} 个操作记录")
                self.log_message.emit(f"📄 JSON: {actions_file.name}")
                self.log_message.emit(f"📝 摘要: {summary_file.name}")
                
                # 生成建议的选择器
                self._generate_selector_suggestions(actions, timestamp)
                
            except Exception as e:
                self.log_message.emit(f"❌ 保存操作记录失败: {e}")
        
        self.webview.page().runJavaScript(get_actions_js, on_actions_received)
    
    def _generate_selector_suggestions(self, actions, timestamp):
        """根据录制的操作生成选择器建议"""
        suggestions_file = self.output_dir / f"selector_suggestions_{timestamp}.txt"
        
        with open(suggestions_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("自动生成的选择器建议\n")
            f.write("=" * 60 + "\n\n")
            
            # 分析点击的按钮
            click_actions = [a for a in actions if a['type'] == 'click']
            if click_actions:
                f.write("## 点击操作的建议选择器：\n\n")
                for idx, action in enumerate(click_actions, 1):
                    f.write(f"操作 {idx}: 点击 \"{action.get('innerText', 'N/A')[:30]}\"\n")
                    f.write(f"  推荐选择器: {action.get('selector', 'N/A')}\n")
                    if action.get('id'):
                        f.write(f"  或使用 ID: #{action['id']}\n")
                    f.write("\n")
            
            # 分析输入操作
            input_actions = [a for a in actions if a['type'] == 'input']
            if input_actions:
                f.write("\n## 输入操作的建议选择器：\n\n")
                for idx, action in enumerate(input_actions, 1):
                    f.write(f"输入 {idx}: {action.get('tagName')} ")
                    if action.get('name'):
                        f.write(f"name=\"{action['name']}\"")
                    f.write("\n")
                    f.write(f"  推荐选择器: {action.get('selector', 'N/A')}\n")
                    f.write("\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("复制上述选择器到 js_scripts.py 中替换 TODO 标记！\n")
            f.write("=" * 60 + "\n")
        
        self.log_message.emit(f"💡 已生成选择器建议: {suggestions_file.name}")
