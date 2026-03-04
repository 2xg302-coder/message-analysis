const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, 'news.db');

// Create a database connection
const db = new sqlite3.Database(DB_PATH, (err) => {
    if (err) {
        console.error('Error opening database', err.message);
    } else {
        console.log('Connected to the SQLite database.');
        initTable();
    }
});

// Initialize the table
function initTable() {
    const sql = `
        CREATE TABLE IF NOT EXISTS news (
            id TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            content TEXT,
            time TEXT,
            timestamp TEXT,
            scraped_at TEXT,
            created_at TEXT,
            source TEXT,
            raw_data TEXT,
            analysis TEXT,
            analyzed_at TEXT
        )
    `;
    
    db.run(sql, (err) => {
        if (err) {
            console.error('Error creating table', err.message);
        } else {
            console.log('Table "news" is ready.');
        }
    });
}

// Helper to wrap db.run in a promise
function run(sql, params = []) {
    return new Promise((resolve, reject) => {
        db.run(sql, params, function (err) {
            if (err) {
                console.error('Error running sql ' + sql);
                console.error(err);
                reject(err);
            } else {
                resolve({ id: this.lastID, changes: this.changes });
            }
        });
    });
}

// Helper to wrap db.get in a promise
function get(sql, params = []) {
    return new Promise((resolve, reject) => {
        db.get(sql, params, (err, result) => {
            if (err) {
                console.error('Error running sql: ' + sql);
                console.error(err);
                reject(err);
            } else {
                resolve(result);
            }
        });
    });
}

// Helper to wrap db.all in a promise
function all(sql, params = []) {
    return new Promise((resolve, reject) => {
        db.all(sql, params, (err, rows) => {
            if (err) {
                console.error('Error running sql: ' + sql);
                console.error(err);
                reject(err);
            } else {
                resolve(rows);
            }
        });
    });
}

// Add a news item
async function addNews(newsItem) {
    if (!newsItem || !newsItem.id) return false;

    // Check if exists
    try {
        console.log(`Checking existence for ID: ${newsItem.id}`);
        const existing = await get('SELECT id FROM news WHERE id = ?', [newsItem.id]);
        if (existing) {
            console.log(`ID ${newsItem.id} already exists.`);
            return false; // Already exists
        }
        
        console.log(`ID ${newsItem.id} does not exist. Inserting...`);

        const record = {
            ...newsItem,
            created_at: new Date().toISOString()
        };

        const sql = `
            INSERT INTO news (id, title, link, content, time, timestamp, scraped_at, created_at, source, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `;
        
        await run(sql, [
            record.id,
            record.title || '',
            record.link || '',
            record.content || '',
            record.time || '',
            record.timestamp || '',
            record.scrapedAt || '', 
            record.created_at,
            record.source || 'unknown',
            JSON.stringify(record)
        ]);

        return true;
    } catch (err) {
        console.error('Error adding news:', err);
        return false;
    }
}

// Add multiple news items in a transaction
async function addNewsBatch(newsList) {
    if (!Array.isArray(newsList) || newsList.length === 0) return 0;

    let addedCount = 0;
    
    try {
        await run('BEGIN TRANSACTION');
        
        for (const newsItem of newsList) {
            if (!newsItem || !newsItem.id) continue;

            // Check existence (using get helper inside transaction is fine)
            const existing = await get('SELECT id FROM news WHERE id = ?', [newsItem.id]);
            if (existing) {
                continue; 
            }

            const record = {
                ...newsItem,
                created_at: new Date().toISOString()
            };

            const sql = `
                INSERT INTO news (id, title, link, content, time, timestamp, scraped_at, created_at, source, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `;

            await run(sql, [
                record.id,
                record.title || '',
                record.link || '',
                record.content || '',
                record.time || '',
                record.timestamp || '',
                record.scrapedAt || '', 
                record.created_at,
                record.source || 'unknown',
                JSON.stringify(record)
            ]);
            
            addedCount++;
        }

        await run('COMMIT');
        return addedCount;
    } catch (err) {
        console.error('Error in batch add:', err);
        await run('ROLLBACK');
        throw err;
    }
}

// Get latest news
async function getLatestNews(limit = 1000) {
    try {
        const rows = await all('SELECT * FROM news ORDER BY created_at DESC LIMIT ?', [limit]);
        return rows.map(row => {
            try {
                const data = JSON.parse(row.raw_data);
                // 优先使用 analysis 列中的数据，如果已存在
                let analysis = null;
                if (row.analysis) {
                    analysis = JSON.parse(row.analysis);
                }
                
                return { 
                    ...data, 
                    ...row, 
                    analysis: analysis // 明确解析 analysis 字段
                }; 
            } catch (e) {
                return row;
            }
        });
    } catch (err) {
        console.error('Error getting latest news:', err);
        return [];
    }
}

