/**
 * 导入题库功能前端交互逻辑
 * 提供文件上传、验证、预览等交互功能
 */

class ImportManager {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupDragDrop();
    }

    bindEvents() {
        // 文件选择事件
        const fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            input.addEventListener('change', (e) => this.handleFileSelect(e));
        });

        // 表单提交事件
        const uploadForm = document.getElementById('uploadForm');
        if (uploadForm) {
            uploadForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // 取消选择按钮
        const clearBtn = document.querySelector('.btn-secondary');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearFile());
        }

        // 题库模式切换
        this.bankModeRadios = document.querySelectorAll('input[name="target_mode"]');
        this.newBankFields = document.getElementById('newBankFields');
        this.existingBankSelect = document.getElementById('existingBankSelect');

        if (this.bankModeRadios.length > 0) {
            this.bankModeRadios.forEach(radio => {
                radio.addEventListener('change', () => this.handleBankModeChange());
            });
            this.handleBankModeChange();
        }
    }

    setupDragDrop() {
        const uploadArea = document.getElementById('uploadArea');
        if (!uploadArea) return;

        // 拖放事件
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            this.handleFileDrop(e);
        });
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.validateAndDisplayFile(file);
            this.syncFileInputs(event.target);
        }
    }

    handleFileDrop(event) {
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (this.allowedFile(file.name)) {
                this.setFileInputs(files);
                this.validateAndDisplayFile(file);
            } else {
                this.showError('只支持 CSV 和 TXT 格式的文件');
            }
        }
    }

    validateAndDisplayFile(file) {
        // 验证文件
        const validation = this.validateFile(file);
        if (!validation.valid) {
            this.showError(validation.message);
            return;
        }

        // 显示文件信息
        this.displayFileInfo(file);
    }

    validateFile(file) {
        // 检查文件类型
        if (!this.allowedFile(file.name)) {
            return {
                valid: false,
                message: '只支持 CSV 和 TXT 格式的文件'
            };
        }

        // 检查文件大小
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            return {
                valid: false,
                message: `文件大小不能超过 ${maxSize / 1024 / 1024}MB`
            };
        }

        // 检查文件是否为空
        if (file.size === 0) {
            return {
                valid: false,
                message: '文件不能为空'
            };
        }

        return { valid: true };
    }

    displayFileInfo(file) {
        const uploadArea = document.getElementById('uploadArea');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const fileType = document.getElementById('fileType');

        if (!uploadArea || !fileInfo || !fileName || !fileSize || !fileType) return;

        // 更新文件信息
        fileName.textContent = file.name;
        fileSize.textContent = this.formatFileSize(file.size);
        fileType.textContent = this.getFileType(file.name);

        // 显示文件信息，隐藏上传区域
        uploadArea.style.display = 'none';
        fileInfo.style.display = 'block';

        // 显示成功消息
        this.showSuccess('文件验证通过，可以开始上传');
    }

    clearFile() {
        // 清空文件输入
        const fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            input.value = '';
        });

        // 显示上传区域，隐藏文件信息
        const uploadArea = document.getElementById('uploadArea');
        const fileInfo = document.getElementById('fileInfo');

        if (uploadArea && fileInfo) {
            uploadArea.style.display = 'block';
            fileInfo.style.display = 'none';
        }

        // 清除消息
        this.clearMessages();
    }

    handleFormSubmit(event) {
        const fileInput = document.getElementById('formFileInput');
        if (!fileInput || !fileInput.files.length) {
            event.preventDefault();
            this.showError('请选择要上传的文件');
            return;
        }

        const selectedModeInput = document.querySelector('input[name="target_mode"]:checked');
        const selectedMode = selectedModeInput ? selectedModeInput.value : 'existing';
        if (selectedMode === 'existing') {
            if (!this.existingBankSelect || !this.existingBankSelect.value) {
                event.preventDefault();
                this.showError('请选择一个目标题库');
                return;
            }
        } else {
            const newBankNameInput = document.querySelector('input[name="new_bank_name"]');
            if (!newBankNameInput || !newBankNameInput.value.trim()) {
                event.preventDefault();
                this.showError('请填写新题库名称');
                return;
            }
        }

        // 显示加载遮罩
        this.showLoading();

        // 可以在这里添加额外的验证
        const file = fileInput.files[0];
        const validation = this.validateFile(file);
        if (!validation.valid) {
            event.preventDefault();
            this.hideLoading();
            this.showError(validation.message);
        }
    }

    syncFileInputs(sourceInput) {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            if (input !== sourceInput) {
                input.files = sourceInput.files;
            }
        });
    }

    setFileInputs(files) {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            input.files = files;
        });
    }

    allowedFile(filename) {
        const allowedExtensions = ['csv', 'txt'];
        const ext = filename.split('.').pop().toLowerCase();
        return allowedExtensions.includes(ext);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    getFileType(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        if (ext === 'csv') return 'CSV 文件';
        if (ext === 'txt') return '文本文件';
        return '未知文件';
    }

    showError(message) {
        this.showMessage(message, 'error');
    }

    showSuccess(message) {
        this.showMessage(message, 'success');
    }

    showMessage(message, type = 'info') {
        // 创建消息元素
        const messageEl = document.createElement('div');
        messageEl.className = `alert alert-${type} alert-dismissible fade show`;
        messageEl.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // 添加到页面
        const container = document.querySelector('.import-container') || document.body;
        container.insertBefore(messageEl, container.firstChild);

        // 自动移除
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.remove();
            }
        }, 5000);
    }

    clearMessages() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            if (alert.parentNode) {
                alert.remove();
            }
        });
    }

    showLoading() {
        const loadingMask = document.getElementById('loadingMask');
        if (loadingMask) {
            loadingMask.style.display = 'flex';
        }
    }

    hideLoading() {
        const loadingMask = document.getElementById('loadingMask');
        if (loadingMask) {
            loadingMask.style.display = 'none';
        }
    }

    handleBankModeChange() {
        const selectedModeInput = document.querySelector('input[name="target_mode"]:checked');
        const selectedMode = selectedModeInput ? selectedModeInput.value : 'existing';

        if (this.newBankFields) {
            this.newBankFields.style.display = selectedMode === 'new' ? 'block' : 'none';
        }

        if (this.existingBankSelect) {
            this.existingBankSelect.disabled = selectedMode === 'new';
        }
    }
}

