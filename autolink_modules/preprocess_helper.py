"""
验证码预处理辅助工具
用于数据标注时的图像预处理
包含智能颜色分析、增强和二值化功能
"""
import cv2
import numpy as np

def analyze_and_enhance_colors(image):
    """
    智能颜色分析和增强
    
    功能:
    1. 自动检测图像颜色分布
    2. 根据需要反转颜色
    3. Gamma校正加深图像
    4. CLAHE增强对比度
    5. 形态学操作完善轮廓
    6. 字符区域额外加深
    """
    # 转为灰度
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    # 使用Otsu自动阈值分析颜色分布
    _, otsu_binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 统计亮色和暗色像素比例
    total_pixels = otsu_binary.size
    light_pixels = np.sum(otsu_binary > 0)
    light_ratio = light_pixels / total_pixels
    
    # 计算平均灰度
    mean_gray = np.mean(gray)
    
    # 复制图像用于处理
    processed = image.copy()
    
    # 策略1: 如果亮色占比>55%且平均灰度>140，反转颜色
    if light_ratio > 0.55 and mean_gray > 140:
        processed = 255 - processed
    
    # 策略2: 如果平均灰度>180，使用gamma加深
    if mean_gray > 180:
        gamma = 0.5  # 更激进的gamma值
        processed = np.power(processed / 255.0, gamma) * 255
        processed = processed.astype(np.uint8)
    
    # 总是执行CLAHE增强(更激进的参数)
    processed_gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(processed_gray)
    
    # 自适应阈值预检测轮廓
    adaptive = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # 闭运算连接断开的轮廓
    kernel = np.ones((3, 3), np.uint8)
    closed = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    # 找到字符区域并额外压暗
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        # 创建字符区域掩码
        mask = np.zeros_like(enhanced)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 50:  # 过滤小噪点
                cv2.drawContours(mask, [cnt], -1, 255, -1)
        
        # 字符区域额外压暗30%
        enhanced = enhanced.astype(float)
        enhanced[mask > 0] *= 0.7
        enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
    
    return enhanced


def rgb_to_binary_smart(image):
    """
    RGB转二值化 - 智能方法(带二次检查)
    
    功能:
    1. 智能颜色分析和增强
    2. 第一次二值化
    3. 检查前景比例
    4. 自动调整确保结果正确
    """
    # 智能颜色分析和增强
    enhanced = analyze_and_enhance_colors(image)
    enhanced_array = np.array(enhanced, dtype=np.float32)
    
    # 第一次二值化
    threshold = 128
    binary = (enhanced_array < threshold).astype(np.uint8) * 255
    
    # 统计前景像素比例
    total_pixels = binary.size
    foreground_pixels = np.sum(binary > 0)
    foreground_ratio = foreground_pixels / total_pixels
    
    # 二次检查和调整
    if foreground_ratio < 0.05:  # 前景太少
        # 策略1: 尝试反转
        binary_inverted = 255 - binary
        foreground_inverted = np.sum(binary_inverted > 0) / total_pixels
        
        if foreground_inverted > 0.05 and foreground_inverted < 0.95:
            binary = binary_inverted
        else:
            # 策略2: 降低阈值
            binary = (enhanced_array < 100).astype(np.uint8) * 255
            foreground_ratio = np.sum(binary > 0) / total_pixels
            
            # 策略3: 如果还是太少，用Otsu
            if foreground_ratio < 0.03:
                _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                foreground_otsu = np.sum(binary > 0) / total_pixels
                if foreground_otsu < 0.03:
                    binary = 255 - binary
                    
    elif foreground_ratio > 0.95:  # 前景太多
        # 策略1: 尝试反转
        binary_inverted = 255 - binary
        foreground_inverted = np.sum(binary_inverted > 0) / total_pixels
        
        if foreground_inverted > 0.05 and foreground_inverted < 0.95:
            binary = binary_inverted
        else:
            # 策略2: 提高阈值
            binary = (enhanced_array < 150).astype(np.uint8) * 255
            foreground_ratio = np.sum(binary > 0) / total_pixels
            
            # 策略3: 如果还是太多，用Otsu
            if foreground_ratio > 0.97:
                _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                foreground_otsu = np.sum(binary > 0) / total_pixels
                if foreground_otsu > 0.97:
                    binary = 255 - binary
    
    return binary


def preprocess_captcha(image_path, output_path=None):
    """
    预处理单张验证码图片
    
    参数:
        image_path: 输入图片路径
        output_path: 输出路径(可选，如果不提供则不保存)
    
    返回:
        binary: 二值化后的图像(numpy数组)
    """
    # 读取图片
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"无法读取图片: {image_path}")
    
    # BGR转RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # 智能预处理
    binary = rgb_to_binary_smart(image_rgb)
    
    # 保存结果(如果指定了输出路径)
    if output_path:
        cv2.imwrite(str(output_path), binary)
        print(f"✓ 已保存: {output_path}")
    
    return binary


# 使用示例
if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    print("验证码预处理辅助工具")
    print("=" * 60)
    print("功能:")
    print("  • 智能颜色分析")
    print("  • 自动增强对比度")
    print("  • 二值化处理")
    print("  • 多层检查确保效果")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        # 命令行模式: python preprocess_helper.py input.png [output.png]
        input_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        
        try:
            binary = preprocess_captcha(input_path, output_path)
            print(f"\n✓ 处理完成")
            print(f"  输入: {input_path}")
            if output_path:
                print(f"  输出: {output_path}")
            print(f"  尺寸: {binary.shape}")
        except Exception as e:
            print(f"\n✗ 处理失败: {e}")
    else:
        # 交互模式
        print("\n使用方法:")
        print("  命令行: python preprocess_helper.py input.png [output.png]")
        print("  代码调用:")
        print("    from preprocess_helper import preprocess_captcha")
        print("    binary = preprocess_captcha('image.png', 'output.png')")
