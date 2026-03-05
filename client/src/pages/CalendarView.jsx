import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, DatePicker, Button, Space, Typography, message, Tooltip } from 'antd';
import { ReloadOutlined, CalendarOutlined, StarFilled } from '@ant-design/icons';
import dayjs from 'dayjs';
import { getCalendarEvents, refreshCalendar } from '../services/api';

const { Title } = Typography;

const CalendarView = () => {
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [events, setEvents] = useState([]);
  const [selectedDate, setSelectedDate] = useState(dayjs());

  const fetchEvents = async (date) => {
    setLoading(true);
    try {
      const dateStr = date.format('YYYY-MM-DD');
      const res = await getCalendarEvents(dateStr);
      // Backend returns list directly
      if (Array.isArray(res.data)) {
        setEvents(res.data);
      } else {
        setEvents([]);
      }
    } catch (error) {
      console.error('Failed to fetch calendar events:', error);
      message.error('获取日历数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshCalendar();
      message.success('日历数据已更新');
      fetchEvents(selectedDate);
    } catch (error) {
      console.error('Failed to refresh calendar:', error);
      message.error('刷新失败');
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchEvents(selectedDate);
  }, [selectedDate]);

  const columns = [
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
      width: 100,
    },
    {
      title: '地区',
      dataIndex: 'country',
      key: 'country',
      width: 100,
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '事件',
      dataIndex: 'event',
      key: 'event',
      render: (text, record) => (
        <Space>
          <span style={{ fontWeight: 'bold' }}>{text}</span>
          {record.importance >= 4 && <Tag color="red">重要</Tag>}
        </Space>
      ),
    },
    {
      title: '重要性',
      dataIndex: 'importance',
      key: 'importance',
      width: 120,
      render: (score) => (
        <Space size={2}>
          {[...Array(score)].map((_, i) => (
            <StarFilled key={i} style={{ color: '#faad14' }} />
          ))}
        </Space>
      ),
    },
    {
      title: '前值',
      dataIndex: 'previous',
      key: 'previous',
      width: 100,
    },
    {
      title: '预期',
      dataIndex: 'consensus',
      key: 'consensus',
      width: 100,
    },
    {
      title: '公布',
      dataIndex: 'actual',
      key: 'actual',
      width: 100,
      render: (text) => (
        <span style={{ color: text ? '#52c41a' : '#bfbfbf', fontWeight: text ? 'bold' : 'normal' }}>
          {text || '-'}
        </span>
      ),
    },
  ];

  return (
    <div className="calendar-view">
      {/* 提示用户检查系统时间 */}
      {selectedDate.year() > 2025 && (
        <div style={{ marginBottom: 16, padding: '8px 16px', background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 4 }}>
          ⚠️ 检测到当前选择的日期为 <b>{selectedDate.format('YYYY-MM-DD')}</b>，如果这是未来的日期，可能暂时没有数据。请尝试选择历史日期（如 2024-03-05）。
        </div>
      )}

      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space align="center">
            <CalendarOutlined style={{ fontSize: 24 }} />
            <Title level={3} style={{ margin: 0 }}>财经日历</Title>
          </Space>
          <Space>
            <DatePicker 
              value={selectedDate} 
              onChange={(date) => date && setSelectedDate(date)} 
              allowClear={false}
            />
            <Button 
              icon={<ReloadOutlined spin={refreshing} />} 
              onClick={handleRefresh}
              loading={refreshing}
            >
              更新数据
            </Button>
          </Space>
        </div>

        <Card bordered={false} className="shadow-sm">
          <Table
            columns={columns}
            dataSource={events}
            rowKey={(record) => `${record.time}-${record.event}`}
            loading={loading}
            pagination={false}
            locale={{ emptyText: '暂无重要财经事件' }}
          />
        </Card>
      </Space>
    </div>
  );
};

export default CalendarView;
