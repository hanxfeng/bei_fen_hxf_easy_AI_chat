// --- 1. DOM 元素获取 ---
const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const loadHistoryBtn = document.getElementById('load-history-btn');
const typingIndicator = document.getElementById('typing-indicator');

// 设置弹窗相关
const settingsIcon = document.getElementById('settings-icon');
const settingsModal = document.getElementById('settings-modal');
const serverIpInput = document.getElementById('server-ip');
const serverTokenInput = document.getElementById('server-token');
const saveSettingsBtn = document.getElementById('save-settings');
const closeSettingsBtn = document.getElementById('close-settings');

// 头像设置相关
const aiAvatarInput = document.getElementById('ai-avatar-input');
const aiAvatarPreview = document.getElementById('ai-avatar-preview');
const userAvatarInput = document.getElementById('user-avatar-input');
const userAvatarPreview = document.getElementById('user-avatar-preview');


// --- 2. 全局变量和配置加载 ---

// 服务器配置
let serverUrl = localStorage.getItem('serverUrl') || '';
let serverToken = localStorage.getItem('serverToken') || '';
serverIpInput.value = serverUrl;
serverTokenInput.value = serverToken;

// 头像配置 (使用 Base64 Data URL 存储)
// 默认值指向你放在同目录下的图片
let aiAvatarSrc = localStorage.getItem('aiAvatarSrc') || 'default-ai.png';
let userAvatarSrc = localStorage.getItem('userAvatarSrc') || 'default-user.png';
aiAvatarPreview.src = aiAvatarSrc;
userAvatarPreview.src = userAvatarSrc;

// 用于智能显示时间戳
let lastMessageTimestamp = null;


// --- 3. 核心功能函数 ---

/**
 * [新功能] 智能时间戳格式化 (Req 2)
 * @param {Date} date - 消息的日期对象
 * @returns {string} 格式化后的时间字符串
 */
