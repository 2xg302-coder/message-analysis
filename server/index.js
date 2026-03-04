const Koa = require('koa');
const Router = require('@koa/router');
const bodyParser = require('koa-bodyparser');
const cors = require('@koa/cors');
const db = require('./database');

const app = new Koa();
const router = new Router();

// 1. 中间件
app.use(cors()); // 允许跨域请求 (这样Chrome插件才能POST数据)
app.use(bodyParser()); // 解析 JSON 请求体

// 2. 路由定义

// POST /api/news - 接收单条新闻
router.post('/api/news', async (ctx) => {
  const newsItem = ctx.request.body;
  if (!newsItem || !newsItem.id) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid news data' };
    return;
  }

  const added = await db.addNews(newsItem);
  console.log(`[News] [${newsItem.source || 'unknown'}] Received: ${newsItem.title || newsItem.content.substring(0, 20)}...`);
  ctx.body = { success: true, added };
});

// POST /api/news/batch - 接收批量新闻
router.post('/api/news/batch', async (ctx) => {
  const newsList = ctx.request.body;
  if (!Array.isArray(newsList)) {
    ctx.status = 400;
    ctx.body = { error: 'Expected an array of news' };
    return;
  }

  let addedCount = 0;
  for (const item of newsList) {
    if (await db.addNews(item)) {
      addedCount++;
    }
  }

  ctx.body = { success: true, received: newsList.length, added: addedCount };
});

// GET /api/news - 获取最近的新闻 (用于测试)
router.get('/api/news', async (ctx) => {
  const source = ctx.query.source;
  let news;
  if (source) {
    news = await db.getNewsBySource(source);
  } else {
    news = await db.getLatestNews();
  }
  ctx.body = { count: news.length, data: news };
});

// GET /api/stats - 获取统计数据 (Mock)
router.get('/api/stats', async (ctx) => {
  // Mock data for trends
  const data = [
    { name: '08:00', sentiment: 40, heat: 24 },
    { name: '09:00', sentiment: 30, heat: 13 },
    { name: '10:00', sentiment: 20, heat: 98 },
    { name: '11:00', sentiment: 27, heat: 39 },
    { name: '12:00', sentiment: 18, heat: 48 },
    { name: '13:00', sentiment: 23, heat: 38 },
    { name: '14:00', sentiment: 34, heat: 43 },
  ];
  ctx.body = { success: true, data };
});

// GET /api/watchlist - 获取关注列表 (Mock)
router.get('/api/watchlist', async (ctx) => {
  // Mock watchlist
  const watchlist = ['半导体', '人工智能', '新能源'];
  ctx.body = { success: true, data: watchlist };
});

// POST /api/watchlist - 更新关注列表 (Mock)
router.post('/api/watchlist', async (ctx) => {
  const { keywords } = ctx.request.body;
  console.log('Updated watchlist:', keywords);
  ctx.body = { success: true };
});

// 3. 启动服务
app.use(router.routes()).use(router.allowedMethods());

const PORT = 3001;
app.listen(PORT, () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
  
  // 启动后台分析任务
  const { startWorker } = require('./analyze');
  startWorker().catch(err => console.error('Analysis Worker Error:', err));
});