async function getNewsBySource(source, limit = 100) {
    try {
        const rows = await all('SELECT * FROM news WHERE source = ? ORDER BY created_at DESC LIMIT ?', [source, limit]);
        return rows.map(row => {
            try {
                const data = JSON.parse(row.raw_data);
                return { ...data, ...row };
            } catch (e) {
                return row;
            }
        });
    } catch (err) {
        console.error('Error getting news by source:', err);
        return [];
    }
}

async function getUnanalyzedNews(limit = 10) {
    try {
        const rows = await all('SELECT * FROM news WHERE analysis IS NULL ORDER BY created_at ASC LIMIT ?', [limit]);
        return rows.map(row => {
            try {
                const data = JSON.parse(row.raw_data);
                return { ...data, ...row };
            } catch (e) {
                return row;
            }
        });
    } catch (err) {
        console.error('Error getting unanalyzed news:', err);
        return [];
    }
}

async function saveAnalysis(id, analysisResult) {
    try {
        const sql = 'UPDATE news SET analysis = ?, analyzed_at = ? WHERE id = ?';
        await run(sql, [JSON.stringify(analysisResult), new Date().toISOString(), id]);
        return true;
    } catch (err) {
        console.error('Error saving analysis:', err);
        return false;
    }
}

module.exports = {
    addNews,
    addNewsBatch,
    getLatestNews,
    getNewsBySource,
    getUnanalyzedNews,
    saveAnalysis,
    getStats,
    db // Export db instance if needed elsewhere
};

async function getStats() {
    try {
        const total = await get('SELECT COUNT(*) as count FROM news');
        const analyzed = await get('SELECT COUNT(*) as count FROM news WHERE analysis IS NOT NULL');
        const pending = total.count - analyzed.count;

        // 获取最近1000条新闻进行更细致的内存统计
        const rows = await all('SELECT analysis FROM news WHERE analysis IS NOT NULL ORDER BY created_at DESC LIMIT 1000');
        let highScoreCount = 0;
        const seriesSet = new Set();
        
        rows.forEach(row => {
            try {
                const analysis = JSON.parse(row.analysis);
                if (analysis) {
                    // 兼容 score 和 relevance_score
                    const score = analysis.score || analysis.relevance_score || 0;
                    if (score >= 7) highScoreCount++;
                    if (analysis.event_tag) seriesSet.add(analysis.event_tag);
                }
            } catch (e) {}
        });

        // 简单的趋势数据模拟
        const trends = await all(`
            SELECT 
                substr(created_at, 12, 2) as hour, 
                count(*) as count 
            FROM news 
            GROUP BY hour 
            ORDER BY hour DESC 
            LIMIT 12
        `);

        return {
            total: total.count,
            analyzed: analyzed.count,
            pending: pending,
            high_score: highScoreCount,
            active_series: seriesSet.size,
            trends: trends.reverse()
        };
    } catch (err) {
        console.error('Error getting stats:', err);
        return { total: 0, analyzed: 0, pending: 0, trends: [] };
    }
}

async function getSeriesList() {
    try {
        const rows = await all('SELECT analysis, created_at FROM news WHERE analysis IS NOT NULL AND analysis LIKE \'%"event_tag"%\' ORDER BY created_at DESC LIMIT 2000');
        const seriesMap = new Map();

        rows.forEach(row => {
            try {
                const analysis = JSON.parse(row.analysis);
                if (analysis && analysis.event_tag) {
                    const tag = analysis.event_tag;
                    if (!seriesMap.has(tag)) {
                        seriesMap.set(tag, { 
                            tag, 
                            count: 0, 
                            latest_date: row.created_at,
                            sample_summary: analysis.summary
                        });
                    }
                    const item = seriesMap.get(tag);
                    item.count++;
                }
            } catch (e) {}
        });

        // 按最新时间排序
        return Array.from(seriesMap.values()).sort((a, b) => new Date(b.latest_date) - new Date(a.latest_date));
    } catch (err) {
        console.error('Error getting series list:', err);
        return [];
    }
}

async function getNewsBySeries(tag) {
    try {
        // 使用模糊查询初步筛选，然后在内存中精确过滤
        const rows = await all('SELECT * FROM news WHERE analysis LIKE ? ORDER BY created_at DESC', [`%${tag}%`]);
        return rows.map(row => {
            try {
                const data = JSON.parse(row.raw_data);
                let analysis = null;
                if (row.analysis) {
                    analysis = JSON.parse(row.analysis);
                }
                return { ...data, ...row, analysis }; 
            } catch (e) {
                return row;
            }
        }).filter(item => item.analysis && item.analysis.event_tag === tag);
    } catch (err) {
        console.error('Error getting news by series:', err);
        return [];
    }
}

module.exports = {
    addNews,
    addNewsBatch,
    getLatestNews,
    getNewsBySource,
    getUnanalyzedNews,
    saveAnalysis,
    getStats,
    getSeriesList,
    getNewsBySeries,
    db 
};