// 预览页面功能
class PreviewManager {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.initFirstQuestion();
    }

    bindEvents() {
        // 展开/收起全部按钮
        const toggleAllBtn = document.querySelector('.btn-outline-secondary');
        if (toggleAllBtn) {
            toggleAllBtn.addEventListener('click', () => this.toggleAllQuestions());
        }

        // 题目头部点击事件
        const questionHeaders = document.querySelectorAll('.question-header');
        questionHeaders.forEach(header => {
            header.addEventListener('click', () => this.toggleQuestion(header));
        });
    }

    toggleQuestion(header) {
        const card = header.parentElement;
        const content = card.querySelector('.question-content');
        const toggleIcon = header.querySelector('.question-toggle i');

        if (content.style.display === 'none' || !content.style.display) {
            content.style.display = 'block';
            toggleIcon.classList.remove('fa-chevron-down');
            toggleIcon.classList.add('fa-chevron-up');
        } else {
            content.style.display = 'none';
            toggleIcon.classList.remove('fa-chevron-up');
            toggleIcon.classList.add('fa-chevron-down');
        }
    }

    toggleAllQuestions() {
        const cards = document.querySelectorAll('.question-preview-card');
        const firstCard = cards[0];
        const firstContent = firstCard.querySelector('.question-content');
        const isExpanded = firstContent.style.display === 'block' || !firstContent.style.display;

        cards.forEach(card => {
            const content = card.querySelector('.question-content');
            const toggleIcon = card.querySelector('.question-toggle i');

            if (isExpanded) {
                content.style.display = 'none';
                toggleIcon.classList.remove('fa-chevron-up');
                toggleIcon.classList.add('fa-chevron-down');
            } else {
                content.style.display = 'block';
                toggleIcon.classList.remove('fa-chevron-down');
                toggleIcon.classList.add('fa-chevron-up');
            }
        });
    }

    initFirstQuestion() {
        const firstCard = document.querySelector('.question-preview-card');
        if (firstCard) {
            const header = firstCard.querySelector('.question-header');
            this.toggleQuestion(header);
        }
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 导入页面
    if (document.querySelector('.import-container')) {
        new ImportManager();
    }

    // 预览页面
    if (document.querySelector('.preview-container')) {
        new PreviewManager();
    }
});

// 导出供其他脚本使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ImportManager, PreviewManager };
}
