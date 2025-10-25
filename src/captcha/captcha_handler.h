#pragma once
#include <string>
#include <vector>
#include <opencv2/opencv.hpp>

class CaptchaHandler {
public:
    CaptchaHandler(const std::string &digits_model, const std::string &operators_model);
    bool loadModels();
    std::string recognize(const cv::Mat &img, float &confidence);
    // ...其它接口
private:
    std::string digitsModelPath;
    std::string operatorsModelPath;
    // ONNX Runtime session指针等
};
