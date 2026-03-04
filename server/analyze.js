const { analyzeNews } = require('./llm');
const db = require('./database');

let isRunning = true;
let currentTask = null; // { id, title, status, startTime }

function setAnalysisStatus(status) {
    isRunning = status;
    console.log(`Analysis Worker status changed to: ${isRunning ? 'RUNNING' : 'PAUSED'}`);
}

function getAnalysisStatus() {
    return {
        isRunning,
        currentTask
    };
}

// 主循环
async function startWorker() {
    console.log('🚀 Analysis Worker Started...');

    // 等待数据库初始化完成
    await new Promise(r => setTimeout(r, 2000));

    while (true) {
        if (!isRunning) {
            currentTask = null;
            await new Promise(r => setTimeout(r, 1000));
            continue;
        }

        try {
            // 获取未分析的新闻 (每次取 1 条，以便实时更新状态)
            const newsList = await db.getUnanalyzedNews(1);
            
            if (newsList.length > 0) {
                const news = newsList[0];
                
                // 更新当前任务状态
                currentTask = {
                    id: news.id,
                    title: news.title || news.content.substring(0, 30),
                    status: 'analyzing',
                    startTime: new Date().toISOString()
                };

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
                        isRunning = false; // 自动暂停
                        currentTask = { ...currentTask, status: 'error', error: 'Missing API Key' };
                        break; 
                    }
                } else {
                    // 保存结果到数据库
                    await db.saveAnalysis(news.id, analysis);
                    console.log(`✅ Analyzed ${news.id}: Tag=${analysis.event_tag || 'N/A'}, Score=${analysis.score}`);
                }
                
                // 任务完成，短暂保留状态以便前端能看到
                currentTask = null;
                
                // 避免触发 API 速率限制 (Rate Limit)
                await new Promise(r => setTimeout(r, 1000)); 
            } else {
                currentTask = null;
            }
        } catch (err) {
            console.error('Analysis loop error:', err);
            currentTask = null;
        }

        // 检查间隔
        await new Promise(r => setTimeout(r, 2000));
    }
}

// 如果直接运行此脚本
if (require.main === module) {
    startWorker();
}

module.exports = { startWorker, setAnalysisStatus, getAnalysisStatus };
