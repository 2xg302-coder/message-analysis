const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, 'news.db');
const db = new sqlite3.Database(DB_PATH);

db.all(`
    SELECT 
        substr(created_at, 1, 10) as date, 
        count(*) as count 
    FROM news 
    GROUP BY substr(created_at, 1, 10) 
    ORDER BY date DESC
`, (err, rows) => {
    if (err) {
        console.error(err);
    } else {
        console.log('📅 每日新闻收集量统计:');
        console.table(rows);
        
        if (rows.length > 0) {
            const total = rows.reduce((sum, r) => sum + r.count, 0);
            const avg = Math.round(total / rows.length);
            console.log(`\n📊 总计: ${total} 条, 平均: ${avg} 条/天`);
        } else {
            console.log('📭 数据库目前为空。');
        }
    }
    db.close();
});
