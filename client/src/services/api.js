import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

// 添加请求拦截器以注入 API Key
api.interceptors.request.use((config) => {
  // 从环境变量获取 API Key (Vite 环境变量前缀必须为 VITE_)
  const apiKey = import.meta.env.VITE_API_SECRET;
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// 获取新闻列表
// params: { limit, offset, page, pageSize, type, min_impact, source, tag, sentiment, entity, keyword, startDate, endDate }
export const getNews = (params = {}) => {
  const backendParams = {};
  if (params.type && params.type !== 'all') backendParams.type = params.type;
  
  if (params.min_impact) {
      backendParams.min_impact = params.min_impact;
  }
  
  if (params.source) backendParams.source = params.source;
  if (params.tag) backendParams.tag = params.tag;
  const keyword = typeof params.keyword === 'string' ? params.keyword.trim() : '';
  if (keyword) backendParams.entity = keyword;
  else if (params.entity) backendParams.entity = params.entity;
  if (params.sentiment && params.sentiment !== 'all') backendParams.sentiment = params.sentiment;
  if (params.startDate) backendParams.start_date = params.startDate;
  if (params.endDate) backendParams.end_date = params.endDate;
  if (params.limit) backendParams.limit = params.limit;
  else if (params.pageSize) backendParams.limit = params.pageSize;

  if (params.offset !== undefined && params.offset !== null) backendParams.offset = params.offset;
  else if (params.page && backendParams.limit) backendParams.offset = (params.page - 1) * backendParams.limit;
  
  return api.get('/news', { params: backendParams });
};

// 获取统计数据
export const getStats = (startDate, endDate, excludeSource) => api.get('/stats', { params: { start_date: startDate, end_date: endDate, exclude_source: excludeSource } });

// 获取标签统计
export const getTagStats = (limit = 100, startDate, endDate) => api.get(`/stats/tags?limit=${limit}`, { params: { start_date: startDate, end_date: endDate } });

// 获取类型统计
export const getTypeStats = (startDate, endDate) => api.get('/stats/types', { params: { start_date: startDate, end_date: endDate } });

// 获取实体排行
export const getTopEntities = (limit = 50, startDate, endDate) => api.get(`/entities?limit=${limit}`, { params: { start_date: startDate, end_date: endDate } });

// 获取实体关系图谱
export const getEntityGraph = (hours = 24, force = false, type = 'cooccurrence') => api.get('/analysis/entity-graph', { params: { hours, force, type } });

// 获取分析任务状态
export const getAnalysisStatus = () => api.get('/analysis/status');

// 控制分析任务开关
export const setAnalysisControl = (running) => api.post('/analysis/control', { running });

export const getSeriesList = () => api.get('/series');
export const getSeriesNews = (tag) => api.get(`/series/${encodeURIComponent(tag)}`);
export const getRelatedSeries = (tag) => api.get(`/series/${encodeURIComponent(tag)}/related`);

export const getWatchlist = () => api.get('/watchlist');
export const updateWatchlist = (keywords) => api.post('/watchlist', { keywords });

// Calendar
export const getCalendarEvents = (date) => {
    if (date) {
        return api.get(`/calendar/date/${date}`);
    }
    return api.get('/calendar/today');
};
export const refreshCalendar = () => api.post('/calendar/refresh');

// Storylines
export const getActiveStorylines = () => api.get('/storylines/active');
export const getStorylinesByDate = (date) => api.get('/storylines', { params: { date } });
export const getHistoryStorylines = (limit = 50, offset = 0) => api.get('/storylines/history', { params: { limit, offset } });
export const generateStorylines = (date) => api.post(`/storylines/generate`, null, { params: { date } });
export const archiveStoryline = (id) => api.put(`/storylines/${id}/archive`);
export const getStorylineSeries = (seriesId) => api.get(`/storylines/series/${seriesId}`);
export const getAllSeries = (status = 'active') => api.get('/storylines/series', { params: { status } });
export const startBatchGeneration = (days = 7) => api.post('/storylines/batch-generate', null, { params: { days } });
export const getTaskStatus = (taskId) => api.get(`/storylines/tasks/${taskId}`);

// Daily Report
export const getDailyReport = (date) => api.get('/reports/daily', { params: { date } });

export const getMonitorStats = () => api.get('/monitor/stats');
export const getIngestionSources = () => api.get('/ingestion/sources');
export const setIngestionSourceEnabled = (source, enabled) => api.put(`/ingestion/sources/${encodeURIComponent(source)}`, { enabled });
export const scanDedupNews = (params) => api.get('/news/dedup/scan', { params });
export const deleteDedupNews = (ids) => api.post('/news/dedup/delete', { ids });

export default api;
