// content.js
console.log('Sina Finance Collector loaded!');

// 用于存储已经处理过的 ID，避免重复 (Set 比 Array 更快)
const processedIds = new Set();

// 简单的提取函数
function extractNews(node) {
    if (!node) return;

    const id = node.dataset.id;
    if (!id || processedIds.has(id)) {
        return; // 已经处理过或者没有ID
    }

    const timeElement = node.querySelector('.bd_i_time_c');
    const contentElement = node.querySelector('.bd_i_txt_c');
    const linkElement = node.querySelector('.bd_i_txt_c a');

    if (timeElement && contentElement) {
        const content = contentElement.innerText.trim();
        
        // 尝试从内容中提取标题
        // 1. 如果有【】，提取括号内的内容作为标题
        // 2. 否则，截取前 50 个字符作为标题
        let title = '';
        const match = content.match(/【(.*?)】/);
        if (match && match[1]) {
            title = match[1];
        } else {
            title = content.length > 50 ? content.substring(0, 50) + '...' : content;
        }

        const newsItem = {
            id: id,
            title: title,
            content: content,
            timestamp: node.dataset.time, // 日期 (YYYYMMDD)
            time: timeElement.innerText.trim(), // 具体时间 (HH:MM:SS)
            link: linkElement ? linkElement.href : null,
            scrapedAt: new Date().toISOString(),
            source: 'sina'
        };

        console.log('📰 New News Detected:', newsItem);
        
        // 标记为已处理
        processedIds.add(id);

        // 发送给后端
        sendNewsToBackend(newsItem);
    }
}

// 发送新闻到后端 API (通过 Background Script)
function sendNewsToBackend(newsItem) {
    chrome.runtime.sendMessage({
        action: 'sendNews',
        data: newsItem
    }, (response) => {
        if (chrome.runtime.lastError) {
            console.error('❌ Error sending message to background:', chrome.runtime.lastError);
        } else if (response && response.success) {
            console.log('✅ Sent to backend via Background:', response.data);
        } else {
            console.error('❌ Error from Background:', response ? response.error : 'Unknown error');
        }
    });
}

// 1. 初始页面加载时，处理现有的新闻
function processExistingNews() {
    const newsNodes = document.querySelectorAll('.bd_i');
    console.log(`Found ${newsNodes.length} existing news items.`);
    newsNodes.forEach(node => extractNews(node));
}

// 2. 监听 DOM 变化，处理新加载的新闻 (MutationObserver)
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            mutation.addedNodes.forEach((node) => {
                // 检查节点是否是我们关心的新闻条目
                if (node.nodeType === 1 && node.classList && node.classList.contains('bd_i')) {
                    extractNews(node);
                }
                // 有时候可能会直接添加包含 .bd_i 的父容器，这里也可以深度遍历一下
                if (node.nodeType === 1 && node.querySelectorAll) {
                    const nestedNews = node.querySelectorAll('.bd_i');
                    nestedNews.forEach(extractNews);
                }
            });
        }
    });
});

// 启动监听
const targetNode = document.querySelector('.bd_list') || document.body;
if (targetNode) {
    observer.observe(targetNode, {
        childList: true,
        subtree: true
    });
    console.log('Observer started on', targetNode);
} else {
    console.error('Target node .bd_list not found!');
}

// 立即执行一次
processExistingNews();
