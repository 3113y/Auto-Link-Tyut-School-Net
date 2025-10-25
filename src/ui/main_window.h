#pragma once
#include <QMainWindow>
#include <QWebEngineView>

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();
private:
    QWebEngineView *webview;
    // ...其它控件和成员变量
};