function formatTimestamp(date) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const startOfYear = new Date(now.getFullYear(), 0, 1);

    const hours = date.getHours();
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const period = hours < 12 ? '上午' : '下午';
    const displayHours = String(hours % 12 || 12); // 12小时制 (0点显示为12)
    const time = `${period} ${displayHours}:${minutes}`;

    if (date >= today) {
        // 今天的消息
        return time;
    } else if (date >= yesterday) {
        // 昨天的消息
        return `昨天 ${time}`;
    } else if (date >= startOfYear) {
        // 今年内、昨天前的消息
        return `${date.getMonth() + 1}月${date.getDate()}日 ${time}`;
    } else {
        // 往年的消息
        return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${time}`;
    }
}

/**
 * [重构] 向聊天窗口追加消息 (Req 2, 3)
 * @param {string} content - 消息内容
 * @param {string} role - 角色 ('user', 'ai', 或 'system')
 * @param {string|Date} timestampStr - 消息的时间戳 (可以是 Date 对象或 ISO 字符串)
 */
function appendMessage(content, role, timestampStr) {
    const timestamp = timestampStr ? new Date(timestampStr) : new Date();

    // 智能时间戳逻辑：如果与上一条消息间隔超过 5 分钟，则显示时间
    if (!lastMessageTimestamp || (timestamp - lastMessageTimestamp > 5 * 60 * 1000)) {
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'timestamp';
        timestampDiv.innerText = formatTimestamp(timestamp);
        chatContainer.appendChild(timestampDiv);
    }
    lastMessageTimestamp = timestamp; // 更新最后一条消息的时间

    // --- 创建消息行 (头像 + 气泡) ---
    const messageWrapper = document.createElement('div');
    messageWrapper.className = `message-wrapper ${role}-message`;

    // 1. 头像
    const avatarImg = document.createElement('img');
    avatarImg.className = 'avatar';
    if (role === 'user') {
        avatarImg.src = userAvatarSrc;
    } else if (role === 'ai') {
        avatarImg.src = aiAvatarSrc;
    }
    // 'system' 角色不添加头像

    // 2. 气泡
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.innerText = content;

    // 按角色组装
    if (role === 'user' || role === 'ai') {
        messageWrapper.appendChild(avatarImg);
    }
    messageWrapper.appendChild(messageContent);
    chatContainer.appendChild(messageWrapper);

    // 自动滚动到底部
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * [新功能] 处理头像文件选择 (Req 3)
 * @param {Event} event - input change 事件
 * @param {HTMLImageElement} previewElement - 用于预览的 img 元素
 * @param {string} storageKey - 存储在 localStorage 的键名
 */
function handleAvatarChange(event, previewElement, storageKey) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        const dataUrl = e.target.result;
        previewElement.src = dataUrl; // 更新预览
        localStorage.setItem(storageKey, dataUrl); // 保存到本地存储
        
        // 更新全局变量，以便新消息立即生效
        if (storageKey === 'userAvatarSrc') {
            userAvatarSrc = dataUrl;
        } else if (storageKey === 'aiAvatarSrc') {
            aiAvatarSrc = dataUrl;
        }
    };
    reader.readAsDataURL(file); // 读取为 Base64
}

/**
 * 显示系统错误消息
 * @param {string} message - 错误信息
 */
function showSystemError(message) {
    appendMessage(message, 'system', new Date());
}


// --- 4. 事件监听器 ---

// 发送消息
sendBtn.addEventListener('click', async () => {
    const text = messageInput.value.trim();
    if (!text) return;

    if (!serverUrl || !serverToken) {
        showSystemError("请先在设置中配置服务器地址和 Token");
        return;
    }

    // 1. 显示用户消息
    appendMessage(text, 'user', new Date());
    messageInput.value = '';

    // 2. [新功能] 显示 "正在输入" (Req 4)
    typingIndicator.style.display = 'block';
    chatContainer.scrollTop = chatContainer.scrollHeight; // 确保提示可见

    try {
        const response = await fetch(`${serverUrl}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${serverToken}`
            },
            body: JSON.stringify({ messages: text })
        });

        const data = await response.json();
        if (response.ok && data.response) {
            // 3. 显示 AI 回复
            // 假设服务器返回的数据中包含时间戳, 字段为 data.timestamp
            // 如果没有，则使用 new Date()
            appendMessage(data.response, 'ai', data.timestamp || new Date());
        } else {
            showSystemError("错误：" + (data.error || '未知错误'));
        }
    } catch (error) {
        showSystemError("请求失败：" + error.message);
    } finally {
        // 4. [新功能] 隐藏 "正在输入" (Req 4)
        typingIndicator.style.display = 'none';
    }
});

// 加载聊天记录
loadHistoryBtn.addEventListener('click', async () => {
    if (!serverUrl || !serverToken) {
        showSystemError("请先在设置中配置服务器地址和 Token");
        return;
    }

    typingIndicator.style.display = 'block'; // 显示加载中
    
    try {
        const response = await fetch(`${serverUrl}/get_chat_history`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${serverToken}`
            }
        });

        const data = await response.json();
        if (response.ok && data.history && Array.isArray(data.history)) {
            if (data.history.length === 0) {
                showSystemError("没有聊天记录");
            } else {
                chatContainer.innerHTML = ''; // 清空当前聊天
                lastMessageTimestamp = null; // 重置时间戳
                data.history.forEach(msg => {
                    // 假设历史记录 msg 对象有:
                    // msg.content (内容)
                    // msg.role ('user' 或 'ai')
                    // msg.timestamp (ISO 格式的时间戳)
                    appendMessage(msg.content, msg.role, msg.timestamp);
                });
            }
        } else {
            showSystemError(data.error || "加载历史记录失败");
        }
    } catch (error) {
        showSystemError("请求失败：" + error.message);
    } finally {
        typingIndicator.style.display = 'none';
    }
});


// --- 设置弹窗相关 ---
settingsIcon.addEventListener('click', () => {
    settingsModal.style.display = 'flex';
});

closeSettingsBtn.addEventListener('click', () => {
    settingsModal.style.display = 'none';
});

saveSettingsBtn.addEventListener('click', () => {
    serverUrl = serverIpInput.value.trim();
    serverToken = serverTokenInput.value.trim();
    localStorage.setItem('serverUrl', serverUrl);
    localStorage.setItem('serverToken', serverToken);
    
    settingsModal.style.display = 'none';
    showSystemError("设置已保存");
});

// 点击模态框外部关闭
settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        settingsModal.style.display = 'none';
    }
});

// [新功能] 头像上传监听
aiAvatarInput.addEventListener('change', (e) => handleAvatarChange(e, aiAvatarPreview, 'aiAvatarSrc'));
userAvatarInput.addEventListener('change', (e) => handleAvatarChange(e, userAvatarPreview, 'userAvatarSrc'));