const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, 'news.db');
const db = new sqlite3.Database(DB_PATH);

console.log('正在分析时间跨度和数据频率...\n');

db.all(`SELECT timestamp, COUNT(*) as count FROM news WHERE timestamp IS NOT NULL AND timestamp != '' GROUP BY timestamp ORDER BY timestamp ASC`, (err, rows) => {
    if (err) {
        console.error('查询失败:', err);
        return;
    }

    if (rows.length === 0) {
        console.log('❌ 数据库中没有有效的 timestamp 数据，无法进行时间跨度分析。');
        // 尝试用 created_at 兜底
        analyzeCreatedAt();
        return;
    }

    console.log('📅 基于 timestamp (YYYYMMDD) 的统计:');
    console.table(rows);

    const totalCount = rows.reduce((sum, row) => sum + row.count, 0);
    const validDays = rows.length;

    // 解析日期字符串 YYYYMMDD
    const parseDate = (str) => {
        const y = str.substring(0, 4);
        const m = str.substring(4, 6);
        const d = str.substring(6, 8);
        return new Date(`${y}-${m}-${d}`);
    };

    const firstDateStr = rows[0].timestamp;
    const lastDateStr = rows[rows.length - 1].timestamp;
    
    const firstDate = parseDate(firstDateStr);
    const lastDate = parseDate(lastDateStr);

    // 计算跨度天数 (毫秒差 / 一天的毫秒数) + 1 (包含当天)
    const timeSpanDays = Math.max(1, Math.round((lastDate - firstDate) / (1000 * 60 * 60 * 24)) + 1);

    console.log('\n📊 分析结果:');
    console.log(`- 总数据量: ${totalCount} 条`);
    console.log(`- 时间跨度: ${firstDateStr} 至 ${lastDateStr} (共 ${timeSpanDays} 天)`);
    console.log(`- 有数据的天数: ${validDays} 天`);
    
    const avgPerDay = Math.round(totalCount / timeSpanDays);
    const avgPerValidDay = Math.round(totalCount / validDays);

    console.log(`\n📈 估算日均量:`);
    console.log(`- 按跨度平均 (Total/Span): ${avgPerDay} 条/天`);
    if (timeSpanDays !== validDays) {
        console.log(`- 按活跃天平均 (Total/ActiveDays): ${avgPerValidDay} 条/天 (排除无数据日期)`);
    }

    // 估算每分钟/每小时
    const perHour = (avgPerDay / 24).toFixed(1);
    const perMinute = (avgPerDay / 1440).toFixed(2);
    
    console.log(`\n⏱️ 处理压力预估:`);
    console.log(`- 每小时: ~${perHour} 条`);
    console.log(`- 每分钟: ~${perMinute} 条`);

    if (perMinute > 60) {
        console.warn('\n⚠️ 警告: 数据量较大 (>1条/秒)，建议使用队列系统或批量处理。');
    } else {
        console.log('\n✅ 结论: 当前单线程轮询机制 (每5秒处理5条) 完全足够。');
    }

    db.close();
});

function analyzeCreatedAt() {
    console.log('\n尝试使用 created_at 分析 (仅供参考)...');
    db.all(`SELECT substr(created_at, 1, 10) as date, COUNT(*) as count FROM news GROUP BY date ORDER BY date ASC`, (err, rows) => {
        if (err) { console.error(err); return; }
        console.table(rows);
        db.close();
    });
}
