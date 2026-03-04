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

// Get latest news
async function getLatestNews(limit = 100) {
    try {
        const rows = await all('SELECT * FROM news ORDER BY created_at DESC LIMIT ?', [limit]);
        return rows.map(row => {
            try {
                const data = JSON.parse(row.raw_data);
                return { ...data, ...row }; // Merge, preferring column values
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
    getLatestNews,
    getNewsBySource,
    getUnanalyzedNews,
    saveAnalysis,
    db // Export db instance if needed elsewhere
};
