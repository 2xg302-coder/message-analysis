const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, 'news.db');
const db = new sqlite3.Database(DB_PATH);

db.serialize(() => {
    // 1. 检查总数
    db.get("SELECT COUNT(*) as total FROM news", (err, row) => {
        console.log(`📊 数据库新闻总数: ${row.total}`);
    });

    // 2. 检查已分析的数量
    db.get("SELECT COUNT(*) as analyzed FROM news WHERE analysis IS NOT NULL", (err, row) => {
        console.log(`✅ 已完成分析: ${row.analyzed}`);
    });

    // 3. 检查待分析的数量
    db.get("SELECT COUNT(*) as pending FROM news WHERE analysis IS NULL", (err, row) => {
        console.log(`⏳ 等待分析: ${row.pending}`);
    });
    
    // 4. 查看最近一条被更新分析的新闻
    db.get("SELECT id, title, analyzed_at FROM news WHERE analysis IS NOT NULL ORDER BY analyzed_at DESC LIMIT 1", (err, row) => {
        if (row) {
            console.log(`\n🕒 最近一次分析时间: ${row.analyzed_at}`);
            console.log(`   新闻ID: ${row.id}`);
            console.log(`   标题: ${row.title}`);
        } else {
            console.log('\n⚠️ 尚未有任何新闻被分析 (可能是 Key 未配置或 Worker 未运行)');
        }
    });
});

db.close();
