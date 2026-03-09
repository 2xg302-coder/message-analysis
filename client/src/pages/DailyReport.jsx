import React, { useState, useEffect } from 'react';
import { 
  Layout, 
  Card, 
  Statistic, 
  List, 
  Tag, 
  Timeline, 
  DatePicker, 
  Row, 
  Col, 
  Typography, 
  Spin, 
  Empty, 
  message 
} from 'antd';
import { 
  PieChart, 
  Pie, 
  Cell, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts';
import dayjs from 'dayjs';
import { getDailyReport } from '../services/api';

const { Title, Text } = Typography;

const DailyReport = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [date, setDate] = useState(dayjs().subtract(1, 'day'));

  const fetchData = async (selectedDate) => {
    setLoading(true);
    try {
      const dateStr = selectedDate.format('YYYY-MM-DD');
      const response = await getDailyReport(dateStr);
      setData(response.data);
    } catch (error) {
      console.error('Failed to fetch daily report:', error);
      message.error('获取日报数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(date);
  }, [date]);

  const handleDateChange = (newDate) => {
    if (newDate) {
      setDate(newDate);
    }
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];
  const SENTIMENT_COLORS = {
    positive: '#52c41a',
    neutral: '#faad14',
    negative: '#ff4d4f'
  };

  if (!data && loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  const renderContent = () => {
    if (!data) return <Empty description="暂无数据" />;

    const { collection_stats, hotspots, series_updates } = data;

    // Prepare chart data
    const sourceData = collection_stats?.sources 
      ? Object.entries(collection_stats.sources).map(([name, value]) => ({ name, value }))
      : [];
    
    const sentimentData = collection_stats?.sentiment 
      ? Object.entries(collection_stats.sentiment).map(([name, value]) => ({ name, value }))
      : [];

    return (
      <div style={{ padding: '24px' }}>
        <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Title level={2} style={{ margin: 0 }}>每日报告</Title>
          <DatePicker 
            value={date} 
            onChange={handleDateChange} 
            allowClear={false}
            style={{ width: 200 }}
          />
        </div>

        {/* Row 1: Statistics */}
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
          <Col xs={24} sm={8}>
            <Card hoverable>
              <Statistic 
                title="采集总量" 
                value={collection_stats?.total_news || 0} 
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card hoverable>
              <Statistic 
                title="已分析" 
                value={collection_stats?.analyzed_count || 0} 
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card hoverable>
              <Statistic 
                title="待处理" 
                value={collection_stats?.pending_count || 0} 
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>

        {/* Row 2: Charts */}
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
          <Col xs={24} md={12}>
            <Card title="来源分布" hoverable>
              <div style={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={sourceData}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {sourceData.map((entry, index) => (
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
          <Col xs={24} md={12}>
            <Card title="情感分布" hoverable>
              <div style={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={sentimentData}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {sentimentData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={SENTIMENT_COLORS[entry.name] || COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </Col>
        </Row>

        {/* Row 3: Hotspots */}
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
          <Col xs={24} md={14}>
            <Card title="今日热点新闻" hoverable>
              <List
                itemLayout="horizontal"
                dataSource={hotspots?.top_news || []}
                renderItem={(item, index) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={<Tag color={index < 3 ? 'red' : 'blue'}>{index + 1}</Tag>}
                      title={
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Text strong>{item.title}</Text>
                          <Tag color="gold">Impact: {item.impact_score}</Tag>
                        </div>
                      }
                      description={item.summary}
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Col>
          <Col xs={24} md={10}>
            <Card title="热门标签" hoverable>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {hotspots?.hot_tags?.map((tag) => (
                  <Tag 
                    key={tag.name} 
                    color="geekblue" 
                    style={{ fontSize: Math.min(12 + tag.count / 10, 24) + 'px', padding: '4px 8px' }}
                  >
                    {tag.name} ({tag.count})
                  </Tag>
                ))}
              </div>
            </Card>
          </Col>
        </Row>

        {/* Row 4: Series Updates */}
        <Card title="事件追踪更新" hoverable>
          <Timeline 
            mode="left"
            items={series_updates?.map((update, index) => ({
              color: update.importance > 7 ? 'red' : 'blue',
              children: (
                <>
                  <Text strong>{update.series_title}</Text>
                  <br />
                  <Text>{update.storyline_title}</Text>
                  <br />
                  <Tag color={update.importance > 7 ? 'red' : 'default'}>
                    重要性: {update.importance}
                  </Tag>
                </>
              )
            }))}
          />
        </Card>
      </div>
    );
  };

  return (
    <Layout style={{ minHeight: '100%', background: 'transparent' }}>
      {renderContent()}
    </Layout>
  );
};

export default DailyReport;
