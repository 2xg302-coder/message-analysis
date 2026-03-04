// content.js
console.log('Sina Finance Collector loaded! v2');

// 用于存储已经处理过的 ID，避免重复 (Set 比 Array 更快)
const processedIds = new Set();

// 简单的提取函数
function extractNews(node) {
    if (!node) return;

    // 优先尝试获取 data-id
    let id = node.dataset.id;
    
    // 兼容处理：如果没有 data-id，尝试从内容或链接中生成一个唯一ID (防止动态加载的DOM结构没有data-id)
    if (!id) {
        // 有些动态加载的元素可能结构不同，这里尝试寻找关键特征
        const linkElement = node.querySelector('.bd_i_txt_c a');
        if (linkElement && linkElement.href) {
            // 从链接中提取数字作为ID
            // 例如: https://finance.sina.com.cn/7x24/2025-03-04/doc-ixxxxxx.shtml -> ixxxxxx
            const match = linkElement.href.match(/\/doc-i(.*?).shtml/);
            if (match && match[1]) {
                id = match[1];
            } else {
                 // 链接做hash? 简单点直接用链接
                 id = linkElement.href;
            }
        }
    }

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

        console.log('📰 New News Detected:', id, title);
        
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

// 扫描所有新闻节点
function scanNews() {
    const newsNodes = document.querySelectorAll('.bd_i');
    // console.log(`Scanning... found ${newsNodes.length} items`);
    newsNodes.forEach(node => extractNews(node));
}

// 1. 初始页面加载时，处理现有的新闻
scanNews();

// 2. 监听 DOM 变化，处理新加载的新闻 (MutationObserver)
const observer = new MutationObserver((mutations) => {
    // 简单粗暴：只要有变化，就扫描一次。性能影响很小，但能确保不漏。
    scanNews();
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

// 3. 轮询兜底 (每3秒检查一次)
setInterval(scanNews, 3000);
