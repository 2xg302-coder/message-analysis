import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

// 获取新闻列表
// params: { source, type, importance_min, sentiment_min, sentiment_max, entities }
export const getNews = (params) => api.get('/news', { params });

// 获取统计数据 (待后端实现)
export const getStats = () => api.get('/stats');

// 获取关注列表 (待后端实现)
export const getWatchlist = () => api.get('/watchlist');

// 更新关注列表 (待后端实现)
export const updateWatchlist = (data) => api.post('/watchlist', data);

// 获取分析任务状态
export const getAnalysisStatus = () => api.get('/analysis/status');

// 控制分析任务开关
export const setAnalysisControl = (running) => api.post('/analysis/control', { running });

// 获取事件/连续剧列表
export const getSeriesList = () => api.get('/series');

// 获取特定事件的新闻
export const getSeriesNews = (tag) => api.get(`/series/${encodeURIComponent(tag)}`);

export default api;
