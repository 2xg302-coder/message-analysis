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

  try {
    const addedCount = await db.addNewsBatch(newsList);
    ctx.body = { success: true, received: newsList.length, added: addedCount };
  } catch (err) {
    console.error('Batch processing failed:', err);
    ctx.status = 500;
    ctx.body = { error: 'Batch processing failed' };
  }
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

// GET /api/stats - 获取统计数据
router.get('/api/stats', async (ctx) => {
  try {
    const stats = await db.getStats();
    ctx.body = { success: true, data: stats };
  } catch (err) {
    ctx.status = 500;
    ctx.body = { error: 'Failed to get stats' };
  }
});

// GET /api/series - 获取事件/连续剧列表
router.get('/api/series', async (ctx) => {
    try {
        const list = await db.getSeriesList();
        ctx.body = { success: true, count: list.length, data: list };
    } catch (err) {
        ctx.status = 500;
        ctx.body = { error: 'Failed to get series list' };
    }
});

// GET /api/series/:tag - 获取特定事件的新闻
router.get('/api/series/:tag', async (ctx) => {
    const tag = decodeURIComponent(ctx.params.tag);
    try {
        const news = await db.getNewsBySeries(tag);
        ctx.body = { success: true, count: news.length, data: news };
    } catch (err) {
        ctx.status = 500;
        ctx.body = { error: 'Failed to get series news' };
    }
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

// GET /api/analysis/status - 获取分析任务状态
router.get('/api/analysis/status', async (ctx) => {
    const { getAnalysisStatus } = require('./analyze');
    ctx.body = { success: true, data: getAnalysisStatus() };
});

// POST /api/analysis/control - 控制分析任务开关
router.post('/api/analysis/control', async (ctx) => {
    const { setAnalysisStatus } = require('./analyze');
    const { running } = ctx.request.body;
    if (typeof running !== 'boolean') {
        ctx.status = 400;
        ctx.body = { error: 'Invalid status' };
        return;
    }
    setAnalysisStatus(running);
    ctx.body = { success: true, running };
});
