import React, { useCallback, useEffect, useState } from 'react';
import { Card, Typography, Spin, message, Pagination, Skeleton, Form, Select, Input, DatePicker, Space, Button } from 'antd';
import dayjs from 'dayjs';
import { getNews } from '../services/api';
import NewsCard from '../components/NewsCard';

const { Title } = Typography;
const { RangePicker } = DatePicker;

const DEFAULT_FILTERS = {
  type: 'all',
  sentiment: 'all',
  keyword: '',
  dateRange: null
};

const ITHomeView = () => {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [initialLoading, setInitialLoading] = useState(true);
  const [form] = Form.useForm();
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  const { current, pageSize } = pagination;

  const fetchData = useCallback(async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      
      const offset = (current - 1) * pageSize;

      const startDate = filters.dateRange?.[0] ? dayjs(filters.dateRange[0]).format('YYYY-MM-DD') : undefined;
      const endDate = filters.dateRange?.[1] ? dayjs(filters.dateRange[1]).format('YYYY-MM-DD') : undefined;
      
      const queryParams = {
        source: 'ITHome',
        limit: pageSize,
        offset,
        type: filters.type,
        sentiment: filters.sentiment,
        keyword: filters.keyword,
        startDate,
        endDate
      };

      const newsRes = await getNews(queryParams);

      if (newsRes.data) {
        // Handle different backend response structures
        const list = Array.isArray(newsRes.data) ? newsRes.data : (newsRes.data.data || []);
        // Some APIs return total count in different fields
        const total = newsRes.data.total || newsRes.data.count || 0;
        
        setNews(list);
        setPagination(prev => ({ ...prev, total: total }));
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
      message.error('获取IT之家数据失败');
    } finally {
      setLoading(false);
      setInitialLoading(false);
    }
  }, [filters, current, pageSize]);

  useEffect(() => {
    fetchData();
    // 仅在第一页自动刷新，避免打断用户翻页
    const interval = setInterval(() => {
      if (current !== 1) return;
        fetchData();
    }, 5 * 60 * 1000); 
    return () => clearInterval(interval);
  }, [fetchData, current]); 

  const handleFilterSubmit = (values) => {
    const nextFilters = {
      type: values.type || 'all',
      sentiment: values.sentiment || 'all',
      keyword: (values.keyword || '').trim(),
      dateRange: values.dateRange || null
    };

    setFilters(nextFilters);
    setPagination(prev => ({ ...prev, current: 1 }));
  };

  const handleFilterReset = () => {
    form.resetFields();
    setFilters({ ...DEFAULT_FILTERS });
    setPagination(prev => ({ ...prev, current: 1 }));
  };

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>IT之家 RSS 订阅</Title>
      </div>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Form
          form={form}
          layout="inline"
          initialValues={DEFAULT_FILTERS}
          onFinish={handleFilterSubmit}
          style={{ rowGap: 12 }}
        >
          <Form.Item name="type" label="内容类型">
            <Select
              style={{ width: 140 }}
              options={[
                { value: 'all', label: '全部' },
                { value: 'flash', label: '快讯' },
                { value: 'article', label: '文章' }
              ]}
            />
          </Form.Item>
          <Form.Item name="sentiment" label="情感倾向">
            <Select
              style={{ width: 140 }}
              options={[
                { value: 'all', label: '全部' },
                { value: 'positive', label: '利好' },
                { value: 'neutral', label: '中性' },
                { value: 'negative', label: '利空' }
              ]}
            />
          </Form.Item>
          <Form.Item name="keyword" label="关键词">
            <Input
              allowClear
              placeholder="标题/正文/实体"
              style={{ width: 220 }}
            />
          </Form.Item>
          <Form.Item name="dateRange" label="发布时间">
            <RangePicker />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">筛选</Button>
              <Button onClick={handleFilterReset}>重置</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

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
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {news.map((item, index) => (
              <NewsCard key={item.id || index} item={item} />
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
    </div>
  );
};

export default ITHomeView;
