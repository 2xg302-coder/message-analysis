import React, { useEffect, useState } from 'react';
import { Card, Typography, Spin, message, Badge, Statistic, Row, Col, Space, Button, Radio, Pagination, Skeleton } from 'antd';
import { getNews, getAnalysisStatus, setAnalysisControl, getStats } from '../services/api';
import Sidebar from '../components/Sidebar';
import NewsFlash from '../components/NewsFlash';
import NewsCard from '../components/NewsCard';

const { Title, Text } = Typography;

const NewsFeed = () => {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
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
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  const fetchData = async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      
      const { current, pageSize } = pagination;
      const offset = (current - 1) * pageSize;
      
      const queryParams = {
        ...filters,
        limit: pageSize,
        offset: offset
      };

      const [newsRes, statsRes, statusRes] = await Promise.all([
        getNews(queryParams),
        getStats(null, null, 'ITHome'), // Exclude ITHome from global stats
        getAnalysisStatus()
      ]);

      if (newsRes.data) {
        // 兼容不同的后端返回结构
        const list = Array.isArray(newsRes.data) ? newsRes.data : (newsRes.data.data || []);
        const total = newsRes.data.total || newsRes.data.count || statsRes.data?.data?.total || 0;
        
        setNews(list);
        setPagination(prev => ({ ...prev, total: total }));
      }
      
      if (statsRes.data && statsRes.data.data) {
        setStats(statsRes.data.data);
      }
      if (statusRes.data && statusRes.data.data) {
        setAnalysisStatus(statusRes.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
      message.error('获取数据失败');
    } finally {
      setLoading(false);
      setInitialLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // 仅在第一页时自动刷新，避免干扰用户翻页阅读
    const interval = setInterval(() => {
      if (pagination.current === 1) {
        fetchData(true);
      }
    }, 30000); 
    return () => clearInterval(interval);
  }, [filters, pagination.current, pagination.pageSize]); 

  const handleFilterChange = (newFilters) => {
    // Merge new filters and reset to page 1
    setFilters(prev => ({ ...prev, ...newFilters }));
    setPagination(prev => ({ ...prev, current: 1 }));
    
    // Auto switch view mode based on type
    if (newFilters.type === 'flash') setViewMode('list');
    else if (newFilters.type === 'article') setViewMode('card');
  };

  const toggleAnalysis = async () => {
    try {
      const newStatus = !analysisStatus.running;
      await setAnalysisControl(newStatus);
      message.success(newStatus ? '分析任务已启动' : '分析任务已暂停');
      fetchData(true);
    } catch (error) {
      message.error('操作失败');
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* 顶部统计和控制栏 */}
      <Card style={{ marginBottom: 24 }} styles={{ body: { padding: '16px 24px' } }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Space size="large">
              <Statistic title="新闻总量" value={stats.total} prefix="📰" />
              <Statistic title="待分析" value={stats.pending} prefix="⏳" styles={{ content: { color: stats.pending > 0 ? '#fa8c16' : undefined } }} />
              <Statistic title="高价值新闻" value={stats.high_score} prefix="💎" styles={{ content: { color: '#f5222d' } }} />
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

      <Row gutter={24}>
        {/* 左侧筛选栏 */}
        <Col span={6}>
          <Sidebar onFilterChange={handleFilterChange} loading={loading} />
        </Col>
        
        {/* 右侧列表 */}
        <Col span={18}>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={4} style={{ margin: 0 }}>实时情报流</Title>
            <Space>
               <Radio.Group 
                 value={filters.min_impact} 
                 onChange={e => handleFilterChange({ min_impact: e.target.value })} 
                 buttonStyle="solid"
               >
                 <Radio.Button value={undefined}>全部</Radio.Button>
                 <Radio.Button value={4}>🔥 高价值</Radio.Button>
               </Radio.Group>
               <Radio.Group value={viewMode} onChange={e => setViewMode(e.target.value)} buttonStyle="solid">
                 <Radio.Button value="list">快讯模式</Radio.Button>
                 <Radio.Button value="card">深度模式</Radio.Button>
               </Radio.Group>
            </Space>
          </div>

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
              <div style={{ marginTop: 16, textAlign: 'right' }}>
                <Pagination
                  current={pagination.current}
                  pageSize={pagination.pageSize}
                  total={pagination.total}
                  onChange={(page, pageSize) => setPagination(prev => ({ ...prev, current: page, pageSize }))}
                  showSizeChanger
                  showQuickJumper
                  showTotal={(total) => `共 ${total} 条`}
                />
              </div>
              {!loading && news.length === 0 && (
                 <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                   暂无相关新闻
                 </div>
              )}
            </Spin>
          )}
        </Col>
      </Row>
    </div>
  );
};

export default NewsFeed;
