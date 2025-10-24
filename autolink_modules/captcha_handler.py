"""Captcha handler with ONNX model support."""
import io
import requests
import numpy as np
from PIL import Image, ImageSequence
from pathlib import Path
import onnxruntime as ort
import cv2
import sys
import os
from .preprocess_helper import analyze_and_enhance_colors, rgb_to_binary_smart


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS  # type: ignore
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class CaptchaHandler:
    """Captcha handler using ONNX models for recognition."""
    
    def __init__(self, digit_model_path="models/best_model_digits.onnx", 
                 operator_model_path="models/best_model_operators.onnx"):
        """Initialize captcha handler with ONNX models."""
        self.char_width = 30
        self.char_height = 50
        
        # Load ONNX models
        self.digit_session = None
        self.operator_session = None
        
        # Use resource path for PyInstaller compatibility
        digit_path = Path(get_resource_path(digit_model_path))
        operator_path = Path(get_resource_path(operator_model_path))
        
        if digit_path.exists():
            self.digit_session = ort.InferenceSession(str(digit_path))
            print(f"Loaded digit model: {digit_path}")
        else:
            print(f"Digit model not found: {digit_path}")
        
        if operator_path.exists():
            self.operator_session = ort.InferenceSession(str(operator_path))
            print(f"Loaded operator model: {operator_path}")
        else:
            print(f"Operator model not found: {operator_path}")
        
        # Class mappings
        self.digit_classes = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        self.operator_classes = ['+', '-', 'multiply']
        
    def download_and_solve(self, captcha_url, timeout=10):
        """Download and solve captcha from URL."""
        if not captcha_url:
            return False, None, "No captcha URL provided"
        
        try:
            response = requests.get(captcha_url, timeout=timeout)
            response.raise_for_status()
            
            processed_image_bytes = self.process_gif_captcha(response.content)
            captcha_text = self.recognize_captcha(processed_image_bytes)
            
            if not captcha_text:
                return False, None, "Captcha recognition failed"
            
            try:
                expression = captcha_text.replace('=?', '')
                captcha_result = self.safe_eval(expression)
                return True, str(captcha_result), None
            except Exception as e:
                return False, None, f"Calculation failed: {e}"
        
        except requests.RequestException as e:
            return False, None, f"Download failed: {e}"
        except Exception as e:
            return False, None, f"Processing error: {e}"
    
    def recognize_captcha(self, image_bytes):
        """Recognize captcha using ONNX models with preprocess_helper."""
        if self.digit_session is None or self.operator_session is None:
            print("ONNX models not loaded")
            return ""
        
        # Load image
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        if img.size != (150, 50):
            img = img.resize((150, 50))
        
        # Split and recognize characters
        result = []
        for position in range(3):  # Only first 3 positions: digit-operator-digit
            left = position * self.char_width
            right = left + self.char_width
            char_img = img.crop((left, 0, right, self.char_height))
            
            # Predict character using ONNX
            char, confidence = self.predict_char_onnx(char_img, position)
            result.append(char)
        
        # Add fixed "=?"
        result.extend(['=', '?'])
        
        return ''.join(result)
    
    def predict_char_onnx(self, char_img, position):
        """Predict single character using ONNX model."""
        # Convert to numpy array
        img_array = np.array(char_img)
        
        # Smart preprocessing using preprocess_helper
        binary_img = rgb_to_binary_smart(img_array)
        
        # Normalize to [0, 1]
        binary_img = binary_img.astype(np.float32) / 255.0
        
        # Reshape to (1, 1, 50, 30) - ONNX input format
        input_data = binary_img.reshape(1, 1, self.char_height, self.char_width)
        
        # Choose model based on position
        if position == 1:
            # Position 1 is operator
            session = self.operator_session
            if session is not None:  # Type guard
                input_name = session.get_inputs()[0].name
                output = session.run(None, {input_name: input_data})[0]
                
                # Softmax
                exp_output = np.exp(output - np.max(output))
                probabilities = exp_output / exp_output.sum()
                
                predicted_idx = np.argmax(probabilities)
                confidence = probabilities[0, predicted_idx]
                predicted_char = self.operator_classes[predicted_idx]
                
                # Convert "multiply" to "*"
                if predicted_char == 'multiply':
                    predicted_char = '*'
            else:
                predicted_char = '?'
                confidence = 0.0
        else:
            # Positions 0 and 2 are digits
            session = self.digit_session
            if session is not None:  # Type guard
                input_name = session.get_inputs()[0].name
                output = session.run(None, {input_name: input_data})[0]
                
                # Softmax
                exp_output = np.exp(output - np.max(output))
                probabilities = exp_output / exp_output.sum()
                
                predicted_idx = np.argmax(probabilities)
                confidence = probabilities[0, predicted_idx]
                predicted_char = self.digit_classes[predicted_idx]
            else:
                predicted_char = '?'
                confidence = 0.0
        
        return predicted_char, confidence
    
    def process_gif_captcha(self, image_bytes, background_threshold=220):
        """Process animated GIF captcha."""
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
                        # Keep dark pixels (captcha characters)
                        if (pixel[0] < background_threshold or 
                            pixel[1] < background_threshold or 
                            pixel[2] < background_threshold):
                            processed_data[x, y] = pixel
                
                canvas = Image.alpha_composite(canvas, processed_frame)
            
            # Convert to PNG
            final_image_bytes = io.BytesIO()
            canvas.save(final_image_bytes, format='PNG')
            return final_image_bytes.getvalue()
    
    def safe_eval(self, expr_str):
        """Safely evaluate arithmetic expression."""
        expr_str = expr_str.replace('x', '*').replace('×', '*').replace('÷', '/')
        
        if not all(c in '0123456789+-*/. ()' for c in expr_str):
            raise ValueError(f"Invalid characters in expression: {expr_str}")
        
        return eval(expr_str)
