const { analyzeNews } = require('./llm');

// 模拟两条新闻：一条有价值，一条是垃圾信息
const sampleNews = [
    {
        id: 'test_1',
        content: `
        【重磅！宁德时代发布麒麟电池，续航突破1000公里！】
        今日，宁德时代（300750）正式发布第三代CTP技术——麒麟电池。
        据介绍，麒麟电池体积利用率突破72%，能量密度达255Wh/kg，轻松实现整车1000公里续航。
        将于2023年量产上市。受此消息影响，锂电池板块午后直线拉升，宁德时代涨超5%。
        `
    },
    {
        id: 'test_2',
        content: `
        想赚钱吗？加入我们的理财群！大师带你飞！
        加微信 123456789，免费领取牛股一只！
        今天大盘震荡，散户如何操作？点击链接查看详情...
        `
    }
];

async function runTest() {
    console.log('🔍 开始测试知识抽取功能...\n');

    for (const news of sampleNews) {
        console.log(`--------------------------------------------------`);
        console.log(`📰 原文片段: ${news.content.trim().substring(0, 50)}...`);
        console.log(`🤖 正在分析...`);
        
        const result = await analyzeNews(news.content);
        
        if (result.error) {
            console.error('❌ 分析失败:', result.error);
        } else {
            console.log('✅ 分析结果:');
            console.log(JSON.stringify(result, null, 2));
            
            if (result.relevance_score > 0) {
                console.log(`💡 [价值信息] 评分: ${result.score}, 事件: ${result.event_type}`);
            } else {
                console.log(`🗑️ [垃圾过滤] 已识别为无价值信息，原因: ${result.reasoning}`);
            }
        }
    }
}

runTest();
