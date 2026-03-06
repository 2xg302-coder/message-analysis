import React, { useState, useEffect, useMemo } from 'react';
import { Card, Table, Tag, DatePicker, Button, Space, Typography, message, Select, Radio, Tooltip } from 'antd';
import { ReloadOutlined, CalendarOutlined, StarFilled, LeftOutlined, RightOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { getCalendarEvents, refreshCalendar } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const CalendarView = () => {
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [events, setEvents] = useState([]);
  const [filteredEvents, setFilteredEvents] = useState([]);
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [importanceFilter, setImportanceFilter] = useState('all'); // 'all', '2', '3'
  const [countryFilter, setCountryFilter] = useState('all');

  // 提取所有国家供筛选
  const countries = useMemo(() => {
    const uniqueCountries = [...new Set(events.map(e => e.country))].filter(Boolean).sort();
    return ['all', ...uniqueCountries];
  }, [events]);

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

  // Filter events when events or filter changes
  useEffect(() => {
    let res = events;
    
    // Filter by importance
    if (importanceFilter !== 'all') {
      const minStars = parseInt(importanceFilter);
      res = res.filter(e => e.importance >= minStars);
    }

    // Filter by country
    if (countryFilter !== 'all') {
      res = res.filter(e => e.country === countryFilter);
    }

    setFilteredEvents(res);
  }, [events, importanceFilter, countryFilter]);

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

  const handleDateChange = (offset) => {
    setSelectedDate(prev => prev.add(offset, 'day'));
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
      width: 100,
      align: 'center',
    },
    {
      title: '地区',
      dataIndex: 'country',
      key: 'country',
      width: 120,
      render: (text) => <Tag color="blue">{text}</Tag>,
      filters: countries.filter(c => c !== 'all').map(c => ({ text: c, value: c })),
      onFilter: (value, record) => record.country === value,
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
      width: 140,
      sorter: (a, b) => a.importance - b.importance,
      render: (score) => (
        <Space size={2}>
          {[...Array(5)].map((_, i) => (
            <StarFilled key={i} style={{ color: i < score ? '#faad14' : '#f0f0f0' }} />
          ))}
        </Space>
      ),
    },
    {
      title: '前值',
      dataIndex: 'previous',
      key: 'previous',
      width: 100,
      align: 'right',
    },
    {
      title: '预期',
      dataIndex: 'consensus',
      key: 'consensus',
      width: 100,
      align: 'right',
    },
    {
      title: '公布',
      dataIndex: 'actual',
      key: 'actual',
      width: 100,
      align: 'right',
      render: (text, record) => {
        // 简单的着色逻辑：如果比预期好（这里很难判断因为不知道是利好还是利空，暂时只根据是否有值着色）
        // 实际业务中通常需要 backend 给出一个 impact 方向
        return (
          <span style={{ color: text ? '#1890ff' : '#bfbfbf', fontWeight: text ? 'bold' : 'normal' }}>
            {text || '-'}
          </span>
        );
      },
    },
  ];

  return (
    <div className="calendar-view">
      {/* 提示用户检查系统时间 */}
      {selectedDate.year() > dayjs().year() + 1 && (
        <div style={{ marginBottom: 16, padding: '8px 16px', background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 4 }}>
          ⚠️ 检测到当前选择的日期为 <b>{selectedDate.format('YYYY-MM-DD')}</b>，如果这是未来的日期，可能暂时没有数据。
        </div>
      )}

      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <Space align="center">
            <CalendarOutlined style={{ fontSize: 24, color: '#1890ff' }} />
            <Title level={3} style={{ margin: 0 }}>财经日历</Title>
          </Space>
          
          <Space wrap>
            <Radio.Group value={importanceFilter} onChange={(e) => setImportanceFilter(e.target.value)} buttonStyle="solid">
              <Radio.Button value="all">全部</Radio.Button>
              <Radio.Button value="2">
                <StarFilled style={{ color: '#faad14', marginRight: 4 }} />
                2星+
              </Radio.Button>
              <Radio.Button value="3">
                <StarFilled style={{ color: '#faad14', marginRight: 4 }} />
                3星+
              </Radio.Button>
            </Radio.Group>

            <Select 
              value={countryFilter} 
              onChange={setCountryFilter} 
              style={{ width: 120 }} 
              placeholder="选择地区"
            >
              <Option value="all">所有地区</Option>
              {countries.filter(c => c !== 'all').map(c => (
                <Option key={c} value={c}>{c}</Option>
              ))}
            </Select>

            <Space.Compact>
              <Button icon={<LeftOutlined />} onClick={() => handleDateChange(-1)} />
              <DatePicker 
                value={selectedDate} 
                onChange={(date) => date && setSelectedDate(date)} 
                allowClear={false}
                style={{ width: 140 }}
              />
              <Button icon={<RightOutlined />} onClick={() => handleDateChange(1)} />
              <Button onClick={() => setSelectedDate(dayjs())}>今天</Button>
            </Space.Compact>
            
            <Tooltip title="从数据源强制刷新最新数据">
              <Button 
                icon={<ReloadOutlined spin={refreshing} />} 
                onClick={handleRefresh}
                loading={refreshing}
              >
                刷新
              </Button>
            </Tooltip>
          </Space>
        </div>

        <Card bordered={false} className="shadow-sm" bodyStyle={{ padding: 0 }}>
          <Table
            columns={columns}
            dataSource={filteredEvents}
            rowKey={(record, index) => `${record.time}-${record.country}-${record.event}-${index}`}
            loading={loading}
            pagination={false}
            locale={{ emptyText: '暂无符合条件的财经事件' }}
            scroll={{ x: 800 }}
            size="middle"
          />
        </Card>
      </Space>
    </div>
  );
};

export default CalendarView;
