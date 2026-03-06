import React, { useEffect, useState } from 'react';
import { Row, Col, List, Card, Timeline, Typography, Tag, Spin, Badge } from 'antd';
import { getSeriesList, getSeriesNews } from '../services/api';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';

const { Title, Text, Paragraph } = Typography;

const SeriesView = () => {
  const [seriesList, setSeriesList] = useState([]);
  const [currentSeries, setCurrentSeries] = useState(null);
  const [newsList, setNewsList] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingNews, setLoadingNews] = useState(false);
  
  const { tag } = useParams();
  const navigate = useNavigate();

  // 获取事件列表
  useEffect(() => {
    const fetchList = async () => {
      try {
        const res = await getSeriesList();
        if (res.data && res.data.data) {
          setSeriesList(res.data.data);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoadingList(false);
      }
    };
    fetchList();
  }, []);

  // 监听 tag 变化或列表加载完成，设置当前选中的 series
  useEffect(() => {
    if (tag) {
      setCurrentSeries(decodeURIComponent(tag));
    } else if (!tag && seriesList.length > 0 && !currentSeries) {
      // 如果 URL 没有 tag 且列表加载完毕，默认选中第一个
      const firstTag = seriesList[0].tag;
      setCurrentSeries(firstTag);
      // 同时更新 URL，保持一致性（可选，但推荐）
      // navigate(`/series/${encodeURIComponent(firstTag)}`, { replace: true });
    }
  }, [tag, seriesList]);

  // 获取具体事件的新闻
  useEffect(() => {
    if (!currentSeries) return;
    
    const fetchNews = async () => {
      setLoadingNews(true);
      try {
        const res = await getSeriesNews(currentSeries);
        if (res.data && res.data.data) {
          setNewsList(res.data.data);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoadingNews(false);
      }
    };
    fetchNews();
  }, [currentSeries]);

  const handleSelectSeries = (tag) => {
    navigate(`/series/${encodeURIComponent(tag)}`);
  };

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>🎬 事件连续剧追踪</Title>
      <Row gutter={24}>
        {/* 左侧：事件列表 */}
        <Col span={8}>
          <Card title="热门事件" style={{ height: 'calc(100vh - 100px)', overflowY: 'auto' }}>
            <Spin spinning={loadingList}>
              <List
                dataSource={seriesList}
                renderItem={item => (
                  <List.Item 
                    onClick={() => handleSelectSeries(item.tag)}
                    style={{ 
                      cursor: 'pointer', 
                      backgroundColor: currentSeries === item.tag ? '#e6f7ff' : 'transparent',
                      padding: '12px',
                      borderRadius: '4px',
                      transition: 'background 0.3s'
                    }}
                  >
                    <List.Item.Meta
                      title={<Text strong>{item.tag}</Text>}
                      description={
                        <div>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            最近更新: {dayjs(item.latest_date).format('MM-DD HH:mm')}
                          </Text>
                          <div style={{ marginTop: 4 }}>
                            <Badge count={item.count} style={{ backgroundColor: '#52c41a' }} overflowCount={999} /> 篇相关报道
                          </div>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
              {!loadingList && seriesList.length === 0 && (
                <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                  暂无聚合事件，请等待 AI 分析积累数据
                </div>
              )}
            </Spin>
          </Card>
        </Col>
        
        {/* 右侧：时间轴 */}
        <Col span={16}>
          <Card title={currentSeries ? `📅 ${currentSeries} - 发展脉络` : '事件详情'} style={{ height: 'calc(100vh - 100px)', overflowY: 'auto' }}>
            <Spin spinning={loadingNews}>
              {newsList.length > 0 ? (
                <Timeline mode="left" style={{ marginTop: 20 }}>
                  {newsList.map(item => {
                    const analysis = item.analysis || {};
                    return (
                      <Timeline.Item key={item.id} label={dayjs(item.created_at).format('MM-DD HH:mm')}>
                        <Card size="small" style={{ marginBottom: 16, borderLeft: '4px solid #1890ff' }}>
                          <Text strong style={{ fontSize: 16 }}>{item.title}</Text>
                          {analysis.summary && (
                            <Paragraph style={{ marginTop: 8, background: '#f5f5f5', padding: 8, borderRadius: 4, color: '#666' }}>
                              {analysis.summary}
                            </Paragraph>
                          )}
                          <div style={{ marginTop: 8 }}>
                             {analysis.score && (
                               <Tag color={analysis.score >= 7 ? 'red' : 'blue'}>评分: {analysis.score}</Tag>
                             )}
                             {/* Handle entities whether it's an array or object */}
                             {analysis.entities && (Array.isArray(analysis.entities) 
                               ? analysis.entities.map((e, idx) => <Tag key={idx}>{e.name || e}</Tag>)
                               : typeof analysis.entities === 'object' 
                                 ? Object.values(analysis.entities).map((name, idx) => <Tag key={idx}>{name}</Tag>)
                                 : null
                             )}
                          </div>
                        </Card>
                      </Timeline.Item>
                    );
                  })}
                </Timeline>
              ) : (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Text type="secondary">暂无数据或请选择左侧事件</Text>
                </div>
              )}
            </Spin>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default SeriesView;
