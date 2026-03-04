const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');

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

const readline = require('readline');

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
            migrateData();
            normalizeData(); // Add normalization step
        }
    });
}

// Normalize existing data (fill missing fields from raw_data or infer them)
async function normalizeData() {
    try {
        console.log('Checking for data normalization...');
        
        // 1. Fix missing titles for 'sina' source (extract from content)
        const sinaRows = await all('SELECT id, content, raw_data FROM news WHERE source = "sina" AND (title IS NULL OR title = "")');
        if (sinaRows.length > 0) {
            console.log(`Normalizing ${sinaRows.length} Sina items...`);
            for (const row of sinaRows) {
                let title = '';
                const content = row.content || '';
                const match = content.match(/【(.*?)】/);
                if (match && match[1]) {
                    title = match[1];
                } else {
                    title = content.length > 50 ? content.substring(0, 50) + '...' : content;
                }
                await run('UPDATE news SET title = ? WHERE id = ?', [title, row.id]);
            }
        }

        // 2. Fix missing content for 'ithome' source (copy from title)
        const ithomeRows = await all('SELECT id, title FROM news WHERE source = "ithome" AND (content IS NULL OR content = "")');
        if (ithomeRows.length > 0) {
            console.log(`Normalizing ${ithomeRows.length} ITHome items...`);
            for (const row of ithomeRows) {
                await run('UPDATE news SET content = ? WHERE id = ?', [row.title, row.id]);
            }
        }
        
        // 3. Normalize timestamp/time format if needed (optional, depends on how bad the old data is)
        
        console.log('Data normalization complete.');
    } catch (err) {
        console.error('Data normalization failed:', err);
    }
}

async function migrateData() {
    const DB_FILE_JSONL = path.join(__dirname, 'news.jsonl');
    if (!fs.existsSync(DB_FILE_JSONL)) {
        return;
    }

    try {
        const row = await get('SELECT count(*) as count FROM news');
        if (row && row.count > 0) {
            console.log('Database already has data, skipping migration.');
            return;
        }

        console.log('Migrating data from news.jsonl...');
        const fileStream = fs.createReadStream(DB_FILE_JSONL);
        const rl = readline.createInterface({
            input: fileStream,
            crlfDelay: Infinity
        });

        let migratedCount = 0;
        for await (const line of rl) {
            if (line.trim()) {
                try {
                    const item = JSON.parse(line);
                    // Use addNews but without re-checking existence for speed if table is empty?
                    // Actually addNews is safe.
                    await addNews(item);
                    migratedCount++;
                } catch (e) {
                    console.error('Error parsing line during migration:', line);
                }
            }
        }
        console.log(`Migration complete. Migrated ${migratedCount} items.`);
    } catch (err) {
        console.error('Migration failed:', err);
    }
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
        const existing = await get('SELECT id FROM news WHERE id = ?', [newsItem.id]);
        if (existing) {
            return false; // Already exists
        }

        const record = {
            ...newsItem,
            created_at: new Date().toISOString()
        };

        const sql = `
            INSERT INTO news (id, title, link, content, time, timestamp, scraped_at, created_at, source, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `;
        
        // Debugging log
        // console.log('Inserting:', record.title, record.source);

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
                // Try to parse raw_data to get full object, or just return row
                // Returning row is safer as it matches the table schema
                // But let's check if we need to parse anything back?
                // For now, returning the row columns is fine.
                // We might want to parse raw_data if there are extra fields not in columns.
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
