#include "main_window.h"
#include <QVBoxLayout>

MainWindow::MainWindow(QWidget *parent) : QMainWindow(parent) {
    QWidget *central = new QWidget(this);
    QVBoxLayout *layout = new QVBoxLayout(central);
    webview = new QWebEngineView(central);
    layout->addWidget(webview);
    setCentralWidget(central);
    // ...初始化其它控件
}

MainWindow::~MainWindow() {}
