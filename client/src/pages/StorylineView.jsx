import React, { useState, useEffect } from 'react';
import { Card, List, Tag, Typography, Button, Space, Tabs, Rate, message, DatePicker, Empty, Popconfirm } from 'antd';
import { RocketOutlined, HistoryOutlined, ThunderboltOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { getActiveStorylines, getStorylinesByDate, getHistoryStorylines, generateStorylines, archiveStoryline } from '../services/api';

const { Title, Paragraph, Text } = Typography;

const StorylineCard = ({ item, onArchive }) => {
  return (
    <Card 
      title={
        <Space>
          <Text strong style={{ fontSize: 16 }}>{item.title}</Text>
          <Tag color="blue">{item.date}</Tag>
        </Space>
      }
      extra={
        <Space>
            <Rate disabled defaultValue={item.importance} count={5} style={{ fontSize: 14 }} />
            {item.status === 'active' && onArchive && (
                <Popconfirm title="确定归档这条主线吗？" onConfirm={() => onArchive(item.id)}>
                    <Button type="text" icon={<DeleteOutlined />} size="small">归档</Button>
                </Popconfirm>
            )}
        </Space>
      }
      style={{ marginBottom: 16 }}
      type="inner"
    >
      <Paragraph>{item.description}</Paragraph>
      <div style={{ marginBottom: 8 }}>
        <Text type="secondary">关键词: </Text>
        {item.keywords && item.keywords.map((kw, idx) => (
          <Tag key={idx}>{kw}</Tag>
        ))}
      </div>
      {item.expected_impact && (
        <div style={{ marginTop: 8, padding: '8px', background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 4 }}>
           <Text type="success" strong><ThunderboltOutlined /> 预期影响: </Text>
           <Text>{item.expected_impact}</Text>
        </div>
      )}
    </Card>
  );
};

const StorylineView = () => {
  const [activeStorylines, setActiveStorylines] = useState([]);
  const [historyStorylines, setHistoryStorylines] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [selectedDate, setSelectedDate] = useState(dayjs());

  const fetchStorylines = async (date) => {
    if (!date) return;
    setLoading(true);
    const dateStr = date.format('YYYY-MM-DD');
    try {
      // Use getStorylinesByDate instead of getActiveStorylines
      // If date is today, we could use active, but consistent API is better
      const res = await getStorylinesByDate(dateStr);
      setActiveStorylines(res.data || []);
    } catch (error) {
      message.error('获取主线失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await getHistoryStorylines();
      setHistoryStorylines(res.data || []);
    } catch (error) {
      message.error('获取历史主线失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStorylines(selectedDate);
    // fetchHistory only when tab changes, but we can load it initially too
  }, [selectedDate]);

  const handleGenerate = async () => {
    if (!selectedDate) return;
    setGenerating(true);
    const dateStr = selectedDate.format('YYYY-MM-DD');
    try {
      await generateStorylines(dateStr);
      message.success(`成功生成 ${dateStr} 的主线`);
      fetchStorylines(selectedDate);
    } catch (error) {
      console.error(error);
      message.error('生成失败，请检查后端日志');
    } finally {
      setGenerating(false);
    }
  };

  const handleArchive = async (id) => {
      try {
          await archiveStoryline(id);
          message.success('归档成功');
          fetchStorylines(selectedDate);
          // fetchHistory(); // Can't easily refresh history tab content from here without state lift, but that's fine
      } catch (error) {
          message.error('归档失败');
      }
  };

  const items = [
    {
      key: 'active',
      label: (
        <span>
          <RocketOutlined />
          每日主线
        </span>
      ),
      children: (
        <div>
          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Text>选择日期:</Text>
              <DatePicker value={selectedDate} onChange={setSelectedDate} allowClear={false} />
              <Button 
                type="primary" 
                icon={<ThunderboltOutlined />} 
                loading={generating}
                onClick={handleGenerate}
              >
                生成/重新生成
              </Button>
            </Space>
          </Card>
          
          {loading ? (
             <Card loading={true} />
          ) : activeStorylines.length > 0 ? (
            activeStorylines.map(item => (
              <StorylineCard key={item.id} item={item} onArchive={handleArchive} />
            ))
          ) : (
            <Empty description="该日期暂无主线数据，请尝试生成" />
          )}
        </div>
      ),
    },
    {
      key: 'history',
      label: (
        <span>
          <HistoryOutlined />
          历史归档
        </span>
      ),
      children: (
        <div>
          {loading && !historyStorylines.length ? (
             <Card loading={true} />
          ) : historyStorylines.length > 0 ? (
            historyStorylines.map(item => (
              <StorylineCard key={item.id} item={item} />
            ))
          ) : (
            <Empty description="暂无历史记录" />
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>市场主线 (Storylines)</Title>
      <Paragraph>
        基于每日财经日历与 AI 分析生成的市场核心交易逻辑。
      </Paragraph>
      <Tabs defaultActiveKey="active" items={items} onChange={(key) => {
          if (key === 'history') fetchHistory();
          else fetchActive();
      }} />
    </div>
  );
};

export default StorylineView;
