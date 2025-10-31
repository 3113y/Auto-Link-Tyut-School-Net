# Copilot Instructions for Auto-Link-Tyut-School-Net

## Overview
This project is a GUI tool designed to automate login to the TYUT teaching management platform. It integrates AI-based CAPTCHA recognition using ONNX models and provides features like multi-server polling, configuration management, and a course-grabbing assistant.

### Key Components
- **`app.py`**: Entry point of the application.
- **`autolink_modules/`**: Core logic modules:
  - `main_window.py`: Main GUI logic.
  - `captcha_handler.py`: Handles CAPTCHA recognition using ONNX models.
  - `login_logic.py`: Implements the login workflow.
  - `config_manager.py`: Manages user configurations.
  - `html_recorder.py`: Records HTML for course-grabbing assistance.
  - `js_scripts.py`: Injects JavaScript for DOM manipulation.
- **`models/`**: Contains ONNX models for CAPTCHA recognition.
- **`scripts/config.json`**: Stores user credentials and server configurations.
- **`recorded_sessions/`**: Stores recorded HTML and user actions for course-grabbing.

## Developer Workflows

### Building the Project
- **Windows (MSVC)**:
  Use the provided CMake build task:
  ```
  cmd /c "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat && cmake -S . -B build && cmake --build build --config Release"
  ```

### Running the Application
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python app.py
   ```

### Testing
- Use `test.py` for unit tests.
- Ensure `scripts/config.json` is properly configured before running tests.

### Packaging
- To create an executable:
  ```bash
  python build_spec.py
  ```
  The output will be located in `dist/TYUT-AutoLogin.exe`.

## Project-Specific Conventions
- **Configuration Management**:
  - All user credentials and server URLs are stored in `scripts/config.json`.
  - Use the GUI to update configurations, which automatically saves to the file.
- **CAPTCHA Recognition**:
  - Models are stored in `models/`.
  - Use `captcha_handler.py` for preprocessing and inference.
- **Course-Grabbing Assistant**:
  - Outputs are saved in `recorded_sessions/`.
  - Update JavaScript selectors in `js_scripts.py` based on suggestions from `selector_suggestions_*.txt`.

## External Dependencies
- **ONNX Runtime**: For AI-based CAPTCHA recognition.
- **PyQt5**: For GUI and embedded browser.
- **Pillow**: For image preprocessing.

## Integration Points
- **VPN and Teaching Platform**:
  - Login logic interacts with `vpn.tyut.edu.cn` and `192.168.200.100`.
  - Multi-server polling is implemented in `login_logic.py`.
- **JavaScript Injection**:
  - DOM manipulation scripts are defined in `js_scripts.py`.

## Notes for AI Agents
- Focus on maintaining modularity within `autolink_modules/`.
- When adding new features, ensure they integrate seamlessly with the existing GUI and configuration management.
- Use `readme.md` and this document as primary references for understanding workflows and conventions.

---

For any unclear sections or additional guidance, please consult the project maintainers or refer to the `readme.md` file.