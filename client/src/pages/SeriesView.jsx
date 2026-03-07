import React, { useEffect, useState, useMemo } from 'react';
import { Row, Col, Card, Timeline, Typography, Tag, Spin, Badge, Empty, message, Divider } from 'antd';
import { getSeriesList, getSeriesNews, getRelatedSeries } from '../services/api';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

// Helper to normalize entities
const getEntities = (entities) => {
  if (!entities) return [];
  if (Array.isArray(entities)) return entities.map(e => (typeof e === 'string' ? e : e.name));
  if (typeof entities === 'object') return Object.values(entities);
  return [];
};

const NewsCard = ({ item }) => {
  const analysis = item.analysis || {};
  const entities = useMemo(() => getEntities(analysis.entities), [analysis.entities]);
  
  return (
    <div style={{ 
      marginBottom: 12, 
      borderLeft: '3px solid #1890ff', 
      padding: '8px 12px',
      background: '#fff',
      boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
      borderRadius: '0 4px 4px 0'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Text strong style={{ fontSize: 15, marginBottom: 4, display: 'block' }}>{item.title}</Text>
        {analysis.score && (
           <Tag color={analysis.score >= 7 ? 'red' : 'blue'} style={{ marginRight: 0, transform: 'scale(0.9)' }}>{analysis.score}</Tag>
         )}
      </div>
      
      {analysis.summary && (
        <div style={{ marginTop: 4, background: '#f9f9f9', padding: '6px 8px', borderRadius: 4, color: '#555', fontSize: 13, lineHeight: '1.5' }}>
          {analysis.summary}
        </div>
      )}
      
      {entities.length > 0 && (
        <div style={{ marginTop: 6 }}>
         {entities.map((name, idx) => (
           <Tag key={idx} style={{ fontSize: 12, lineHeight: '20px' }}>{name}</Tag>
         ))}
        </div>
      )}
    </div>
  );
};

const RelatedSeries = ({ currentTag, onSelect }) => {
  const [related, setRelated] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!currentTag) return;
    
    const fetchRelated = async () => {
      setLoading(true);
      try {
        const res = await getRelatedSeries(currentTag);
        if (res.data && res.data.data) {
          setRelated(res.data.data);
        } else {
          setRelated([]);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchRelated();
  }, [currentTag]);

  if (loading) return <Spin size="small" style={{ margin: '10px 0' }} />;
  if (related.length === 0) return null;

  return (
    <div style={{ marginTop: 20, padding: '12px', background: '#f9f9f9', borderRadius: 8 }}>
      <Text strong style={{ marginBottom: 12, display: 'block' }}>🔗 相关联事件</Text>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {related.map(item => (
          <div 
            key={item.tag}
            onClick={() => onSelect(item.tag)}
            style={{ 
              cursor: 'pointer',
              padding: '8px 0',
              borderBottom: '1px dashed #eee'
            }}
          >
            <div style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text style={{ color: '#1890ff' }}>{item.tag}</Text>
                <Tag color="orange" style={{ transform: 'scale(0.8)', marginRight: 0 }}>
                  相关度: {(item.score * 100).toFixed(0)}%
                </Tag>
              </div>
              <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                共有关联: {item.shared_entities.join(', ')}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

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
        message.error('获取热门事件列表失败');
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
      const firstTag = seriesList[0].tag;
      setCurrentSeries(firstTag);
    }
  }, [tag, seriesList, currentSeries]);

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
        message.error('获取事件详情失败');
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
      <Row gutter={16}>
        {/* 左侧：事件列表 */}
        <Col span={6}>
          <Card 
            title="热门事件 (Top 20)" 
            style={{ height: 'calc(100vh - 100px)', overflowY: 'auto' }}
            styles={{ body: { padding: '0 12px' } }}
          >
            <Spin spinning={loadingList}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {seriesList
                  .sort((a, b) => b.count - a.count) // 确保按热度排序
                  .slice(0, 20) // 仅显示 Top 20
                  .map((item, index) => (
                  <div
                    key={item.tag}
                    onClick={() => handleSelectSeries(item.tag)}
                    style={{ 
                      cursor: 'pointer', 
                      backgroundColor: currentSeries === item.tag ? '#e6f7ff' : 'transparent',
                      padding: '8px',
                      borderRadius: '4px',
                      transition: 'background 0.3s',
                      border: 'none',
                      display: 'flex',
                      flexDirection: 'column',
                      borderLeft: index < 3 ? '3px solid #ff4d4f' : '3px solid transparent' // 前三名高亮
                    }}
                  >
                    <Text strong style={{ fontSize: 14, marginBottom: 4 }}>{item.tag}</Text>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                      <Text type="secondary">
                        {dayjs(item.latest_date).format('MM-DD')}
                      </Text>
                      <span>
                        <Badge count={item.count} style={{ backgroundColor: '#52c41a', transform: 'scale(0.8)' }} overflowCount={999} /> 篇
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              {!loadingList && seriesList.length === 0 && (
                <Empty description="暂无聚合事件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Spin>
          </Card>
        </Col>
        
        {/* 右侧：时间轴 */}
        <Col span={14}>
          <Card 
            title={currentSeries ? `📅 ${currentSeries} - 发展脉络` : '事件详情'} 
            style={{ height: 'calc(100vh - 100px)', overflowY: 'auto' }}
            styles={{ body: { padding: '16px 24px' } }}
          >
            <Spin spinning={loadingNews}>
              {newsList.length > 0 ? (
                <Timeline style={{ marginTop: 10 }} items={
                  newsList.map(item => ({
                    key: item.id,
                    label: <span style={{ fontSize: '12px', color: '#999' }}>{dayjs(item.created_at).format('MM-DD HH:mm')}</span>,
                    children: <NewsCard item={item} />
                  }))
                } />
              ) : (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '300px' }}>
                  <Empty description="暂无数据或请选择左侧事件" />
                </div>
              )}
            </Spin>
          </Card>
        </Col>
        
        {/* 最右侧：关联分析 */}
        <Col span={4}>
           {currentSeries && (
             <RelatedSeries 
               currentTag={currentSeries} 
               onSelect={handleSelectSeries} 
             />
           )}
        </Col>
      </Row>
    </div>
  );
};

export default SeriesView;
