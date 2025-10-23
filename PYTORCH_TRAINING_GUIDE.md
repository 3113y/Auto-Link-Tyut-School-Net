# PyTorch验证码识别训练指南

## 📊 数据集信息
- **总样本数**: 401张字符图片
- **类别数**: 13类 (0-9, +, -, *)
- **图片尺寸**: 30×50像素 (黑底白字二值图)
- **数据分布**: 
  - 数字类 (0-9): 20-31张/类
  - 运算符: +39张, -46张, *47张

## ⚠️ 核心问题
- **当前准确率**: 52% (模板匹配)
- **错误集中点**: 位置2的数字识别 (100%错误发生在此)
- **混淆对**: 1↔9(4次), 3↔8(3次), 4↔7(2次), 0↔1(2次)

---

## 🚀 第一步：准备数据

### 1.1 复制数据到PyTorch项目
```powershell
# 在你的PyTorch项目根目录执行
Copy-Item -Path "E:\Auto Link Tyut School Net\captcha_templates" -Destination ".\data\" -Recurse
```

### 1.2 重命名运算符目录
```powershell
cd data\captcha_templates
Rename-Item -Path "+" -NewName "plus"
Rename-Item -Path "-" -NewName "minus"
Rename-Item -Path "*" -NewName "multiply"
```

### 1.3 验证数据结构
```powershell
Get-ChildItem -Directory | ForEach-Object { 
    Write-Host "$($_.Name): $(($_ | Get-ChildItem).Count)张"
}
```

---

## 🏗️ 第二步：创建模型文件

### 2.1 model.py - CNN模型定义
```python
import torch
import torch.nn as nn

class CaptchaCNN(nn.Module):
    """验证码字符识别CNN模型
    
    输入: (batch, 1, 50, 30) - 黑底白字二值图
    输出: (batch, 13) - 13类概率分布
    """
    def __init__(self, num_classes=13):
        super(CaptchaCNN, self).__init__()
        
        # 特征提取层
        self.features = nn.Sequential(
            # Conv1: 30x50 -> 28x48
            nn.Conv2d(1, 32, kernel_size=3, padding=0),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # -> 14x24
            
            # Conv2: 14x24 -> 12x22
            nn.Conv2d(32, 64, kernel_size=3, padding=0),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # -> 6x11
            
            # Conv3: 6x11 -> 4x9
            nn.Conv2d(64, 128, kernel_size=3, padding=0),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )
        
        # 分类器
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(128 * 4 * 9, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes)
        )
    
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)  # Flatten
        x = self.classifier(x)
        return x

# 类别映射
CLASS_NAMES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 
               'multiply', 'minus', 'plus']
CLASS_TO_CHAR = {
    '0': '0', '1': '1', '2': '2', '3': '3', '4': '4',
    '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
    'multiply': '*', 'minus': '-', 'plus': '+'
}
```

### 2.2 train.py - 训练脚本
```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms
from model import CaptchaCNN
import os
from datetime import datetime

# 超参数
BATCH_SIZE = 32
EPOCHS = 100
LEARNING_RATE = 0.001
TRAIN_RATIO = 0.8  # 80%训练，20%验证

# 数据预处理
transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=1),  # 确保单通道
    transforms.Resize((50, 30)),  # 标准化尺寸
    transforms.ToTensor(),
    # 图片是黑底白字，像素值归一化到[0,1]
])

def train():
    # 设备配置
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'使用设备: {device}')
    
    # 加载数据集
    dataset = datasets.ImageFolder(
        root='data/captcha_templates',
        transform=transform
    )
    
    # 划分训练集和验证集
    train_size = int(TRAIN_RATIO * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(
        dataset, 
        [train_size, val_size],
        generator=torch.Generator().manual_seed(42)  # 固定随机种子
    )
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    print(f'训练集: {train_size}张, 验证集: {val_size}张')
    print(f'类别数: {len(dataset.classes)}')
    print(f'类别: {dataset.classes}')
    
    # 创建模型
    model = CaptchaCNN(num_classes=len(dataset.classes)).to(device)
    
    # 损失函数和优化器
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=10
    )
    
    # 训练循环
    best_val_acc = 0.0
    for epoch in range(EPOCHS):
        # 训练阶段
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = outputs.max(1)
            train_total += labels.size(0)
            train_correct += predicted.eq(labels).sum().item()
        
        train_acc = 100. * train_correct / train_total
        
        # 验证阶段
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                
                val_loss += loss.item()
                _, predicted = outputs.max(1)
                val_total += labels.size(0)
                val_correct += predicted.eq(labels).sum().item()
        
        val_acc = 100. * val_correct / val_total
        
        # 学习率调整
        scheduler.step(val_loss)
        
        # 打印进度
        print(f'Epoch [{epoch+1}/{EPOCHS}] '
              f'Train Loss: {train_loss/len(train_loader):.4f} '
              f'Train Acc: {train_acc:.2f}% '
              f'Val Loss: {val_loss/len(val_loader):.4f} '
              f'Val Acc: {val_acc:.2f}%')
        
        # 保存最佳模型
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            os.makedirs('saved_models', exist_ok=True)
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
                'class_to_idx': dataset.class_to_idx,
            }, 'saved_models/best_model.pth')
            print(f'✓ 保存最佳模型 (验证准确率: {val_acc:.2f}%)')
    
    print(f'\n训练完成! 最佳验证准确率: {best_val_acc:.2f}%')

if __name__ == '__main__':
    train()
```

