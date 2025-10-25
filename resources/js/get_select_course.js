// 选课核心逻辑（示例）
(function() {
    // TODO: 替换为实际选择器
    var rows = document.querySelectorAll('#course-table .course-row');
    for (var i = 0; i < rows.length; i++) {
        var btn = rows[i].querySelector('.btn-select');
        if (btn) {
            btn.click();
            return 'success';
        }
    }
    return 'course_not_found';
})();
