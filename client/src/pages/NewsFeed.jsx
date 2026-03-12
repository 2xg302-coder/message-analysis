import React, { useEffect, useState } from 'react';
import { Card, Typography, Spin, message, Badge, Statistic, Row, Col, Space, Button, Skeleton, Divider } from 'antd';
import { getNews, getAnalysisStatus, setAnalysisControl, getStats } from '../services/api';
import FilterBar from '../components/FilterBar';
import NewsFlash from '../components/NewsFlash';
import NewsCard from '../components/NewsCard';

const { Title, Text } = Typography;

const NewsFeed = () => {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [filters, setFilters] = useState({});
  const [viewMode, setViewMode] = useState('card'); // 'list' | 'card'
  const [stats, setStats] = useState({
    total: 0,
    analyzed: 0,
    pending: 0,
    high_score: 0,
    active_series: 0
  });
  const [analysisStatus, setAnalysisStatus] = useState({ running: false, current: null });
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  const [hasMore, setHasMore] = useState(true);

  const fetchNewsData = async (page, pageSize, currentFilters, isAppend = false) => {
    try {
      if (isAppend) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      
      const offset = (page - 1) * pageSize;
      const queryParams = {
        ...currentFilters,
        limit: pageSize,
        offset: offset
      };

      const [newsRes, statsRes, statusRes] = await Promise.all([
        getNews(queryParams),
        // Only fetch stats and status on first page load or refresh, not on load more? 
        // Actually lightweight enough to fetch always, or maybe just fetch news on load more.
        !isAppend ? getStats(null, null, 'ITHome') : Promise.resolve({}), 
        !isAppend ? getAnalysisStatus() : Promise.resolve({})
      ]);

      if (newsRes.data) {
        const list = Array.isArray(newsRes.data) ? newsRes.data : (newsRes.data.data || []);
        const total = newsRes.data.total || newsRes.data.count || (statsRes.data?.data?.total) || 0;
        
        if (isAppend) {
          setNews(prev => [...prev, ...list]);
        } else {
          setNews(list);
        }
        
        setPagination(prev => ({ ...prev, current: page, total }));
        // If we got fewer items than requested, no more data
        setHasMore(list.length === pageSize);
      }
      
      if (!isAppend) {
        if (statsRes.data && statsRes.data.data) {
          setStats(statsRes.data.data);
        }
        if (statusRes.data && statusRes.data.data) {
          setAnalysisStatus(statusRes.data.data);
        }
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
      message.error('获取数据失败');
    } finally {
      setLoading(false);
      setLoadingMore(false);
      setInitialLoading(false);
    }
  };

  // Initial load and filter change
  useEffect(() => {
    fetchNewsData(1, pagination.pageSize, filters, false);
  }, [filters, pagination.pageSize]);

  // Auto refresh (only if on first page and not loading)
  useEffect(() => {
    const interval = setInterval(() => {
      if (pagination.current === 1 && !loading && !loadingMore) {
        // Silent refresh for stats and first page
        // But we don't want to disrupt the user if they are reading.
        // Maybe just update stats?
        // For now, let's keep it simple: refresh if at top.
        fetchNewsData(1, pagination.pageSize, filters, false);
      }
    }, 30000); 
    return () => clearInterval(interval);
  }, [filters, pagination, loading, loadingMore]);

  const handleFilterChange = (newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
    // useEffect will trigger fetch
  };

  const handleLoadMore = () => {
    fetchNewsData(pagination.current + 1, pagination.pageSize, filters, true);
  };

  const handleRefresh = () => {
    fetchNewsData(1, pagination.pageSize, filters, false);
  };

  const toggleAnalysis = async () => {
    try {
      const newStatus = !analysisStatus.running;
      await setAnalysisControl(newStatus);
      message.success(newStatus ? '分析任务已启动' : '分析任务已暂停');
      // Refresh status immediately
      const statusRes = await getAnalysisStatus();
      if (statusRes.data && statusRes.data.data) {
        setAnalysisStatus(statusRes.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
      message.error('操作失败');
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* 顶部统计和控制栏 */}
      <Card style={{ marginBottom: 16 }} styles={{ body: { padding: '16px 24px' } }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Space size="large" wrap>
              <Statistic title="新闻总量" value={stats.total} prefix="📰" />
              <Statistic title="待分析" value={stats.pending} prefix="⏳" valueStyle={{ color: stats.pending > 0 ? '#fa8c16' : undefined }} />
              <Statistic title="高价值新闻" value={stats.high_score} prefix="💎" valueStyle={{ color: '#f5222d' }} />
              <Statistic title="活跃事件" value={stats.active_series} prefix="🔥" />
            </Space>
          </Col>
          <Col>
            <Space orientation="vertical" align="end">
              <Space>
                 <Badge status={analysisStatus.running ? 'processing' : 'default'} text={analysisStatus.running ? '分析任务运行中' : '分析任务已暂停'} />
                 <Button type={analysisStatus.running ? 'default' : 'primary'} onClick={toggleAnalysis} size="small">
                   {analysisStatus.running ? '暂停' : '启动'}
                 </Button>
              </Space>
              {analysisStatus.current && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  正在分析: {analysisStatus.current.title?.substring(0, 20)}...
                </Text>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 筛选栏 */}
      <FilterBar 
        filters={filters} 
        onFilterChange={handleFilterChange} 
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onRefresh={handleRefresh}
        loading={loading}
      />

      {/* 新闻列表 */}
      {initialLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {[1, 2, 3].map(i => (
            <Card key={i} style={{ width: '100%' }}>
              <Skeleton active avatar paragraph={{ rows: 2 }} />
            </Card>
          ))}
        </div>
      ) : (
        <Spin spinning={loading && news.length === 0}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: viewMode === 'card' ? '16px' : '0' }}>
            {news.map((item, index) => (
              <div key={item.id || index}>
                {viewMode === 'list' ? <NewsFlash item={item} /> : <NewsCard item={item} />}
              </div>
            ))}
          </div>

          {!loading && news.length === 0 && (
             <div style={{ textAlign: 'center', padding: '60px', color: '#999' }}>
               <Title level={4} style={{ color: '#ccc' }}>暂无相关新闻</Title>
               <Text type="secondary">请尝试调整筛选条件</Text>
             </div>
          )}

          {news.length > 0 && (
            <div style={{ marginTop: 24, textAlign: 'center', marginBottom: 24 }}>
              {hasMore ? (
                <Button onClick={handleLoadMore} loading={loadingMore} size="large">
                  加载更多新闻
                </Button>
              ) : (
                <Divider plain>没有更多了</Divider>
              )}
            </div>
          )}
        </Spin>
      )}
    </div>
  );
};

export default NewsFeed;
