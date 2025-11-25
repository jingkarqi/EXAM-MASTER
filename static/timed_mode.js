// 定时模式倒计时功能
(function() {
    'use strict';

    // 获取倒计时元素
    const countdownElement = document.getElementById('countdown');
    const examForm = document.getElementById('examForm');

    if (!countdownElement) {
        console.error('倒计时元素未找到');
        return;
    }

    // 从元素文本中提取初始剩余时间
    let remainingTime = parseFloat(countdownElement.textContent.replace('秒', ''));

    if (isNaN(remainingTime) || remainingTime <= 0) {
        console.error('无效的剩余时间:', countdownElement.textContent);
        return;
    }

    console.log('初始剩余时间:', remainingTime, '秒');

    // 倒计时函数
    function updateCountdown() {
        remainingTime -= 0.1; // 每100毫秒减少0.1秒

        if (remainingTime <= 0) {
            remainingTime = 0;
            clearInterval(countdownInterval);

            // 时间到，自动提交表单
            if (examForm) {
                console.log('时间到，自动提交表单');
                examForm.submit();
            } else {
                console.error('表单元素未找到');
            }
        }

        // 更新显示
        countdownElement.textContent = remainingTime.toFixed(1) + '秒';

        // 添加视觉反馈
        if (remainingTime < 60) {
            countdownElement.style.color = '#dc3545'; // 红色
            countdownElement.style.fontWeight = 'bold';
        } else if (remainingTime < 180) {
            countdownElement.style.color = '#ffc107'; // 黄色
        } else {
            countdownElement.style.color = '#28a745'; // 绿色
        }
    }

    // 启动倒计时
    const countdownInterval = setInterval(updateCountdown, 100);

    // 页面卸载时清理定时器
    window.addEventListener('beforeunload', function() {
        clearInterval(countdownInterval);
    });

    // 表单提交时清理定时器
    if (examForm) {
        examForm.addEventListener('submit', function() {
            clearInterval(countdownInterval);
        });
    }

})();