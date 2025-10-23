"""JavaScript 代码模块 - 用于网页操作和状态检查"""


def get_check_login_status_js():
    """获取检查登录状态的 JavaScript 代码"""
    return """
    (function() {
        if (typeof motionpro !== 'undefined' && motionpro.vpn && motionpro.vpn.status === 1) {
            return 'vpn_success_api';
        }
        var vpnOffButton = document.querySelector('#vpnOff');
        if (vpnOffButton && vpnOffButton.className === 'btn') {
            return 'vpn_success_ui';
        }
        var vpnOnButton = document.querySelector('#vpnOn');
        var unameField = document.querySelector('[name="uname"]');
        var loginButton = document.querySelector('#login');
        if (!loginButton && !unameField && window.location.href.includes('192.168.200.100')) {
            return 'local_auth_success';
        }
        if (vpnOnButton && vpnOnButton.hasAttribute('disabled')) {
            return 'connecting';
        }
        if (unameField) {
            return 'failure';
        }
        return 'unknown';
    })();
    """


def get_check_login_message_js():
    """获取检查登录消息的 JavaScript 代码"""
    return """
    (function() {
        var msgElement = document.getElementById('loginMsg');
        if (msgElement && msgElement.textContent.trim()) {
            return msgElement.textContent.trim();
        }
        return null;
    })();
    """


def get_fill_local_auth_fields_js(username, password):
    """获取填充教学管理服务平台账号密码的 JavaScript 代码"""
    return f"""
    (function() {{
        var unameField = document.getElementById('txt_username');
        var pwdField = document.getElementById('txt_password');

        if (unameField && pwdField) {{
            console.log('找到教学管理服务平台登录表单字段，自动填充账号密码。');
            unameField.value = "{username}";
            pwdField.value = "{password}";
            console.log('账号密码已填充，请手动输入验证码并点击登录按钮。');
        }} else {{
            console.error('未找到教学管理服务平台登录表单字段。');
            if (!unameField) console.error('Username field (txt_username) not found.');
            if (!pwdField) console.error('Password field (txt_password) not found.');
        }}
    }})();
    """


def get_fill_form_and_login_js(username, password, captcha_result=None):
    """获取填充表单并登录的 JavaScript 代码"""
    captcha_val = captcha_result or ''
    return f"""
    (function() {{
        var unameField = document.querySelector('[name="uname"]') || document.getElementById('txt_username');
        var pwdField = document.querySelector('[name="pwd"]') || document.getElementById('txt_password');
        var captchaField = document.getElementById('captcha') || document.getElementById('txt_lazycaptcha');
        var loginButton = document.querySelector('#login') || document.getElementById('btn_login');

        if (unameField && pwdField && loginButton) {{
            console.log('找到登录表单字段。');
            unameField.value = "{username}";
            pwdField.value = "{password}";

            var captchaVal = "{captcha_val}";
            if (captchaField && captchaVal) {{
                console.log('填充验证码...');
                captchaField.value = captchaVal;
            }}

            console.log('尝试点击登录按钮...');
            loginButton.click();
        }} else {{
            console.error('登录表单字段或按钮未找到。无法执行登录。');
            if (!unameField) console.error('Username field not found.');
            if (!pwdField) console.error('Password field not found.');
            if (!loginButton) console.error('Login button not found.');
        }}
    }})();
    """


def get_check_captcha_js():
    """获取检查验证码图片的 JavaScript 代码"""
    return "document.getElementById('img_lazycaptcha') && document.getElementById('img_lazycaptcha').src"


def get_captcha_url_js():
    """获取验证码图片 URL 的 JavaScript 代码"""
    return "document.getElementById('img_lazycaptcha').src;"
