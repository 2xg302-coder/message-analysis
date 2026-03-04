import React from 'react';
import { Typography, Card, Row, Col } from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

const { Title } = Typography;

// 模拟数据 - 后续应从API获取
const data = [
  { name: '08:00', sentiment: 40, heat: 24 },
  { name: '09:00', sentiment: 30, heat: 13 },
  { name: '10:00', sentiment: 20, heat: 98 },
  { name: '11:00', sentiment: 27, heat: 39 },
  { name: '12:00', sentiment: 18, heat: 48 },
  { name: '13:00', sentiment: 23, heat: 38 },
  { name: '14:00', sentiment: 34, heat: 43 },
];

const Trends = () => {
  return (
    <div>
      <Title level={2}>趋势分析</Title>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title="情感走势 (模拟数据)">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="sentiment" stroke="#8884d8" activeDot={{ r: 8 }} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={24}>
          <Card title="热度分析 (模拟数据)">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="heat" fill="#82ca9d" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Trends;
