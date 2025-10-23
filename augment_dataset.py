"""
智能数据集扩充工具
- 统计现有样本数，计算每类需要补充多少到50个
- 从captcha_samples中提取字符
- 使用模板识别预标注
- 图形界面确认/纠正标签
- 自动保存到captcha_templates
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json
from collections import defaultdict
import random

# PyQt5导入
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QHBoxLayout, QPushButton, QLabel, QButtonGroup,
                                 QRadioButton, QGridLayout, QProgressBar, QMessageBox)
    from PyQt5.QtGui import QPixmap, QImage
    from PyQt5.QtCore import Qt, QEvent
except ImportError:
    print("错误: 需要安装PyQt5")
    print("运行: pip install PyQt5")
    sys.exit(1)

# 配置
TEMPLATES_DIR = Path("captcha_templates")
SAMPLES_DIR = Path("captcha_samples")
TARGET_COUNT = 50  # 每类目标数量
CHAR_WIDTH = 30
CHAR_HEIGHT = 50
IMAGE_WIDTH = 150
IMAGE_HEIGHT = 50

# 类别定义（目录名）
ALL_CLASSES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '+', '-', 'multiply']
OPERATORS = ['+', '-', 'multiply']
DIGITS = [str(i) for i in range(10)]
# 显示名称映射
CLASS_DISPLAY_NAME = {
    '0': '0', '1': '1', '2': '2', '3': '3', '4': '4',
    '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
    '+': '+', '-': '-', 'multiply': '*'
}

# 运算符位置约束（位置1和3）
OPERATOR_POSITIONS = [1, 3]
DIGIT_POSITIONS = [0, 2, 4]


def count_existing_samples():
    """统计每个类别现有的样本数"""
    counts = {}
    for class_name in ALL_CLASSES:
        class_dir = TEMPLATES_DIR / class_name
        if class_dir.exists():
            counts[class_name] = len(list(class_dir.glob("*.png")))
        else:
            counts[class_name] = 0
    return counts


def calculate_needs(counts):
    """计算每个类别还需要多少样本"""
    needs = {}
    for class_name in ALL_CLASSES:
        current = counts.get(class_name, 0)
        needed = max(0, TARGET_COUNT - current)
        needs[class_name] = needed
    return needs


def process_image_to_chars(image_path):
    """
    处理验证码图片（PNG/GIF），提取5个字符
    返回: [(原图char_rgb, 二值图char_binary, position), ...]
    """
    try:
        img = Image.open(image_path)
        
        # 转换第一帧（如果是GIF）并保存RGB原图
        if img.format == 'GIF':
            img_rgb = img.convert('RGB')
        else:
            img_rgb = img.convert('RGB')
        
        # 创建灰度图用于二值化
        img_gray = img_rgb.convert('L')
        
        # 创建二值图（用于模板匹配）
        pixels = list(img_gray.getdata())
        from collections import Counter
        background = Counter(pixels).most_common(1)[0][0]
        threshold = (background + 0) // 2
        img_binary = img_gray.point(lambda x: 255 if x < threshold else 0, '1')
        img_binary = img_binary.convert('L')
        
        # 分割5个字符（同时保存RGB原图和二值图）
        chars = []
        for i in range(5):
            x = i * CHAR_WIDTH
            char_rgb = img_rgb.crop((x, 0, x + CHAR_WIDTH, CHAR_HEIGHT))  # RGB原图
            char_binary = img_binary.crop((x, 0, x + CHAR_WIDTH, CHAR_HEIGHT))  # 二值图
            chars.append((char_rgb, char_binary, i))
        
        return chars
    except Exception as e:
        print(f"处理图片失败 {image_path}: {e}")
        return []


def simple_template_match(char_img, position):
    """
    简单模板匹配（用于预识别）
    返回: (predicted_class, confidence)
    """
    # 根据位置确定候选类别
    if position in OPERATOR_POSITIONS:
        candidates = OPERATORS
    else:
        candidates = DIGITS
    
    best_match = None
    best_score = -1
    
    # 遍历候选类别
    for class_name in candidates:
        template_dir = TEMPLATES_DIR / class_name
        if not template_dir.exists():
            continue
        
        # 加载该类的所有模板
        for template_path in template_dir.glob("*.png"):
            try:
                template = Image.open(template_path).convert('L')
                
                # 确保尺寸一致
                if template.size != char_img.size:
                    continue
                
                # 计算相似度（像素匹配率）
                pixels1 = list(char_img.getdata())
                pixels2 = list(template.getdata())
                
                matches = sum(1 for p1, p2 in zip(pixels1, pixels2) if p1 == p2)
                score = matches / len(pixels1)
                
                if score > best_score:
                    best_score = score
                    best_match = class_name
            except Exception as e:
                continue
    
    return best_match, best_score


class DataAugmentationTool(QMainWindow):
    """数据集扩充标注工具"""
    
    def __init__(self, char_queue, needs):
        super().__init__()
        self.char_queue = char_queue  # [(char_img, position, source_path, predicted_label), ...]
        self.needs = needs.copy()  # 剩余需求
        self.current_index = 0
        self.saved_count = 0
        
        self.init_ui()
        self.show_current_char()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("智能数据集扩充工具")
        self.setGeometry(100, 100, 800, 700)
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 进度信息
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel()
        progress_layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.char_queue))
        progress_layout.addWidget(self.progress_bar)
        layout.addLayout(progress_layout)
        
        # 图片显示区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(300, 500)
        self.image_label.setStyleSheet("border: 2px solid black; background-color: white;")
        layout.addWidget(self.image_label)
        
        # 预测结果
        self.prediction_label = QLabel()
        self.prediction_label.setAlignment(Qt.AlignCenter)
        self.prediction_label.setStyleSheet("font-size: 18px; font-weight: bold; color: blue;")
        layout.addWidget(self.prediction_label)
        
        # 位置信息
        self.position_label = QLabel()
        self.position_label.setAlignment(Qt.AlignCenter)
        self.position_label.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(self.position_label)
        
        # 类别选择按钮组
        button_group_widget = QWidget()
        button_layout = QGridLayout(button_group_widget)
        
        self.button_group = QButtonGroup()
        
        # 数字按钮 (0-9)
        for i in range(10):
            btn = QRadioButton(str(i))
            btn.setStyleSheet("font-size: 16px; padding: 10px;")
            self.button_group.addButton(btn, i)
            row = i // 5
            col = i % 5
            button_layout.addWidget(btn, row, col)
        
        # 运算符按钮（显示名 + 内部ID）
        # 按钮显示: +, -, *  但保存到目录: +, -, multiply
        operators_with_ids = [('+', 10), ('-', 11), ('*', 12)]
        for idx, (op, btn_id) in enumerate(operators_with_ids):
            btn = QRadioButton(op)
            btn.setStyleSheet("font-size: 16px; padding: 10px;")
            self.button_group.addButton(btn, btn_id)
            button_layout.addWidget(btn, 2, idx)
        
        layout.addWidget(button_group_widget)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        
        self.skip_btn = QPushButton("跳过 (S)")
        self.skip_btn.clicked.connect(self.skip_current)
        self.skip_btn.setStyleSheet("font-size: 14px; padding: 10px;")
        action_layout.addWidget(self.skip_btn)
        
        self.confirm_btn = QPushButton("确认并保存 (Enter)")
        self.confirm_btn.clicked.connect(self.confirm_and_save)
        self.confirm_btn.setStyleSheet("font-size: 14px; padding: 10px; background-color: #4CAF50; color: white;")
        action_layout.addWidget(self.confirm_btn)
        
        layout.addLayout(action_layout)
        
        # 需求统计
        self.needs_label = QLabel()
        self.needs_label.setStyleSheet("font-size: 12px; color: gray;")
        layout.addWidget(self.needs_label)
        
        self.update_needs_display()
    
    def update_needs_display(self):
        """更新需求统计显示"""
        needs_items = []
        for cls, cnt in sorted(self.needs.items()):
            if cnt > 0:
                # 显示名称：multiply -> *
                display_name = CLASS_DISPLAY_NAME.get(cls, cls)
                needs_items.append(f"{display_name}:需要{cnt}")
        
        needs_str = " | ".join(needs_items)
        if not needs_str:
            needs_str = "✅ 所有类别已达到50个！"
        self.needs_label.setText(needs_str)
    
    def show_current_char(self):
        """显示当前字符"""
        if self.current_index >= len(self.char_queue):
            self.finish()
            return
        
        char_img, position, source_path, predicted_label, confidence = self.char_queue[self.current_index]
        
        # 更新进度
        self.progress_bar.setValue(self.current_index + 1)
        self.progress_label.setText(f"进度: {self.current_index + 1}/{len(self.char_queue)} | 已保存: {self.saved_count}")
        
        # 放大显示图片（char_img已经是RGB格式）
        width, height = char_img.size
        scale = 6
        char_img_display = char_img.resize((width * scale, height * scale), Image.Resampling.NEAREST)
        
        # 转换为QPixmap显示
        img_bytes = char_img_display.tobytes()
        qimage = QImage(img_bytes, char_img_display.width, char_img_display.height, 
                       char_img_display.width * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        self.image_label.setPixmap(pixmap)
        
        # 显示预测结果
        if predicted_label:
            # 显示名称：multiply -> *
            display_name = CLASS_DISPLAY_NAME.get(predicted_label, predicted_label)
            self.prediction_label.setText(f"🤖 预测: {display_name} (置信度: {confidence:.1%})")
            # 自动选中预测的按钮
            btn_id = self.get_button_id(predicted_label)
            if btn_id is not None:
                btn = self.button_group.button(btn_id)
                if btn:
                    btn.setChecked(True)
        else:
            self.prediction_label.setText("🤖 预测: 无法识别")
        
        # 显示位置信息
        pos_desc = ["第1个数字", "第1个运算符", "第2个数字", "第2个运算符", "第3个数字"][position]
        self.position_label.setText(f"位置: {position} ({pos_desc}) | 来源: {source_path.name}")
    
    def get_button_id(self, label):
        """获取目录名对应的按钮ID"""
        if label.isdigit():
            return int(label)
        elif label == '+':
            return 10
        elif label == '-':
            return 11
        elif label == 'multiply':  # multiply 目录对应 * 按钮
            return 12
        return None
    
    def get_label_from_button_id(self, btn_id):
        """从按钮ID获取目录名（用于保存）"""
        if 0 <= btn_id <= 9:
            return str(btn_id)
        elif btn_id == 10:
            return '+'
        elif btn_id == 11:
            return '-'
        elif btn_id == 12:
            return 'multiply'  # * 对应 multiply 目录
        return None
    
    def confirm_and_save(self):
        """确认并保存当前字符"""
        # 获取选中的标签
        selected_btn = self.button_group.checkedButton()
        if not selected_btn:
            QMessageBox.warning(self, "警告", "请先选择一个类别！")
            return
        
        btn_id = self.button_group.id(selected_btn)
        label = self.get_label_from_button_id(btn_id)  # 这里返回目录名（如multiply）
        
        # 检查是否还需要这个类别 - 如果已达50个，自动跳过不保存
        if self.needs.get(label, 0) <= 0:
            print(f"⚠️  类别 '{CLASS_DISPLAY_NAME.get(label, label)}' 已达到50个，自动跳过")
            self.skip_current()
            return
        
        # 保存图片（RGB原图）
        char_img = self.char_queue[self.current_index][0]
        self.save_char_image(char_img, label)
        
        # 更新需求
        if label in self.needs and self.needs[label] > 0:
            self.needs[label] -= 1
        
        self.saved_count += 1
        self.update_needs_display()
        
        # 下一张
        self.current_index += 1
        self.show_current_char()
    
    def save_char_image(self, char_img, label):
        """保存字符图片到对应类别目录（保存切片后的RGB原图）"""
        class_dir = TEMPLATES_DIR / label
        class_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名（统计目录中所有PNG文件，而不是特定模式）
        existing_files = list(class_dir.glob("*.png"))
        next_id = len(existing_files) + 1
        
        # 使用目录名作为文件名前缀（避免*等特殊字符）
        # label 就是目录名：0-9, +, -, multiply
        filename = f"{label}_{next_id:03d}.png"
        
        save_path = class_dir / filename
        # 直接保存切片后的RGB原图
        char_img.save(save_path)
        
        # 显示名称用于打印
        display_name = CLASS_DISPLAY_NAME.get(label, label)
        print(f"✓ 保存: {display_name} -> {save_path}")
    
    def skip_current(self):
        """跳过当前字符"""
        self.current_index += 1
        self.show_current_char()
    
    def finish(self):
        """完成标注"""
        QMessageBox.information(self, "完成", 
                               f"数据集扩充完成！\n"
                               f"共保存 {self.saved_count} 个样本\n"
                               f"请查看 captcha_templates 目录")
        self.close()
    
    def keyPressEvent(self, event):
        """键盘快捷键"""
        key = event.key()
        text = event.text()
        
        # 数字键 0-9（通过文本判断更可靠）
        if text.isdigit():
            digit = int(text)
            btn = self.button_group.button(digit)
            if btn:
                btn.setChecked(True)
        
        # 运算符
        elif text == '+' or text == '=':  # + 或 =
            btn = self.button_group.button(10)
            if btn:
                btn.setChecked(True)
        elif text == '-':  # -
            btn = self.button_group.button(11)
            if btn:
                btn.setChecked(True)
        elif text == '*':  # * (Shift+8)
            btn = self.button_group.button(12)
            if btn:
                btn.setChecked(True)
        
        # Enter 确认
        elif key in (16777220, 16777221):  # Qt.Key_Return, Qt.Key_Enter
            self.confirm_and_save()
        
        # S 跳过
        elif text.upper() == 'S':
            self.skip_current()
        
        # Esc 退出
        elif key == 16777216:  # Qt.Key_Escape
            self.close()


def main():
    """主函数"""
    print("=" * 60)
    print("智能数据集扩充工具")
    print("=" * 60)
    
    # 1. 统计现有样本
    print("\n📊 统计现有样本...")
    counts = count_existing_samples()
    for class_name in ALL_CLASSES:
        count = counts[class_name]
        print(f"  {class_name}: {count}/50", end="")
        if count >= TARGET_COUNT:
            print(" ✓")
        else:
            print(f" (还需 {TARGET_COUNT - count})")
    
    # 2. 计算需求
    needs = calculate_needs(counts)
    total_needed = sum(needs.values())
    
    if total_needed == 0:
        print("\n✅ 所有类别已达到50个样本！无需扩充。")
        return
    
    print(f"\n📦 总共还需要: {total_needed} 个样本")
    
    # 3. 准备字符队列
    print("\n🔍 从captcha_samples提取字符并预识别...")
    char_queue = []
    
    # 获取所有样本图片（PNG或GIF）
    sample_files = list(SAMPLES_DIR.glob("*.png")) + list(SAMPLES_DIR.glob("*.gif"))
    sample_files.sort()  # 按文件名排序
    
    # 从第100张开始（跳过前99张，避免重复）
    start_index = 100
    sample_files = sample_files[start_index:]
    print(f"  跳过前 {start_index} 张图片（避免重复）")
    print(f"  剩余 {len(sample_files)} 张图片待处理")
    
    processed_count = 0
    for image_path in sample_files:
        chars = process_image_to_chars(image_path)
        
        for char_gray, char_binary, position in chars:
            # 只处理前3个字符（位置0,1,2），跳过"="和"?"（位置3,4）
            if position >= 3:
                continue
            
            # 使用二值图进行预识别
            predicted_label, confidence = simple_template_match(char_binary, position)
            
            # 如果预测的类别还需要样本，加入队列（保存原图用于显示）
            if predicted_label and needs.get(predicted_label, 0) > 0:
                char_queue.append((char_gray, position, image_path, predicted_label, confidence))
            # 或者无法识别的也加入（可能是需要的稀缺类别）
            elif not predicted_label:
                char_queue.append((char_gray, position, image_path, None, 0.0))
        
        processed_count += 1
        if processed_count % 50 == 0:
            print(f"  已处理 {processed_count}/{len(sample_files)} 个GIF...")
        
        # 如果队列已经足够大，可以停止
        if len(char_queue) >= total_needed * 2:  # 准备2倍的候选
            break
    
    print(f"✓ 共提取 {len(char_queue)} 个字符候选")
    
    if len(char_queue) == 0:
        print("\n⚠️  没有找到可用的字符！请检查captcha_samples目录。")
        return
    
    # 4. 启动图形界面
    print("\n🚀 启动图形标注界面...")
    print("\n使用说明:")
    print("  - 按数字键 0-9 选择数字")
    print("  - 按 + - * 选择运算符")
    print("  - 按 Enter 确认并保存")
    print("  - 按 S 跳过当前样本")
    print("  - 按 Esc 退出\n")
    
    app = QApplication(sys.argv)
    tool = DataAugmentationTool(char_queue, needs)
    tool.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
