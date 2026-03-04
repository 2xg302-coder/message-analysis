const { analyzeNews } = require('./llm');
const db = require('./database');

// 主循环
async function startWorker() {
    console.log('🚀 Analysis Worker Started...');

    // 等待数据库初始化完成 (简单延时，或者假设 db 模块已经处理好了)
    // database.js 会在第一次 require 时开始初始化，虽然 migrateData 是 async 的，但通常很快
    // 这里等待几秒钟确保 migrate 完成
    await new Promise(r => setTimeout(r, 2000));

    while (true) {
        try {
            // 获取未分析的新闻 (每次取 5 条)
            const newsList = await db.getUnanalyzedNews(5);
            
            if (newsList.length > 0) {
                console.log(`Found ${newsList.length} unanalyzed news. Processing...`);
                
                for (const news of newsList) {
                    const content = news.content || news.title;
                    
                    if (!content) {
                        console.warn(`News ${news.id} has no content/title. Marking as skipped.`);
                        await db.saveAnalysis(news.id, { error: 'No content' });
                        continue;
                    }

                    console.log(`Analyzing news ${news.id}: ${content.substring(0, 20)}...`);
                    
                    // 调用 LLM
                    const analysis = await analyzeNews(content);
                    
                    if (analysis.error) {
                        console.error(`Skipping ${news.id} due to error: ${analysis.error}`);
                        
                        if (analysis.error === 'No API Key') {
                            console.warn('Please configure DEEPSEEK_API_KEY in server/.env');
                            await new Promise(r => setTimeout(r, 10000)); // 等 10 秒再重试
                            break; 
                        }
                        // 如果是其他错误，暂时不保存状态，以便重试
                    } else {
                        // 保存结果到数据库
                        await db.saveAnalysis(news.id, analysis);
                        console.log(`✅ Analyzed ${news.id}: Sentiment=${analysis.sentiment}, Score=${analysis.score}`);
                    }
                    
                    // 避免触发 API 速率限制 (Rate Limit)
                    await new Promise(r => setTimeout(r, 1000)); 
                }
            } else {
                // 没有新新闻，等待一会儿
                // console.log('No new news. Waiting...');
            }
        } catch (err) {
            console.error('Analysis loop error:', err);
        }

        // 每 5 秒检查一次
        await new Promise(r => setTimeout(r, 5000));
    }
}

// 如果直接运行此脚本
if (require.main === module) {
    startWorker();
}

module.exports = { startWorker };
