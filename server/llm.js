require('dotenv').config();
const OpenAI = require('openai');

const apiKey = process.env.DEEPSEEK_API_KEY;
const baseURL = process.env.DEEPSEEK_BASE_URL || 'https://api.deepseek.com';

let client = null;

if (apiKey && apiKey !== 'sk-your-key-here') {
    client = new OpenAI({
        apiKey: apiKey,
        baseURL: baseURL
    });
} else {
    console.warn('⚠️ DeepSeek API Key not configured in .env file. Analysis will be skipped.');
}

async function analyzeNews(newsContent) {
    if (!client) {
        return { error: 'No API Key' };
    }

    const prompt = `
你是一个专业的金融分析师。请分析以下财经新闻，并提取关键信息。
新闻内容：
"${newsContent}"

请输出 JSON 格式，包含以下字段：
1. summary: 一句话摘要（不超过30字）。
2. sentiment: 情感倾向，枚举值: "positive" (利好), "negative" (利空), "neutral" (中性)。
3. score: 重要性评分 (0-10分)，10分表示重磅突发，0分表示无价值水文。
4. keywords: 关键词列表 (Array<String>)，提取公司名、行业名或核心事件。
5. impact: 简述对哪些行业或概念板块有直接影响。

请直接返回 JSON，不要包含 Markdown 格式标记。
`;

    try {
        const completion = await client.chat.completions.create({
            messages: [{ role: "user", content: prompt }],
            model: "deepseek-chat",
            temperature: 0.1,
            response_format: { type: "json_object" }
        });

        const result = completion.choices[0].message.content;
        return JSON.parse(result);
    } catch (error) {
        console.error('LLM Analysis Error:', error);
        return { error: error.message };
    }
}

module.exports = { analyzeNews };
