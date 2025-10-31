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


# ==================== 抢课模块 JS 脚本 ====================

def get_check_course_page_js():
    """检查是否在选课页面"""
    return """
    (function() {
        // TODO: 根据实际选课页面调整选择器
        var courseTable = document.querySelector('.course-table') || 
                         document.querySelector('[id*="course"]') ||
                         document.querySelector('[class*="select-course"]');
        return courseTable !== null;
    })();
    """


def get_search_course_js(course_name=None, teacher_name=None, course_id=None):
    """搜索课程的 JavaScript 代码"""
    return f"""
    (function() {{
        // TODO: 根据实际页面调整选择器
        var searchInput = document.querySelector('#courseSearchInput') || 
                         document.querySelector('[name="courseName"]');
        var searchBtn = document.querySelector('#searchBtn') || 
                       document.querySelector('.search-button');
        
        if (searchInput) {{
            searchInput.value = "{course_name or ''}";
            if (searchBtn) {{
                searchBtn.click();
                return 'search_triggered';
            }}
            return 'search_input_filled';
        }}
        return 'search_field_not_found';
    }})();
    """


def get_select_course_js(course_id=None, course_name=None, teacher_name=None):
    """选课的 JavaScript 代码（核心功能）"""
    return f"""
    (function() {{
        // TODO: 根据实际页面调整选择器
        // 方法1: 通过课程ID查找
        var courseRow = document.querySelector('[data-course-id="{course_id}"]');
        
        // 方法2: 通过课程名称和教师名称查找
        if (!courseRow && "{course_name}") {{
            var allRows = document.querySelectorAll('.course-row, tr');
            for (var i = 0; i < allRows.length; i++) {{
                var row = allRows[i];
                var nameCell = row.querySelector('.course-name') || row.cells[1];
                var teacherCell = row.querySelector('.teacher-name') || row.cells[2];
                
                if (nameCell && nameCell.textContent.includes("{course_name}")) {{
                    if (!"{teacher_name}" || (teacherCell && teacherCell.textContent.includes("{teacher_name}"))) {{
                        courseRow = row;
                        break;
                    }}
                }}
            }}
        }}
        
        if (!courseRow) {{
            return 'course_not_found';
        }}
        
        // 查找选课按钮
        var selectBtn = courseRow.querySelector('.select-btn') || 
                       courseRow.querySelector('[class*="select"]') ||
                       courseRow.querySelector('button');
        
        if (!selectBtn) {{
            return 'button_not_found';
        }}
        
        // 检查按钮状态
        if (selectBtn.disabled || selectBtn.classList.contains('disabled')) {{
            return 'course_full';
        }}
        
        // 点击选课按钮
        selectBtn.click();
        
        // 等待确认弹窗
        setTimeout(function() {{
            var confirmBtn = document.querySelector('.confirm-select') || 
                           document.querySelector('[class*="confirm"]') ||
                           document.querySelector('.swal2-confirm');
            if (confirmBtn) {{
                confirmBtn.click();
            }}
        }}, 100);
        
        return 'select_clicked';
    }})();
    """


def get_check_select_result_js():
    """检查选课结果"""
    return """
    (function() {
        // TODO: 根据实际页面调整选择器
        // 检查成功提示
        var successMsg = document.querySelector('.success-message') || 
                        document.querySelector('[class*="success"]');
        if (successMsg && successMsg.textContent.includes('成功')) {
            return 'success';
        }
        
        // 检查失败提示
        var errorMsg = document.querySelector('.error-message') || 
                      document.querySelector('[class*="error"]');
        if (errorMsg) {
            return 'failed: ' + errorMsg.textContent.trim();
        }
        
        // 检查课程是否已满
        if (document.body.textContent.includes('已满') || 
            document.body.textContent.includes('人数已满')) {
            return 'course_full';
        }
        
        return 'unknown';
    })();
    """


def get_course_list_js():
    """获取当前页面的课程列表信息"""
    return """
    (function() {
        // TODO: 根据实际页面调整选择器
        var courses = [];
        var rows = document.querySelectorAll('.course-row, tbody tr');
        
        rows.forEach(function(row) {
            var nameCell = row.querySelector('.course-name') || row.cells[1];
            var teacherCell = row.querySelector('.teacher-name') || row.cells[2];
            var statusCell = row.querySelector('.course-status') || row.cells[3];
            var selectBtn = row.querySelector('.select-btn') || row.querySelector('button');
            
            if (nameCell) {
                courses.push({
                    name: nameCell.textContent.trim(),
                    teacher: teacherCell ? teacherCell.textContent.trim() : '',
                    status: statusCell ? statusCell.textContent.trim() : '',
                    available: selectBtn ? !selectBtn.disabled : false
                });
            }
        });
        
        return JSON.stringify(courses);
    })();
    """
