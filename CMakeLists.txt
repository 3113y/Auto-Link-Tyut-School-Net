cmake_minimum_required(VERSION 3.16)
project(tyut_auto_login)
set(CMAKE_CXX_STANDARD 17)

# 设置C++编译输出目录为 build_c
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${PROJECT_SOURCE_DIR}/build_c")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${PROJECT_SOURCE_DIR}/build_c")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${PROJECT_SOURCE_DIR}/build_c")

# Qt
find_package(Qt6 COMPONENTS Widgets WebEngineWidgets Network REQUIRED)
# 本地依赖路径
set(LOCAL_LIBS_DIR "${PROJECT_SOURCE_DIR}/libs")

# OpenCV
if(EXISTS "${LOCAL_LIBS_DIR}/opencv")
  set(OpenCV_DIR "${LOCAL_LIBS_DIR}/opencv")
  set(OpenCV_INCLUDE_DIRS "${LOCAL_LIBS_DIR}/opencv/include")
  set(OpenCV_LIBS_DIR "${LOCAL_LIBS_DIR}/opencv/lib")
  file(GLOB OpenCV_LIBS "${OpenCV_LIBS_DIR}/*.lib")
  message(STATUS "Using local OpenCV in ${OpenCV_DIR}")
else()
  find_package(OpenCV REQUIRED)
  set(OpenCV_LIBS ${OpenCV_LIBS})
endif()

# ONNX Runtime
if(EXISTS "${LOCAL_LIBS_DIR}/onnxruntime")
  set(ONNXRUNTIME_INCLUDE_DIRS "${LOCAL_LIBS_DIR}/onnxruntime/include")
  set(ONNXRUNTIME_LIBS_DIR "${LOCAL_LIBS_DIR}/onnxruntime/lib")
  file(GLOB ONNXRUNTIME_LIBS "${ONNXRUNTIME_LIBS_DIR}/*.lib")
  message(STATUS "Using local ONNX Runtime in ${LOCAL_LIBS_DIR}/onnxruntime")
else()
  # 可选：find_package(onnxruntime REQUIRED)
  set(ONNXRUNTIME_LIBS "onnxruntime")
endif()

# nlohmann_json
set(NLOHMANN_JSON_INCLUDE "${LOCAL_LIBS_DIR}/nlohmann_json")

add_executable(tyut_auto_login
  src/main.cpp
  src/ui/main_window.cpp
  src/ui/main_window.h
  src/captcha/captcha_handler.cpp
  src/captcha/captcha_handler.h
  src/captcha/preprocess.cpp
  src/captcha/preprocess.h
)

target_include_directories(tyut_auto_login PRIVATE
  ${OpenCV_INCLUDE_DIRS}
  ${ONNXRUNTIME_INCLUDE_DIRS}
  ${NLOHMANN_JSON_INCLUDE}
)
target_link_directories(tyut_auto_login PRIVATE
  ${OpenCV_LIBS_DIR}
  ${ONNXRUNTIME_LIBS_DIR}
)
target_link_libraries(tyut_auto_login PRIVATE
  Qt6::Widgets Qt6::WebEngineWidgets
  ${OpenCV_LIBS}
  ${ONNXRUNTIME_LIBS}
)

# Qt资源文件（JS脚本）
qt_add_resources(tyut_auto_login resources/js/qt_js.qrc)
target_link_libraries(tyut_auto_login PRIVATE tyut_auto_login_resources)
