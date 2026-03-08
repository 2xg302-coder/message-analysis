// ithome.js
console.log('ITHome News Collector loaded!');

// 存储已处理的新闻 ID，防止重复
const processedIds = new Set();

// 从本地存储加载已处理的 ID
chrome.storage.local.get(['ithome_news'], (result) => {
    if (result.ithome_news) {
        result.ithome_news.forEach(item => processedIds.add(item.link));
        console.log(`Loaded ${processedIds.size} processed news IDs from storage.`);
    }
});

// 保存新闻到本地存储
function saveNews(newsItem) {
    chrome.storage.local.get(['ithome_news'], (result) => {
        const newsList = result.ithome_news || [];
        // 检查是否已存在（双重检查）
        if (!newsList.some(item => item.link === newsItem.link)) {
            newsList.push(newsItem);
            chrome.storage.local.set({ ithome_news: newsList }, () => {
                console.log('✅ Saved locally:', newsItem.title);
            });
        }
    });
}

// 发送新闻到后端 (通过 Background Script)
function sendNewsToBackend(newsItem) {
    chrome.runtime.sendMessage({
        action: 'sendNews',
        data: newsItem
    }, (response) => {
        if (chrome.runtime.lastError) {
            console.error('❌ Error sending message to background:', chrome.runtime.lastError);
        } else if (response && response.success) {
            console.log('✅ Sent to backend via Background:', newsItem.title);
        } else {
            console.warn('⚠️ Backend rejected:', response ? response.error : 'Unknown error');
        }
    });
}

function extractIthomeNews(node) {
    if (!node) return;

    // 尝试获取标题和链接
    // 常见的结构是 h2 > a 或者直接是 a
    const titleElement = node.querySelector('h2 a') || 
                         node.querySelector('.title a') || 
                         node.querySelector('a.title') || 
                         node.querySelector('a[target="_blank"]'); // 更宽泛的尝试

    const timeElement = node.querySelector('.time') || 
                        node.querySelector('.date') || 
                        node.querySelector('span.t') ||
                        node.querySelector('span.time');
    
    // 如果找不到标题，可能不是新闻项
    if (!titleElement) return;

    // 排除非文章链接 (例如广告、导航)
    const link = titleElement.href;
    if (!link || link.includes('javascript:') || !link.includes('.htm')) return;

    const title = titleElement.innerText.trim();
    if (!title) return;
    
    // 生成一个简单的 ID (基于链接)
    const id = link;

    if (processedIds.has(id)) return;

    // 尝试解析日期和时间
    // IT之家的时间格式通常是 "20:30" 或 "02-24" 或 "刚刚"
    // 我们需要将其标准化为 YYYYMMDD 和 HH:MM:SS
    const now = new Date();
    let timestamp = now.toISOString().slice(0, 10).replace(/-/g, ''); // YYYYMMDD
    let time = now.toTimeString().slice(0, 8); // HH:MM:SS

    if (timeElement) {
        const timeText = timeElement.innerText.trim();
        // 如果是 HH:MM 格式 (今天)
        if (/^\d{1,2}:\d{2}$/.test(timeText)) {
            time = timeText + ':00';
        }
        // 如果是 MM-DD 格式 (往期)
        else if (/^\d{1,2}-\d{1,2}$/.test(timeText)) {
            // 假设是今年
            const [month, day] = timeText.split('-');
            timestamp = `${now.getFullYear()}${month.padStart(2, '0')}${day.padStart(2, '0')}`;
            time = '00:00:00'; // 往期新闻可能没有具体时间
        }
    }

    const newsItem = {
        id: id,
        title: title,
        content: title, // 列表页只有标题，暂时用标题充当内容
        link: link,
        timestamp: timestamp,
        time: time,
        scrapedAt: new Date().toISOString(),
        source: 'ITHome'
    };

    console.log('📰 New ITHome News Detected:', newsItem);
    processedIds.add(id);
    saveNews(newsItem);
    sendNewsToBackend(newsItem);
}

function processExistingNews() {
    // 尝试多种常见的列表选择器
    const selectors = [
        '.nl li',            // 首页常见结构 (ul.nl > li.n)
        '.new-list li',      // 列表页
        '.bl li',            // Block List
        'ul.newslist li',
        '.post-list li',
        '#list li',          // 移动端可能用到
        '.list-box li',      // 新版列表容器
        '.news-box li',
        '#newslist li'
    ];

    let found = false;
    for (const selector of selectors) {
        const nodes = document.querySelectorAll(selector);
        if (nodes.length > 0) {
            console.log(`Found ${nodes.length} items using selector: ${selector}`);
            nodes.forEach(node => extractIthomeNews(node));
            found = true;
            // 如果找到一种匹配的结构，通常不需要再试其他的，但也可能有多个区域
            // 这里为了保险，我们可以继续尝试，或者只处理找到的第一个有效列表
        }
    }

    if (!found) {
        console.warn('No news items found with common selectors. Trying generic search...');
        // 备用方案：查找所有包含 h2 和 a 的 li 元素
        const listItems = document.querySelectorAll('li, .news-item, .article');
        listItems.forEach(item => {
            if (item.querySelector('h2 a') || item.querySelector('.title')) {
                extractIthomeNews(item);
            }
        });
    }
}

// 监听动态加载的内容
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.addedNodes.length > 0) {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) { // ELEMENT_NODE
                    // 检查节点本身
                    extractIthomeNews(node);
                    
                    // 检查子节点
                    const nestedItems = node.querySelectorAll('li, .news-item, .article');
                    nestedItems.forEach(extractIthomeNews);
                }
            });
        }
    });
});

// 启动监听
const targetNode = document.body;
if (targetNode) {
    observer.observe(targetNode, {
        childList: true,
        subtree: true
    });
}

// 初始执行
// 延迟一点执行，确保页面基本加载完成
setTimeout(processExistingNews, 1000);
