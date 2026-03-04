const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, 'news.db');
const db = new sqlite3.Database(DB_PATH);

function resetAnalysis() {
    const readline = require('readline').createInterface({
        input: process.stdin,
        output: process.stdout
    });

    console.log('⚠️  警告：此操作将清除所有已有的 AI 分析结果，以便使用新的逻辑重新分析。');
    console.log('数据本身不会被删除，仅重置 analysis 字段。');
    
    readline.question('确认要重置吗？(yes/no): ', (answer) => {
        if (answer.toLowerCase() === 'yes') {
            const sql = 'UPDATE news SET analysis = NULL, analyzed_at = NULL';
            
            db.run(sql, function(err) {
                if (err) {
                    console.error('❌ 重置失败:', err.message);
                } else {
                    console.log(`✅ 重置成功！共影响 ${this.changes} 条数据。`);
                    console.log('请重启 server 或等待 worker 自动处理这些新闻。');
                }
                db.close();
                process.exit(0);
            });
        } else {
            console.log('操作已取消。');
            db.close();
            process.exit(0);
        }
        readline.close();
    });
}

resetAnalysis();
