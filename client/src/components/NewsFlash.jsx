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
