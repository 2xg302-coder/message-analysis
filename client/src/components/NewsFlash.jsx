import React from 'react';
import { Row, Col, Tag, Typography } from 'antd';
import dayjs from 'dayjs';

const { Text } = Typography;

const NewsFlash = ({ item }) => {
  return (
    <div style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
      <Row align="middle" style={{ width: '100%' }}>
        <Col span={3}>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {dayjs(item.created_at).format('HH:mm:ss')}
          </Text>
        </Col>
        <Col span={16}>
          <Text strong style={{ marginRight: 8 }}>{item.title}</Text>
          {item.tags && Array.isArray(item.tags) && item.tags.map(tag => (
            <Tag key={tag} color="blue" style={{ fontSize: '10px', lineHeight: '18px' }}>{tag}</Tag>
          ))}
          {/* 三元组迷你展示 */}
          {item.triples && item.triples.length > 0 && (
            <div style={{ marginTop: 4, fontSize: '11px', color: '#666' }}>
              {item.triples.slice(0, 2).map((t, idx) => (
                <span key={idx} style={{ marginRight: 10, background: '#f5f5f5', padding: '0 4px', borderRadius: 2 }}>
                  {t.subject} → {t.predicate} → {t.object}
                </span>
              ))}
              {item.triples.length > 2 && <span style={{ color: '#999' }}>+{item.triples.length - 2}</span>}
            </div>
          )}
        </Col>
        <Col span={5} style={{ textAlign: 'right' }}>
           {item.sentiment_score > 0.5 && <Tag color="red">利好</Tag>}
           {item.sentiment_score < -0.5 && <Tag color="green">利空</Tag>}
           {item.impact_score >= 4 && <Tag color="gold">重要</Tag>}
        </Col>
      </Row>
    </div>
  );
};

export default NewsFlash;
