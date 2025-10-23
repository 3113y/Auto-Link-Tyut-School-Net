""""""

验证码处理模块验证码处理模块



功能：功能：

- 下载验证码图片- 下载验证码图片

- 处理 GIF 动态验证码- 处理 GIF 动态验证码

- 验证码识别接口（待集成深度学习模型）- 验证码识别接口（待集成深度学习模型）

- 算术表达式安全计算- 算术表达式安全计算

""""""

import ioimport io

import requestsimport requests

from PIL import Image, ImageSequencefrom PIL import Image, ImageSequence

from pathlib import Path



class CaptchaHandler:

    """验证码处理器"""class CaptchaHandler:

        """验证码处理器"""

    def __init__(self, model=None):    

        """    def __init__(self, model=None):

        初始化验证码处理器        """

                初始化验证码处理器

        Args:        

            model: 深度学习模型（可选，用于验证码识别）        Args:

        """            model: 深度学习模型（可选，用于验证码识别）

        self.char_width = 30        """

        self.char_height = 50        self.char_width = 30

        self.model = model  # 深度学习模型将在这里集成        self.char_height = 50

            self.model = model  # 深度学习模型将在这里集成

    def download_and_solve(self, captcha_url, timeout=10):    

        """    def download_and_solve(self, captcha_url, timeout=10):

        下载并识别验证码（完整流程）        """

                下载并识别验证码（完整流程）

        Args:        

            captcha_url: 验证码图片URL        此方法执行完整的验证码处理流程：

            timeout: 请求超时时间（秒）        1. 下载验证码图片

                    2. 处理 GIF 动态验证码

        Returns:        3. 模板匹配识别

            tuple: (成功标志, 计算结果, 错误信息)        4. 计算算术表达式

        """        

        if not captcha_url:        Args:

            return False, None, "未找到验证码图片URL"            captcha_url (str): 验证码图片的 URL

                    timeout (int): 请求超时时间（秒），默认 10 秒

        try:            

            response = requests.get(captcha_url, timeout=timeout)        Returns:

            response.raise_for_status()            tuple: (success: bool, result: str or None, error_msg: str or None)

                            - success: 处理是否成功

            processed_image_bytes = self.process_gif_captcha(response.content)                - result: 验证码识别结果或计算结果

                            - error_msg: 错误信息（如果有）

            # 识别验证码                

            captcha_text = self.recognize_captcha(processed_image_bytes)        Examples:

                        >>> handler = CaptchaHandler()

            if not captcha_text:            >>> success, result, error = handler.download_and_solve("http://example.com/captcha.gif")

                return False, None, "验证码识别失败"            >>> if success:

                        ...     print(f"验证码结果: {result}")

            try:        """

                expression = captcha_text.replace('=?', '')        if not captcha_url:

                captcha_result = self.safe_eval(expression)            return False, None, "未找到验证码图片URL"

                return True, str(captcha_result), None        

            except Exception as e:        try:

                return False, None, f"验证码计算失败: {e}"            response = requests.get(captcha_url, timeout=timeout)

                            response.raise_for_status()

        except requests.RequestException as e:            

            return False, None, f"下载验证码失败: {e}"            processed_image_bytes = self.process_gif_captcha(response.content)

        except Exception as e:            

            return False, None, f"处理验证码时发生错误: {e}"            # 使用模板匹配识别验证码

                captcha_text = self.recognize_captcha(processed_image_bytes)

    def recognize_captcha(self, image_bytes):            

        """            if not captcha_text:

        识别验证码（待集成深度学习模型）                return False, None, "验证码识别为空"

                    

        Args:            try:

            image_bytes: 处理后的PNG图片字节数据                # 去除 "=?" 后计算表达式

                            expression = captcha_text.replace('=?', '')

        Returns:                captcha_result = self.safe_eval(expression)

            str: 识别结果，如 "3+5=?" 或空字符串                return True, str(captcha_result), None

        """            except Exception as e:

        if self.model is None:                return False, None, f"验证码计算失败: {e}"

            print("⚠ 未加载识别模型")                

            return ""        except requests.RequestException as e:

                    return False, None, f"下载验证码失败: {e}"

        # TODO: 使用深度学习模型识别        except Exception as e:

        # 1. 分割图片为5个字符            return False, None, f"处理验证码时发生错误: {e}"

        # 2. 对每个字符调用模型预测    

        # 3. 拼接结果    def recognize_captcha(self, image_bytes):

        return ""        """

            识别验证码（使用模板匹配）

    def process_gif_captcha(self, image_bytes, background_threshold=220):        

        """        Args:

        处理 GIF 动态验证码            image_bytes: 处理后的PNG图片字节

                    

        流程：        Returns:

        1. 逐帧提取 GIF            str: 识别结果，如 "3+5=?"

        2. 去除背景像素（亮色）        """

        3. 保留前景内容（暗色，即验证码字符）        if not self.templates:

        4. 合成所有帧            return ""

        5. 输出为 PNG 格式        

                # 分割字符

        Args:        img = Image.open(io.BytesIO(image_bytes))

            image_bytes: GIF 图片字节数据        if img.size != (150, 50):

            background_threshold: 背景阈值            img = img.resize((150, 50))

                    

        Returns:        result = []

            bytes: 处理后的 PNG 图片字节数据        for i in range(5):

        """            left = i * self.char_width

        with Image.open(io.BytesIO(image_bytes)) as img:            right = left + self.char_width

            canvas = Image.new('RGBA', img.size, (255, 255, 255, 0))            char_img = img.crop((left, 0, right, self.char_height))

                        

            for frame in ImageSequence.Iterator(img):            # 识别字符

                frame = frame.convert('RGBA')            char = self.match_template(char_img, i)

                processed_frame = Image.new('RGBA', frame.size, (255, 255, 255, 0))            result.append(char)

                frame_data = frame.load()        

                processed_data = processed_frame.load()        return ''.join(result)

                    

                if not frame_data or not processed_data:    def match_template(self, char_img, position):

                    continue        """

                        模板匹配识别单个字符

                for y in range(frame.height):        

                    for x in range(frame.width):        Args:

                        pixel = frame_data[x, y]            char_img: 字符图像

                        # 保留暗色像素（验证码字符）            position: 位置（0-4）

                        if (pixel[0] < background_threshold or             

                            pixel[1] < background_threshold or         Returns:

                            pixel[2] < background_threshold):            str: 识别的字符

                            processed_data[x, y] = pixel        """

                        # 位置3和4固定

                canvas = Image.alpha_composite(canvas, processed_frame)        if position == 3:

                        return '='

            # 转为 PNG        if position == 4:

            final_image_bytes = io.BytesIO()            return '?'

            canvas.save(final_image_bytes, format='PNG')        

            return final_image_bytes.getvalue()        # 提取二值化特征

            gray = char_img.convert('L')

    def safe_eval(self, expression):        arr = np.array(gray)

        """        threshold = np.mean(arr)

        安全计算算术表达式        binary = (arr < threshold).astype(np.float32)

                

        只允许基本算术运算，禁止其他操作        # 与所有模板匹配（考虑位置约束）

                best_char = '?'

        Args:        best_score = -1

            expression: 算术表达式字符串，如 "3+5"        

                    for char, template in self.templates.items():

        Returns:            # 位置0和2应该是数字（强约束）

            int: 计算结果            if position in [0, 2] and char not in '0123456789':

        """                continue

        allowed_chars = set('0123456789+-* ')            # 位置1应该是运算符（强约束）

        if not all(c in allowed_chars for c in expression):            if position == 1 and char not in '+-*':

            raise ValueError(f"表达式包含非法字符: {expression}")                continue

                    

        try:            # 确保尺寸一致

            result = eval(expression, {"__builtins__": {}}, {})            if binary.shape != template.shape:

            return int(result)                continue

        except Exception as e:            

            raise ValueError(f"表达式计算失败: {e}")            # 计算相似度（像素匹配率）

            score = np.sum((binary > 0.5) == (template > 0.5)) / binary.size
            
            if score > best_score:
                best_score = score
                best_char = char
        
        return best_char
    
    def process_gif_captcha(self, image_bytes, background_threshold=220):
        """
        处理 GIF 动态验证码
        
        升级版：自动检测并移除干扰线，不再填充轮廓。
        处理流程：
        1. 逐帧提取 GIF 图片
        2. 将每一帧转换为 RGBA 模式
        3. 去除背景像素（亮色像素）
        4. 保留前景内容（暗色像素，即验证码字符）
        5. 合成所有帧
        6. 移除干扰线（细长、非闭合线段）
        7. 输出为 PNG 格式
        """
        with Image.open(io.BytesIO(image_bytes)) as img:
            canvas = Image.new('RGBA', img.size, (255, 255, 255, 0))
            for frame in ImageSequence.Iterator(img):
                frame = frame.convert('RGBA')
                processed_frame = Image.new('RGBA', frame.size, (255, 255, 255, 0))
                frame_data = frame.load()
                processed_data = processed_frame.load()
                if not frame_data or not processed_data:
                    continue
                for y in range(frame.height):
                    for x in range(frame.width):
                        pixel = frame_data[x, y]
                        if pixel[0] < background_threshold or pixel[1] < background_threshold or pixel[2] < background_threshold:
                            processed_data[x, y] = pixel
                canvas = Image.alpha_composite(canvas, processed_frame)
            # 移除干扰线
            canvas = self.remove_interference_lines(canvas, background_threshold)
            final_image_bytes = io.BytesIO()
            canvas.save(final_image_bytes, format='PNG')
            return final_image_bytes.getvalue()

    def remove_interference_lines(self, image, threshold=220):
        """
        自动检测并移除贯穿数字和运算符号的干扰线（非闭合线）
        Args:
            image (PIL.Image): RGBA图像
            threshold (int): 背景阈值
        Returns:
            PIL.Image: 处理后的图像
        """
        import numpy as np
        from PIL import ImageFilter
        # 转为灰度
        gray = image.convert('L')
        arr = np.array(gray)
        # 二值化
        bin_arr = (arr < threshold).astype(np.uint8) * 255
        # 边缘检测（Sobel）
        from scipy.ndimage import sobel
        edge_x = sobel(bin_arr, axis=1)
        edge_y = sobel(bin_arr, axis=0)
        edges = np.hypot(edge_x, edge_y)
        edges = (edges > 100).astype(np.uint8) * 255
        # 连通域分析，找细长线段
        from skimage.measure import label, regionprops
        label_img = label(edges)
        props = regionprops(label_img)
        mask = np.zeros_like(bin_arr)
        for prop in props:
            minr, minc, maxr, maxc = prop.bbox
            h, w = maxr - minr, maxc - minc
            # 只处理细长线段（宽或高很小，长度较大）
            if (h <= 2 and w > 10) or (w <= 2 and h > 10):
                # 判断是否非闭合（端点在边缘或与字符不连通）
                mask[label_img == prop.label] = 255
        # 用mask去除干扰线
        arr_rgba = np.array(image)
        arr_rgba[mask == 255] = [255, 255, 255, 0]
        return Image.fromarray(arr_rgba)
    
    def fill_semi_closed_regions(self, image, threshold=220, edge_tolerance=3):
        """
        填充未完全封闭的区域
        
        对于被干扰线贯穿、边缘有2-3px干扰像素的半封闭区域，
        使用与轮廓颜色相同的颜色进行填充。
        
        Args:
            image (PIL.Image): 输入图像（RGBA模式）
            threshold (int): 背景阈值
            edge_tolerance (int): 边缘容差（像素），默认3
            
        Returns:
            PIL.Image: 处理后的图像
        """
        img_copy = image.copy()
        pixels = img_copy.load()
        width, height = img_copy.size
        
        visited = set()
        
        def is_foreground(x, y):
            if x < 0 or x >= width or y < 0 or y >= height:
                return False
            pixel = pixels[x, y]
            return pixel[3] > 0 and (pixel[0] < threshold or pixel[1] < threshold or pixel[2] < threshold)
        
        def get_boundary_color(x, y):
            colors = []
            for dx in range(-edge_tolerance, edge_tolerance + 1):
                for dy in range(-edge_tolerance, edge_tolerance + 1):
                    nx, ny = x + dx, y + dy
                    if is_foreground(nx, ny):
                        colors.append(pixels[nx, ny])
            if colors:
                avg_r = sum(c[0] for c in colors) // len(colors)
                avg_g = sum(c[1] for c in colors) // len(colors)
                avg_b = sum(c[2] for c in colors) // len(colors)
                return (avg_r, avg_g, avg_b, 255)
            return None
        
        def flood_fill(start_x, start_y, fill_color):
            queue = deque([(start_x, start_y)])
            filled_pixels = []
            
            while queue:
                x, y = queue.popleft()
                
                if (x, y) in visited or x < 0 or x >= width or y < 0 or y >= height:
                    continue
                
                pixel = pixels[x, y]
                if pixel[3] > 0 and (pixel[0] < threshold or pixel[1] < threshold or pixel[2] < threshold):
                    continue
                
                visited.add((x, y))
                filled_pixels.append((x, y))
                
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    queue.append((x + dx, y + dy))
            
            has_boundary = any(
                is_foreground(x + dx, y + dy)
                for x, y in filled_pixels
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]
            )
            
            if has_boundary and len(filled_pixels) < width * height * 0.3:
                for x, y in filled_pixels:
                    pixels[x, y] = fill_color
        
        for y in range(height):
            for x in range(width):
                if (x, y) not in visited:
                    pixel = pixels[x, y]
                    if pixel[3] == 0 or (pixel[0] >= threshold and pixel[1] >= threshold and pixel[2] >= threshold):
                        boundary_color = get_boundary_color(x, y)
                        if boundary_color:
                            flood_fill(x, y, boundary_color)
        
        return img_copy
    
    def safe_eval(self, expr_str):
        """
        安全地计算简单算术表达式
        
        用于处理数学验证码，例如 "3+5=?" 或 "10×2=?"。
        此方法会先标准化表达式，然后安全地计算结果。
        
        安全措施：
        - 只允许数字 (0-9)
        - 只允许基本运算符 (+ - * /)
        - 只允许括号和空格
        - 拒绝任何其他字符（防止代码注入）
        
        Args:
            expr_str (str): 算术表达式字符串
                支持的格式：
                - "3+5" → 8
                - "10-2" → 8
                - "4*6" 或 "4x6" 或 "4×6" → 24
                - "8/2" 或 "8÷2" → 4.0
                - "(3+5)*2" → 16
            
        Returns:
            float or int: 计算结果
            
        Raises:
            ValueError: 如果表达式包含不允许的字符
            
        Examples:
            >>> handler = CaptchaHandler()
            >>> handler.safe_eval("3+5")
            8
            >>> handler.safe_eval("10×2")
            20
            >>> handler.safe_eval("(3+5)*2")
            16
        """
        expr_str = expr_str.replace('x', '*').replace('×', '*').replace('÷', '/')
        
        if not all(c in '0123456789+-*/. ()' for c in expr_str):
            raise ValueError(f"表达式包含不允许的字符: {expr_str}")
        
        return eval(expr_str)
