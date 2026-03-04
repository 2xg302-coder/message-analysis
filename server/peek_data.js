const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, 'news.db');
const db = new sqlite3.Database(DB_PATH);

db.all(`SELECT id, title, time, timestamp, created_at FROM news LIMIT 5`, (err, rows) => {
    if (err) {
        console.error(err);
    } else {
        console.log('🔍 数据样例 (前5条):');
        console.table(rows);
    }
    db.close();
});
