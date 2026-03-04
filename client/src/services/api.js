import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

// 获取新闻列表
// source: 可选，新闻来源
export const getNews = (source) => api.get('/news', { params: { source } });

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
