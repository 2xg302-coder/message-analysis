const fs = require('fs');
const path = require('path');
const readline = require('readline');

const DB_FILE = path.join(__dirname, 'news.jsonl');

// 内存中的 ID 集合，用于快速去重
const idSet = new Set();
// 内存中的最新新闻缓存 (用于展示)
let newsCache = [];

// 初始化：读取文件，加载 ID
function init() {
    if (!fs.existsSync(DB_FILE)) {
        fs.writeFileSync(DB_FILE, '', 'utf8');
        return;
    }

    const fileStream = fs.createReadStream(DB_FILE);
    const rl = readline.createInterface({
        input: fileStream,
        crlfDelay: Infinity
    });

    rl.on('line', (line) => {
        if (line.trim()) {
            try {
                const item = JSON.parse(line);
                if (item.id) {
                    idSet.add(item.id);
                    newsCache.push(item);
                }
            } catch (e) {
                console.error('Error parsing line:', line);
            }
        }
    });

    rl.on('close', () => {
        console.log(`Database loaded. ${idSet.size} items found.`);
        // 只保留最近 100 条在内存缓存中
        newsCache = newsCache.slice(-100);
    });
}

init();

module.exports = {
    addNews: (newsItem) => {
        if (!newsItem || !newsItem.id) return false;
        
        // 去重
        if (idSet.has(newsItem.id)) {
            return false;
        }

        // 添加时间戳
        const record = {
            ...newsItem,
            created_at: new Date().toISOString()
        };

        // 写入文件 (追加模式)
        try {
            fs.appendFileSync(DB_FILE, JSON.stringify(record) + '\n', 'utf8');
            
            // 更新内存
            idSet.add(record.id);
            newsCache.unshift(record); // 加到开头
            if (newsCache.length > 100) newsCache.pop(); // 保持大小
            
            return true;
        } catch (err) {
            console.error('Write Error:', err);
            return false;
        }
    },

    getLatestNews: () => {
        return newsCache;
    }
};
