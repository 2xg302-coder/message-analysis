import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

// 获取新闻列表
// params: { limit, offset, type, min_impact, source }
export const getNews = (params) => {
    // Map frontend filter names to backend params
    const backendParams = {};
    if (params.type && params.type !== 'all') backendParams.type = params.type;
    
    // Handle importance (min_impact)
    // Frontend sends 'importance' which is a number (4, 6, 8) or 0 (all)
    // Or from high value toggle, it sends min_impact directly.
    if (params.min_impact) {
        backendParams.min_impact = params.min_impact;
    } else if (params.importance && params.importance > 0) {
        // Assume importance scale 1-5 mapping or direct.
        // User UI has 4, 6, 8 stars? Wait, UI shows 4, 6, 8.
        // Backend impact_score is 1-5 or 1-10? 
        // processor.py says: "impact_score": min(score, 10)
        // So backend is 1-10.
        backendParams.min_impact = params.importance;
    } else {
        // Default logic or no filter
    }
    
    return api.get('/news', { params: backendParams });
};

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
