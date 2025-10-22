# 验证码处理工具，包括GIF处理
import io
from PIL import Image, ImageSequence

def process_gif_captcha(image_bytes, background_threshold=220):
    """
    处理GIF验证码，提取帧、去除背景、合成静态图像
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
        final_image_bytes = io.BytesIO()
        canvas.save(final_image_bytes, format='PNG')
        return final_image_bytes.getvalue()
