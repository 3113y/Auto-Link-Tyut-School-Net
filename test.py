import sys
try:
    import img2pdf
    print("img2pdf 已成功加载")
except ImportError as e:
    print(f"img2pdf 加载失败: {e}")

print(sys.executable)