### 2.3 predict.py - 预测脚本
```python
import torch
from PIL import Image
import torchvision.transforms as transforms
from model import CaptchaCNN, CLASS_TO_CHAR

def load_model(model_path='saved_models/best_model.pth'):
    """加载训练好的模型"""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # 加载检查点
    checkpoint = torch.load(model_path, map_location=device)
    
    # 创建模型
    num_classes = len(checkpoint['class_to_idx'])
    model = CaptchaCNN(num_classes=num_classes).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    # 创建索引到类别的映射
    idx_to_class = {v: k for k, v in checkpoint['class_to_idx'].items()}
    
    return model, idx_to_class, device

def predict_char(image_path, model, idx_to_class, device):
    """预测单个字符"""
    # 预处理
    transform = transforms.Compose([
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((50, 30)),
        transforms.ToTensor(),
    ])
    
    # 加载图片
    image = Image.open(image_path)
    image_tensor = transform(image).unsqueeze(0).to(device)
    
    # 预测
    with torch.no_grad():
        output = model(image_tensor)
        probabilities = torch.softmax(output, dim=1)
        confidence, predicted = probabilities.max(1)
    
    # 获取类别和字符
    class_name = idx_to_class[predicted.item()]
    char = CLASS_TO_CHAR[class_name]
    
    return char, confidence.item()

# 测试示例
if __name__ == '__main__':
    model, idx_to_class, device = load_model()
    
    # 测试单张图片
    test_image = 'data/captcha_templates/3/3_001.png'
    char, confidence = predict_char(test_image, model, idx_to_class, device)
    print(f'预测结果: {char} (置信度: {confidence*100:.2f}%)')
```

---

## 🎯 第三步：训练模型

### 3.1 安装依赖
```powershell
# 在PyTorch项目中
pip install torch torchvision pillow
```

### 3.2 开始训练
```powershell
python train.py
```

### 3.3 预期输出
```
使用设备: cuda
训练集: 320张, 验证集: 81张
类别数: 13
Epoch [1/100] Train Loss: 2.5123 Train Acc: 15.23% Val Loss: 2.1234 Val Acc: 25.93%
Epoch [2/100] Train Loss: 1.8234 Train Acc: 45.67% Val Loss: 1.5432 Val Acc: 52.34%
...
✓ 保存最佳模型 (验证准确率: 98.76%)
```

---

## 📦 第四步：导出模型用于集成

训练完成后，将模型复制回这个项目:

```powershell
# 复制训练好的模型
Copy-Item -Path "你的PyTorch项目\saved_models\best_model.pth" `
          -Destination "E:\Auto Link Tyut School Net\saved_models\"

# 复制predict.py和model.py
Copy-Item -Path "你的PyTorch项目\model.py" `
          -Destination "E:\Auto Link Tyut School Net\autolink_modules\"
Copy-Item -Path "你的PyTorch项目\predict.py" `
          -Destination "E:\Auto Link Tyut School Net\autolink_modules\"
```

---

## 🔌 第五步：集成到captcha_handler.py

模型训练好后，我会帮你修改 `captcha_handler.py` 的 `recognize_captcha()` 方法:

```python
def recognize_captcha(self, img_path: str) -> str:
    """识别验证码并返回表达式"""
    if self.model is None:
        return ""
    
    # 1. 处理GIF得到5个字符图片
    chars = self.process_gif_captcha(img_path)
    
    # 2. 使用深度学习模型预测每个字符
    result = ""
    for char_img in chars:
        char, confidence = predict_char(char_img, self.model, ...)
        result += char
    
    return result
```

---

## 📊 优化建议

### 数据增强 (如果准确率不够高)
```python
transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=1),
    transforms.Resize((50, 30)),
    transforms.RandomRotation(5),  # 随机旋转±5度
    transforms.RandomAffine(0, translate=(0.05, 0.05)),  # 随机平移
    transforms.ToTensor(),
])
```

### 针对混淆对的训练
```python
# 在损失函数中加权
class_weights = torch.ones(13)
class_weights[1] = 2.0  # 1的权重
class_weights[9] = 2.0  # 9的权重
class_weights[3] = 2.0  # 3的权重
class_weights[8] = 2.0  # 8的权重
criterion = nn.CrossEntropyLoss(weight=class_weights)
```

---

## ✅ 检查清单

训练前确认:
- [ ] 数据已复制到PyTorch项目
- [ ] 运算符目录已重命名 (+→plus, -→minus, *→multiply)
- [ ] PyTorch已安装
- [ ] GPU可用(可选,但推荐)

训练中监控:
- [ ] 验证准确率 > 95% (目标)
- [ ] 训练准确率和验证准确率差距 < 5% (避免过拟合)
- [ ] 特别关注 1/9, 3/8, 4/7, 0/1 的混淆矩阵

训练后验证:
- [ ] 在验证集上准确率 > 95%
- [ ] 在真实验证码上测试 (从 captcha_samples 抽取)
- [ ] 位置2的准确率显著提升

---

## 🎓 关键点总结

1. **数据格式完美**: 你的 captcha_templates 已经是标准ImageFolder格式
2. **小数据集**: 401张需要防止过拟合 (Dropout + 数据增强)
3. **针对性训练**: 重点关注 1↔9, 3↔8, 4↔7, 0↔1 混淆对
4. **目标准确率**: 从52%提升到>95%

开始训练后随时告诉我进展! 🚀
