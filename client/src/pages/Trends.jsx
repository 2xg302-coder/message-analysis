import React, { useEffect, useState } from 'react';
import { Typography, Card, Row, Col, Statistic, Spin, Progress, Switch, Alert, Steps } from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { getStats, getAnalysisStatus, setAnalysisControl } from '../services/api';
import { RobotOutlined, PauseCircleOutlined, PlayCircleOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

const Trends = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    analyzed: 0,
    positive: 0,
    negative: 0,
    trends: []
  });
  
  // 分析任务状态
  const [analysisStatus, setAnalysisStatus] = useState({
    isRunning: true,
    currentTask: null
  });

  const fetchStats = async () => {
    try {
      const res = await getStats();
      if (res.data && res.data.success) {
        setStats(res.data.data);
      }
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
    
    // 状态刷新频率更高，以便看到实时进度
    const statusInterval = setInterval(fetchAnalysisStatus, 2000);
    // 统计数据刷新频率稍低
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

  const sentimentData = [
    { name: '利好', value: stats.positive },
    { name: '利空', value: stats.negative },
    { name: '中性/其他', value: stats.analyzed - stats.positive - stats.negative }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>AI 分析控制台</Title>
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
      
      {/* 实时任务监控卡片 */}
      <Card 
        style={{ marginBottom: 24, borderLeft: `4px solid ${analysisStatus.isRunning ? '#52c41a' : '#d9d9d9'}` }}
        title={
            <span>
                <RobotOutlined style={{ marginRight: 8 }} />
                {analysisStatus.isRunning ? (analysisStatus.currentTask ? '正在分析...' : '正在待机 (等待新数据)') : '分析任务已暂停'}
            </span>
        }
      >
        {analysisStatus.currentTask ? (
            <div>
                <div style={{ marginBottom: 12 }}>
                    <Text type="secondary">新闻ID: {analysisStatus.currentTask.id}</Text>
                </div>
                <div style={{ fontSize: 16, fontWeight: 'bold', marginBottom: 16 }}>
                    {analysisStatus.currentTask.title}
                </div>
                <Steps
                    size="small"
                    current={1}
                    items={[
                        { title: '获取数据' },
                        { title: 'DeepSeek 思考中...', icon: <Spin /> },
                        { title: '提取结构化知识' },
                    ]}
                />
            </div>
        ) : (
            <div style={{ color: '#999', fontStyle: 'italic' }}>
                {analysisStatus.isRunning ? '暂无新任务，Worker 正在轮询...' : '点击上方开关恢复分析任务'}
            </div>
        )}
      </Card>
      
      <Spin spinning={loading}>
        {/* 顶部核心指标 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic title="新闻总入库" value={stats.total} prefix="📚" />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="已分析" 
                value={stats.analyzed} 
                suffix={`/ ${stats.total}`} 
                prefix="🤖"
              />
              <Progress percent={Math.round((stats.analyzed / (stats.total || 1)) * 100)} size="small" />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="利好消息" value={stats.positive} valueStyle={{ color: '#3f8600' }} prefix="📈" />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="利空消息" value={stats.negative} valueStyle={{ color: '#cf1322' }} prefix="📉" />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          {/* 情感分布饼图 */}
          <Col span={12}>
            <Card title="情感倾向分布">
              <div style={{ height: 300, display: 'flex', justifyContent: 'center' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={sentimentData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      fill="#8884d8"
                      paddingAngle={5}
                      dataKey="value"
                      label
                    >
                      {sentimentData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </Col>

          {/* 采集趋势柱状图 */}
          <Col span={12}>
            <Card title="近12小时采集量趋势">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={stats.trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="hour" label={{ value: '小时', position: 'insideBottomRight', offset: 0 }} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" name="新闻数量" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
};

export default Trends;
