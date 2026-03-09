import React from 'react';
import { Card, Tag, Typography, Space } from 'antd';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

const { Text, Paragraph } = Typography;

// 获取边框颜色
const getBorderColor = (item) => {
  const sentiment = item.sentiment_score || 0;
  const impact = item.impact_score || 0;

  if (sentiment > 0.5) return '#f5222d'; // 利好 (红)
  if (sentiment < -0.5) return '#52c41a'; // 利空 (绿)
  if (impact >= 4) return '#faad14'; // 重要 (黄)
  return undefined;
};

const NewsCard = ({ item }) => {
  const navigate = useNavigate();
  const analysis = item.analysis || {};
  const hasAnalysis = !!item.analysis;
  const borderColor = getBorderColor(item);

  return (
      <Card 
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '16px', fontWeight: 'bold' }}>
              {item.title || (item.content ? item.content.substring(0, 30) + '...' : '无标题')}
            </span>
            <Space>
              {item.sentiment_score !== undefined && (
                 <Tag color={item.sentiment_score > 0 ? 'red' : (item.sentiment_score < 0 ? 'green' : 'default')}>
                   情感: {item.sentiment_score.toFixed(1)}
                 </Tag>
              )}
              {item.impact_score !== undefined && (
                 <Tag color="gold">影响: {item.impact_score}</Tag>
              )}
            </Space>
          </div>
        }
        extra={<Text type="secondary">{dayjs(item.created_at).format('MM-DD HH:mm')}</Text>}
        hoverable
        style={{ 
          borderColor: borderColor,
          borderLeft: borderColor ? `4px solid ${borderColor}` : undefined 
        }}
      >
        {/* 摘要区域 */}
        {hasAnalysis && analysis.summary ? (
          <div style={{ marginBottom: 16, padding: '12px', background: '#f9f9f9', borderRadius: '4px' }}>
            <Text strong>📝 AI 摘要：</Text>
            <Text>{analysis.summary}</Text>
          </div>
        ) : null}

        {/* 标签和实体 */}
        <div style={{ marginBottom: 12 }}>
            {item.tags && Array.isArray(item.tags) && item.tags.map(tag => <Tag key={tag} color="blue">#{tag}</Tag>)}
            
            {item.entities && !Array.isArray(item.entities) && typeof item.entities === 'object' && Object.keys(item.entities).map((name, idx) => (
              <Tag key={idx} color="cyan">{name}</Tag>
            ))}
            
            {item.entities && Array.isArray(item.entities) && item.entities.map((e, idx) => (
              <Tag key={idx} color="cyan">{e.name || e}</Tag>
            ))}

            {item.triples && Array.isArray(item.triples) && item.triples.length > 0 && (
              <div style={{ marginTop: 8, padding: '8px', background: '#f0f5ff', borderRadius: '4px', fontSize: '12px' }}>
                <Text strong type="secondary" style={{ marginRight: 8 }}>🕸️ 关系图谱:</Text>
                {item.triples.map((t, idx) => (
                   <Tag key={idx} color="geekblue" style={{ marginBottom: 4 }}>
                     {t.subject} <span style={{ color: '#999' }}>→</span> {t.predicate} <span style={{ color: '#999' }}>→</span> {t.object}
                   </Tag>
                ))}
              </div>
            )}

            {hasAnalysis && analysis.event_tag && (
              <Tag color="purple" style={{ cursor: 'pointer', marginTop: 8 }} onClick={() => navigate(`/series/${encodeURIComponent(analysis.event_tag)}`)}>
                🎬 {analysis.event_tag}
              </Tag>
            )}
        </div>

        <Paragraph ellipsis={{ rows: 3, expandable: true, symbol: '展开全文' }} style={{ color: '#666' }}>
          {item.content}
        </Paragraph>
        
        <div style={{ marginTop: 10, display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#999' }}>
          <span>来源: {item.source || '未知'}</span>
        </div>
      </Card>
  );
};

export default NewsCard;
