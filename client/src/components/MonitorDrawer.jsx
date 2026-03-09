import React, { useEffect, useState } from 'react';
import { Drawer, Row, Col, Statistic, Card, List, Tag, Badge, Descriptions, Progress } from 'antd';
import { SyncOutlined, DatabaseOutlined, ProjectOutlined, BugOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { getMonitorStats } from '../services/api';
import dayjs from 'dayjs';

const MonitorDrawer = ({ open, onClose }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const res = await getMonitorStats();
      setStats(res.data);
    } catch (error) {
      console.error("Failed to fetch monitor stats", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchStats();
      const timer = setInterval(fetchStats, 5000);
      return () => clearInterval(timer);
    }
  }, [open]);

  if (!stats) return <Drawer title="系统监控面板" open={open} onClose={onClose} width={600} />;

  return (
    <Drawer title="系统监控面板" open={open} onClose={onClose} width={600}>
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card bordered={false} style={{ background: '#f6ffed' }}>
            <Statistic 
              title="今日采集总量" 
              value={stats.collection.today} 
              prefix={<DatabaseOutlined />} 
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card bordered={false} style={{ background: '#e6f7ff' }}>
            <Statistic 
              title="待处理积压" 
              value={stats.collection.backlog} 
              prefix={<ClockCircleOutlined />} 
              valueStyle={{ color: stats.collection.backlog > 50 ? '#cf1322' : '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card bordered={false} style={{ background: '#fff7e6' }}>
            <Statistic 
              title="今日生成推演" 
              value={stats.topics.generatedToday} 
              suffix={`/ 总 ${stats.topics.total}`}
              prefix={<ProjectOutlined />} 
              valueStyle={{ color: '#d46b08' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card bordered={false} style={{ background: '#fff1f0' }}>
            <Statistic 
              title="今日处理失败" 
              value={stats.collection.failedToday} 
              prefix={<BugOutlined />} 
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>

      <Descriptions title="处理引擎状态" bordered style={{ marginTop: 24 }} column={1}>
        <Descriptions.Item label="运行状态">
          <Badge status={stats.analyzer.isRunning ? "processing" : "default"} text={stats.analyzer.isRunning ? "运行中" : "已暂停"} />
        </Descriptions.Item>
        <Descriptions.Item label="当前并发任务">
          {stats.analyzer.processingCount} / {stats.analyzer.maxConcurrency || 8} (Max)
        </Descriptions.Item>
        <Descriptions.Item label="上次处理时间">
            {stats.analyzer.lastProcessedTime ? dayjs(stats.analyzer.lastProcessedTime).format('HH:mm:ss') : '-'}
        </Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: 24 }}>
        <h4>当前正在处理的任务 ({stats.analyzer.processingCount})</h4>
        <List
          dataSource={stats.analyzer.currentTasks}
          renderItem={item => (
            <List.Item>
              <List.Item.Meta
                avatar={<SyncOutlined spin style={{ color: '#1890ff' }} />}
                title={item.title || `Task #${item.id}`}
                description={
                  <span>
                    ID: {item.id} | 开始时间: {dayjs(item.startTime).format('HH:mm:ss')}
                  </span>
                }
              />
            </List.Item>
          )}
          locale={{ emptyText: '当前无任务处理中' }}
        />
      </div>
    </Drawer>
  );
};

export default MonitorDrawer;
