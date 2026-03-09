import React, { useEffect, useState } from 'react';
import { Typography, Card, Row, Col, Statistic, Spin, Progress, Switch, Alert, Steps, Tag, Space, Modal, List, Empty } from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, ScatterChart, Scatter, ZAxis } from 'recharts';
import { getStats, getAnalysisStatus, setAnalysisControl, getNews, getTopEntities } from '../services/api';
import { RobotOutlined, PauseCircleOutlined, PlayCircleOutlined, FireOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;
const COLORS = ['#cf1322', '#fa8c16', '#1890ff', '#52c41a', '#722ed1'];

const Trends = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    analyzed: 0,
    high_score: 0,
    medium_score: 0,
    low_score: 0,
    trends: [],
    hot_entities: [], // 假设后端返回热点实体
    impact_sentiment_data: [] // 假设后端返回用于热力图的数据
  });
  
  // 分析任务状态
  const [analysisStatus, setAnalysisStatus] = useState({
    isRunning: true,
    currentTask: null
  });

  const [isModalVisible, setIsModalVisible] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [entityNews, setEntityNews] = useState([]);
  const [newsLoading, setNewsLoading] = useState(false);

  const handleEntityClick = async (entityName) => {
    setSelectedEntity(entityName);
    setIsModalVisible(true);
    setNewsLoading(true);
    setEntityNews([]);
    try {
      const res = await getNews({ entity: entityName, limit: 20 });
      if (res.data && res.data.data) {
        setEntityNews(res.data.data);
      }
    } catch (err) {
      console.error('Failed to fetch entity news', err);
    } finally {
      setNewsLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const [statsRes, entitiesRes] = await Promise.all([
        getStats(),
        getTopEntities(30)
      ]);
      
      let newStats = {};
      if (statsRes.data && statsRes.data.success) {
        newStats = { ...statsRes.data.data };
      }
      
      if (entitiesRes.data && entitiesRes.data.success) {
        // Map count to score for visualization
        // Find max count for normalization
        const maxCount = Math.max(...entitiesRes.data.data.map(e => e.count), 1);
        
        newStats.hot_entities = entitiesRes.data.data.map(e => ({
          name: e.name,
          score: (e.count / maxCount) * 100 // Normalize to 0-100
        }));
      }
      
      setStats(prev => ({ ...prev, ...newStats }));
    } catch (err) {
      console.error('Failed to fetch stats', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalysisStatus = async () => {
    try {
      const res = await getAnalysisStatus();
      if (res.data && res.data.success) {
        setAnalysisStatus(res.data.data);
      }
    } catch (err) {
      console.error('Failed to fetch analysis status', err);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchAnalysisStatus();
    
    const statusInterval = setInterval(fetchAnalysisStatus, 2000);
    const statsInterval = setInterval(fetchStats, 30000);
    
    return () => {
      clearInterval(statusInterval);
      clearInterval(statsInterval);
    };
  }, []);

  const handleToggleAnalysis = async (checked) => {
    try {
      await setAnalysisControl(checked);
      setAnalysisStatus(prev => ({ ...prev, isRunning: checked }));
    } catch (err) {
      console.error('Failed to toggle analysis', err);
    }
  };

  const scoreData = [
    { name: '高价值 (>=7)', value: stats.high_score || 0 },
    { name: '中等价值 (4-6)', value: stats.medium_score || 0 },
    { name: '低价值 (<=3)', value: stats.low_score || 0 }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>数据洞察与分析</Title>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Text strong>AI 分析任务：</Text>
          <Switch 
            checkedChildren={<PlayCircleOutlined />} 
            unCheckedChildren={<PauseCircleOutlined />} 
            checked={analysisStatus.isRunning} 
            onChange={handleToggleAnalysis} 
          />
        </div>
      </div>
      
      <Spin spinning={loading}>
        {/* 核心指标卡片 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic title="新闻总量" value={stats.total} prefix="📚" />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="已分析" value={stats.analyzed} suffix={`/ ${stats.total}`} prefix="🤖" />
              <Progress percent={Math.round((stats.analyzed / (stats.total || 1)) * 100)} size="small" />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="情感偏向 (今日)" value={0.2} precision={2} valueStyle={{ color: '#cf1322' }} prefix="📈" />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="高影响因子" value={stats.high_score} prefix="💥" valueStyle={{ color: '#fa8c16' }} />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          {/* 采集趋势 */}
          <Col span={16}>
            <Card title="24小时舆情热度趋势">
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={stats.trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="hour" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="count" name="采集数量" stroke="#1890ff" activeDot={{ r: 8 }} />
                  <Line type="monotone" dataKey="analyzed_count" name="已分析量" stroke="#52c41a" strokeDasharray="5 5" />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </Col>

          {/* 今日热点实体 (词云替代方案) */}
          <Col span={8}>
            <Card title={<Space><FireOutlined style={{ color: '#ff4d4f' }} /> 今日核心实体</Space>}>
              <div style={{ height: 400, overflowY: 'auto', padding: '10px' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  {(stats.hot_entities || [
                    { name: '英伟达', score: 95 },
                    { name: '美联储', score: 88 },
                    { name: '比特币', score: 82 },
                    { name: '特斯拉', score: 75 },
                    { name: '降息', score: 70 },
                    { name: 'AI芯片', score: 65 },
                    { name: '财报', score: 60 },
                    { name: '黄金', score: 55 },
                    { name: 'SpaceX', score: 50 },
                    { name: 'OpenAI', score: 45 },
                  ]).map((entity, index) => (
                    <Tag 
                      key={index} 
                      color={COLORS[index % COLORS.length]} 
                      onClick={() => handleEntityClick(entity.name)}
                      style={{ 
                        fontSize: `${Math.max(12, entity.score / 3)}px`, 
                        padding: '4px 10px',
                        margin: '4px',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      {entity.name}
                    </Tag>
                  ))}
                </div>
              </div>
            </Card>
          </Col>
        </Row>


      </Spin>
      
      <Modal
        title={<Space><FireOutlined style={{ color: '#ff4d4f' }} /> 关于 "{selectedEntity}" 的相关新闻</Space>}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
        width={800}
        bodyStyle={{ maxHeight: '600px', overflowY: 'auto' }}
      >
        <List
          loading={newsLoading}
          itemLayout="vertical"
          dataSource={entityNews}
          locale={{ emptyText: <Empty description="暂无相关新闻" /> }}
          renderItem={item => (
            <List.Item
              key={item.id}
              extra={
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                  <Tag color={(item.sentiment_score || 0) > 0.1 ? 'green' : (item.sentiment_score || 0) < -0.1 ? 'red' : 'default'}>
                    {(item.sentiment_score || 0) > 0.1 ? '利好' : (item.sentiment_score || 0) < -0.1 ? '利空' : '中性'}
                  </Tag>
                  {(item.impact_score || 0) >= 4 && <Tag color="orange">高影响</Tag>}
                </div>
              }
            >
              <List.Item.Meta
                title={<a href={item.link} target="_blank" rel="noopener noreferrer" style={{ fontSize: '16px', fontWeight: 'bold' }}>{item.title}</a>}
                description={
                  <Space split="|">
                    <Text type="secondary">{item.time || new Date(item.created_at).toLocaleString()}</Text>
                    <Text type="secondary">{item.source}</Text>
                  </Space>
                }
              />
              <div style={{ marginTop: '8px' }}>
                {item.analysis?.summary || item.content?.substring(0, 150) + (item.content?.length > 150 ? '...' : '')}
              </div>
            </List.Item>
          )}
        />
      </Modal>
    </div>
  );
};

export default Trends;
