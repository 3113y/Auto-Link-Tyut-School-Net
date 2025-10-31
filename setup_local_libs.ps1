# 自动检测并设置本地依赖环境变量（仅Windows）
$root = $PSScriptRoot
$libs = Join-Path $root 'libs'

# OpenCV
$opencv_inc = Join-Path $libs 'opencv\include'
$opencv_lib = Join-Path $libs 'opencv\lib'
if (Test-Path $opencv_lib) {
    $env:OpenCV_DIR = $libs + '\opencv'
    $env:OpenCV_INCLUDE_DIRS = $opencv_inc
    $env:OpenCV_LIBS_DIR = $opencv_lib
    Write-Host "已设置本地 OpenCV 路径: $opencv_lib"
}

# ONNX Runtime
$onnx_inc = Join-Path $libs 'onnxruntime\include'
$onnx_lib = Join-Path $libs 'onnxruntime\lib'
if (Test-Path $onnx_lib) {
    $env:ONNXRUNTIME_INCLUDE_DIRS = $onnx_inc
    $env:ONNXRUNTIME_LIBS_DIR = $onnx_lib
    Write-Host "已设置本地 ONNX Runtime 路径: $onnx_lib"
}

# nlohmann_json
$json_inc = Join-Path $libs 'nlohmann_json'
if (Test-Path $json_inc) {
    $env:NLOHMANN_JSON_INCLUDE = $json_inc
    Write-Host "已设置本地 nlohmann_json 路径: $json_inc"
}

Write-Host "本地依赖环境变量已设置，可直接用 CMake 构建。"
