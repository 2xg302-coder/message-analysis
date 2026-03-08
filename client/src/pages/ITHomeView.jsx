import React, { useEffect, useState } from 'react';
import { Card, Typography, Spin, message, Pagination, Skeleton } from 'antd';
import { getNews } from '../services/api';
import NewsCard from '../components/NewsCard';

const { Title } = Typography;

const ITHomeView = () => {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [initialLoading, setInitialLoading] = useState(true);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });

  const fetchData = async () => {
    try {
      setLoading(true);
      
      const { current, pageSize } = pagination;
      const offset = (current - 1) * pageSize;
      
      const queryParams = {
        source: 'ITHome',
        limit: pageSize,
        offset: offset
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
  };

  useEffect(() => {
    fetchData();
    // Auto refresh every 5 minutes
    const interval = setInterval(() => {
        fetchData();
    }, 5 * 60 * 1000); 
    return () => clearInterval(interval);
  }, [pagination.current, pagination.pageSize]); 

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>IT之家 RSS 订阅</Title>
      </div>

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
