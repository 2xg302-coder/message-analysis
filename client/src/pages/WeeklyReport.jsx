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
  message,
  Button,
  Select,
  Space
} from 'antd';
import { ReloadOutlined, HistoryOutlined } from '@ant-design/icons';
import { 
  PieChart, 
  Pie, 
  Cell, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid
} from 'recharts';
import dayjs from 'dayjs';
import weekday from 'dayjs/plugin/weekday';
import localeData from 'dayjs/plugin/localeData';
import 'dayjs/locale/zh-cn';
import { getWeeklyReport, getWeeklyReportHistory } from '../services/api';

dayjs.extend(weekday);
dayjs.extend(localeData);
dayjs.locale('zh-cn');

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

const WeeklyReport = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  // Default to the Monday of the current week
  const [date, setDate] = useState(dayjs().weekday(0));
  const [historyWeeks, setHistoryWeeks] = useState([]);

  const fetchData = async (selectedDate, refresh = false) => {
    setLoading(true);
    try {
      // Ensure we send the Monday of the week
      const monday = selectedDate.weekday(0).format('YYYY-MM-DD');
      const response = await getWeeklyReport(monday, refresh);
      if (response.data && response.data.success) {
        setData(response.data.data);
      } else {
        message.error('获取周报数据失败: ' + (response.data?.message || '未知错误'));
      }
    } catch (error) {
      console.error('Failed to fetch weekly report:', error);
      message.error('获取周报数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await getWeeklyReportHistory();
      if (response.data && response.data.success) {
        setHistoryWeeks(response.data.weeks);
      }
    } catch (error) {
      console.error('Failed to fetch report history:', error);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  useEffect(() => {
    fetchData(date);
  }, [date]);

  const handleDateChange = (newDate) => {
    if (newDate) {
      setDate(newDate.weekday(0));
    }
  };

  const handleHistorySelect = (value) => {
    setDate(dayjs(value));
  };

  const handleRefresh = () => {
    fetchData(date, true);
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

    const { collection_stats, daily_trends, hotspots, series_updates, high_value_info } = data;

    // Prepare chart data
    const sourceData = collection_stats?.sources 
      ? Object.entries(collection_stats.sources).map(([name, value]) => ({ name, value }))
      : [];
    
    const sentimentData = collection_stats?.sentiment 
      ? Object.entries(collection_stats.sentiment).map(([name, value]) => ({ name, value }))
      : [];

    return (
      <div style={{ padding: '24px' }}>
        <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>周报</Title>
            <Text type="secondary">{data.week_start} 至 {data.week_end}</Text>
          </div>
          <Space>
            <Select 
              placeholder="历史周报" 
              style={{ width: 200 }} 
              onChange={handleHistorySelect}
              value={historyWeeks.some(w => w.start === date.format('YYYY-MM-DD')) ? date.format('YYYY-MM-DD') : undefined}
            >
              {historyWeeks.map(w => (
                <Option key={w.start} value={w.start}>{w.start} 至 {w.end}</Option>
              ))}
            </Select>
            <DatePicker 
              picker="week"
              value={date} 
              onChange={handleDateChange} 
              allowClear={false}
              style={{ width: 140 }}
            />
            <Button 
              icon={<ReloadOutlined />} 
              onClick={handleRefresh} 
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        </div>

        {/* High Value Info Section */}
        {high_value_info && (
          <Card 
            title={<Space><Tag color="purple">深度总结</Tag>本周高价值信息综述</Space>} 
            style={{ marginBottom: '24px', background: '#f9f0ff', borderColor: '#d3adf7' }}
            headStyle={{ background: '#efdbff' }}
          >
            <Paragraph style={{ fontSize: '16px', whiteSpace: 'pre-line', margin: 0 }}>
              {typeof high_value_info === 'string' ? high_value_info : JSON.stringify(high_value_info)}
            </Paragraph>
          </Card>
        )}

        {/* Row 1: Statistics */}
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
          <Col xs={24} sm={8}>
            <Card hoverable>
              <Statistic 
                title="本周采集总量" 
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
                title="分析率" 
                value={collection_stats?.total_news ? Math.round((collection_stats.analyzed_count / collection_stats.total_news) * 100) : 0} 
                suffix="%"
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
        </Row>

        {/* Row 2: Charts */}
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
           <Col xs={24} lg={12}>
            <Card title="每日采集趋势" hoverable>
              <div style={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={daily_trends || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tickFormatter={(val) => dayjs(val).format('MM-DD')} />
                    <YAxis />
                    <Tooltip labelFormatter={(val) => dayjs(val).format('YYYY-MM-DD')} />
                    <Bar dataKey="count" fill="#1890ff" name="采集量" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </Col>
          <Col xs={24} lg={6}>
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
          <Col xs={24} lg={6}>
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
            <Card title="本周热点新闻 TOP 10" hoverable>
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
                      description={
                        <div>
                          <Text type="secondary" style={{ fontSize: '12px' }}>{dayjs(item.created_at).format('YYYY-MM-DD HH:mm')}</Text>
                          <br/>
                          {item.summary}
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Col>
          <Col xs={24} md={10}>
            <Card title="本周热门标签" hoverable>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {hotspots?.hot_tags?.map((tag) => (
                  <Tag 
                    key={tag.name} 
                    color="geekblue" 
                    style={{ fontSize: Math.min(12 + tag.count / 20, 24) + 'px', padding: '4px 8px' }}
                  >
                    {tag.name} ({tag.count})
                  </Tag>
                ))}
              </div>
            </Card>
          </Col>
        </Row>

        {/* Row 4: Series Updates */}
        <Card title="本周重要事件进展" hoverable>
          <Timeline 
            mode="left"
            items={series_updates?.map((update, index) => ({
              color: update.importance > 7 ? 'red' : 'blue',
              label: update.date,
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

export default WeeklyReport;
