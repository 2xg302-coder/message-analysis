import React, { useEffect, useState } from 'react';
import { List, Card, Tag, Typography, Spin, message, Badge, Statistic, Row, Col, Space, Button, Tooltip, Radio, Divider } from 'antd';
import { getNews, getAnalysisStatus, setAnalysisControl, getStats } from '../services/api';
import Sidebar from '../components/Sidebar';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

const { Title, Paragraph, Text } = Typography;

const NewsFeed = () => {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
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
  const navigate = useNavigate();

  const fetchData = async () => {
    try {
      setLoading(true);
      const [newsRes, statsRes, statusRes] = await Promise.all([
        getNews(filters),
        getStats(),
        getAnalysisStatus()
      ]);

      if (newsRes.data && newsRes.data.data) {
        setNews(newsRes.data.data);
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
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // 降低刷新频率避免闪烁
    return () => clearInterval(interval);
  }, [filters]); // 依赖 filters 变化重新加载

  const handleFilterChange = (newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
    // 自动切换视图模式
    if (newFilters.type === 'flash') setViewMode('list');
    else if (newFilters.type === 'article') setViewMode('card');
  };

  const toggleAnalysis = async () => {
    try {
      const newStatus = !analysisStatus.running;
      await setAnalysisControl(newStatus);
      message.success(newStatus ? '分析任务已启动' : '分析任务已暂停');
      fetchData();
    } catch (error) {
      message.error('操作失败');
    }
  };

  // 获取边框颜色
  const getBorderColor = (item) => {
    const sentiment = item.sentiment_score || 0;
    const impact = item.impact_score || 0;

    if (sentiment > 0.5) return '#f5222d'; // 利好 (红)
    if (sentiment < -0.5) return '#52c41a'; // 利空 (绿)
    if (impact >= 4) return '#faad14'; // 重要 (黄)
    return undefined;
  };

  const renderFlashItem = (item) => (
    <List.Item style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
      <Row align="middle" style={{ width: '100%' }}>
        <Col span={3}>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {dayjs(item.created_at).format('HH:mm:ss')}
          </Text>
        </Col>
        <Col span={16}>
          <Text strong style={{ marginRight: 8 }}>{item.title}</Text>
          {item.tags && item.tags.map(tag => (
            <Tag key={tag} color="blue" style={{ fontSize: '10px', lineHeight: '18px' }}>{tag}</Tag>
          ))}
        </Col>
        <Col span={5} style={{ textAlign: 'right' }}>
           {item.sentiment_score > 0.5 && <Tag color="red">利好</Tag>}
           {item.sentiment_score < -0.5 && <Tag color="green">利空</Tag>}
           {item.impact_score >= 4 && <Tag color="gold">重要</Tag>}
        </Col>
      </Row>
    </List.Item>
  );

  const renderDeepItem = (item) => {
    const analysis = item.analysis || {};
    const hasAnalysis = !!item.analysis;
    const score = analysis.score || analysis.relevance_score;
    const borderColor = getBorderColor(item);

    return (
      <List.Item>
        <Card 
          title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '16px', fontWeight: 'bold' }}>
                {item.title || (item.content ? item.content.substring(0, 30) + '...' : '无标题')}
              </span>
              <Space>
                {item.sentiment_score && (
                   <Tag color={item.sentiment_score > 0 ? 'red' : (item.sentiment_score < 0 ? 'green' : 'default')}>
                     情感: {item.sentiment_score.toFixed(1)}
                   </Tag>
                )}
                {item.impact_score && (
                   <Tag color="gold">影响: {item.impact_score}</Tag>
                )}
              </Space>
            </div>
          }
          extra={<Text type="secondary">{dayjs(item.created_at).format('MM-DD HH:mm')}</Text>}
          hoverable
          style={{ 
            borderColor: borderColor,
            borderLeft: borderColor ? `4px solid ${borderColor}` : undefined 
          }}
        >
          {/* 摘要区域 */}
          {hasAnalysis && analysis.summary ? (
            <div style={{ marginBottom: 16, padding: '12px', background: '#f9f9f9', borderRadius: '4px' }}>
              <Text strong>📝 AI 摘要：</Text>
              <Text>{analysis.summary}</Text>
            </div>
          ) : null}

          {/* 标签和实体 */}
          <div style={{ marginBottom: 12 }}>
              {item.tags && item.tags.map(tag => <Tag key={tag} color="blue">#{tag}</Tag>)}
              {item.entities && item.entities.map((e, idx) => (
                <Tag key={idx} color="cyan">{e.name || e}</Tag>
              ))}
              {hasAnalysis && analysis.event_tag && (
                <Tag color="purple" style={{ cursor: 'pointer' }} onClick={() => navigate(`/series/${encodeURIComponent(analysis.event_tag)}`)}>
                  🎬 {analysis.event_tag}
                </Tag>
              )}
          </div>

          <Paragraph ellipsis={{ rows: 3, expandable: true, symbol: '展开全文' }} style={{ color: '#666' }}>
            {item.content}
          </Paragraph>
          
          <div style={{ marginTop: 10, display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#999' }}>
            <span>来源: {item.source || '未知'}</span>
          </div>
        </Card>
      </List.Item>
    );
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* 顶部统计和控制栏 - 保持不变 */}
      <Card style={{ marginBottom: 24 }} bodyStyle={{ padding: '16px 24px' }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Space size="large">
              <Statistic title="新闻总量" value={stats.total} prefix="📰" />
              <Statistic title="待分析" value={stats.pending} prefix="⏳" valueStyle={{ color: stats.pending > 0 ? '#fa8c16' : undefined }} />
              <Statistic title="高价值新闻" value={stats.high_score} prefix="💎" valueStyle={{ color: '#f5222d' }} />
              <Statistic title="活跃事件" value={stats.active_series} prefix="🔥" />
            </Space>
          </Col>
          <Col>
            <Space direction="vertical" align="end">
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
            <Radio.Group value={viewMode} onChange={e => setViewMode(e.target.value)} buttonStyle="solid">
              <Radio.Button value="list">快讯模式</Radio.Button>
              <Radio.Button value="card">深度模式</Radio.Button>
            </Radio.Group>
          </div>

          <Spin spinning={loading}>
            <List
              grid={viewMode === 'card' ? { gutter: 16, column: 1 } : undefined}
              dataSource={news}
              pagination={{ pageSize: 10, showSizeChanger: true, showQuickJumper: true }}
              renderItem={viewMode === 'list' ? renderFlashItem : renderDeepItem}
            />
          </Spin>
        </Col>
      </Row>
    </div>
  );
};

export default NewsFeed;
