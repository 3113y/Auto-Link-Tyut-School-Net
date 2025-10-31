#include "preprocess.h"

cv::Mat preprocess_rgb_to_binary_smart(const cv::Mat &img) {
    // TODO: 按照Python preprocess_helper.py逻辑实现
    cv::Mat gray, bin;
    cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);
    cv::threshold(gray, bin, 128, 255, cv::THRESH_BINARY);
    return bin;
}
