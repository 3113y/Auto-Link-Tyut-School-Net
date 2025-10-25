#include "captcha_handler.h"
#include "preprocess.h"
// #include <onnxruntime_cxx_api.h> // 需安装ONNX Runtime C++

CaptchaHandler::CaptchaHandler(const std::string &digits_model, const std::string &operators_model)
    : digitsModelPath(digits_model), operatorsModelPath(operators_model) {}

bool CaptchaHandler::loadModels() {
    // TODO: 加载ONNX模型
    return true;
}

std::string CaptchaHandler::recognize(const cv::Mat &img, float &confidence) {
    // TODO: 预处理+ONNX推理
    cv::Mat bin = preprocess_rgb_to_binary_smart(img);
    // TODO: ONNX推理代码
    confidence = 1.0f;
    return "8-6=2";
}
