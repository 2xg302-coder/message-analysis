import React, { useEffect, useState } from 'react';
import { List, Card, Tag, Typography, Spin, message } from 'antd';
import { getNews } from '../services/api';
import dayjs from 'dayjs';

const { Title } = Typography;

const NewsFeed = () => {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchNews = async () => {
    // 只有在第一次加载时显示loading，后续更新静默进行
    if (news.length === 0) setLoading(true);
    try {
      const response = await getNews();
      // 根据后端返回结构调整
      // server/index.js: ctx.body = { count: news.length, data: news };
      if (response.data && response.data.data) {
        setNews(response.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch news:', error);
      message.error('获取新闻失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNews();
    const interval = setInterval(fetchNews, 60000); // 60秒自动刷新
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <Title level={2}>实时新闻流</Title>
      <Spin spinning={loading}>
        <List
          grid={{ gutter: 16, column: 1 }}
          dataSource={news}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
          }}
          renderItem={(item) => (
            <List.Item>
              <Card 
                title={item.title || '无标题'} 
                extra={dayjs(item.created_at).format('YYYY-MM-DD HH:mm:ss')}
                hoverable
              >
                <p style={{ whiteSpace: 'pre-wrap' }}>{item.content}</p>
                <div style={{ marginTop: 10 }}>
                    {item.source && <Tag color="blue">{item.source}</Tag>}
                    {/* 这里后续可以展示智能分析的标签 */}
                </div>
              </Card>
            </List.Item>
          )}
        />
      </Spin>
    </div>
  );
};

export default NewsFeed;
