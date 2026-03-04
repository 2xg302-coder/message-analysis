import React, { useEffect, useState } from 'react';
import { List, Card, Tag, Typography, Spin, message, Badge, Statistic, Row, Col, Space, Button, Tooltip } from 'antd';
import { getNews, getAnalysisStatus, setAnalysisControl, getStats } from '../services/api';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

const { Title, Paragraph, Text } = Typography;

const NewsFeed = () => {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
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
      const [newsRes, statsRes, statusRes] = await Promise.all([
        getNews(),
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
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

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

  const renderScore = (score) => {
    if (score === undefined || score === null) return null;
    let color = '#d9d9d9';
    if (score >= 8) color = '#f5222d';
    else if (score >= 5) color = '#fa8c16';
    else if (score > 0) color = '#1890ff';
    
    return (
      <Tooltip title={`AI 评分: ${score}/10`}>
        <Tag color={color}>评分: {score}</Tag>
      </Tooltip>
    );
  };

  return (
    <div style={{ padding: '24px' }}>
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

      <Title level={2}>实时情报流</Title>
      
      <Spin spinning={loading}>
        <List
          grid={{ gutter: 16, column: 1 }}
          dataSource={news}
          pagination={{ pageSize: 10, showSizeChanger: true, showQuickJumper: true }}
          renderItem={(item) => {
            const analysis = item.analysis || {};
            const hasAnalysis = !!item.analysis;
            const score = analysis.score || analysis.relevance_score;
            
            return (
              <List.Item>
                <Card 
                  title={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '16px', fontWeight: 'bold' }}>
                        {item.title || (item.content ? item.content.substring(0, 30) + '...' : '无标题')}
                      </span>
                      <div>
                        {hasAnalysis ? renderScore(score) : <Tag>待分析</Tag>}
                      </div>
                    </div>
                  }
                  extra={<Text type="secondary">{dayjs(item.created_at).format('MM-DD HH:mm')}</Text>}
                  hoverable
                  style={{ borderColor: (score >= 8) ? '#ffccc7' : undefined }}
                >
                  {hasAnalysis && analysis.summary ? (
                    <div style={{ marginBottom: 16, padding: '12px', background: '#f5f5f5', borderRadius: '4px', borderLeft: '4px solid #1890ff' }}>
                      <Text strong>📝 AI 摘要：</Text>
                      <Text>{analysis.summary}</Text>
                    </div>
                  ) : null}

                  {hasAnalysis && (
                    <div style={{ marginBottom: 12 }}>
                       {analysis.event_tag && (
                         <Tag color="purple" style={{ cursor: 'pointer' }} onClick={() => navigate(`/series/${encodeURIComponent(analysis.event_tag)}`)}>
                           🎬 {analysis.event_tag}
                         </Tag>
                       )}
                       {analysis.topic && <Tag color="blue">🏷️ {analysis.topic}</Tag>}
                       {analysis.entities && analysis.entities.map((e, idx) => (
                         <Tag key={idx}>{e.name}</Tag>
                       ))}
                    </div>
                  )}

                  <Paragraph ellipsis={{ rows: 2, expandable: true, symbol: '展开全文' }} style={{ color: '#666' }}>
                    {item.content}
                  </Paragraph>
                  
                  <div style={{ marginTop: 10, display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#999' }}>
                    <span>来源: {item.source || '未知'}</span>
                    {hasAnalysis && analysis.impact && (
                      <span style={{ color: '#d46b08' }}>⚠️ 影响: {analysis.impact}</span>
                    )}
                  </div>
                </Card>
              </List.Item>
            );
          }}
        />
      </Spin>
    </div>
  );
};

export default NewsFeed;
