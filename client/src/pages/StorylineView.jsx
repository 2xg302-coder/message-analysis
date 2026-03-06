import React, { useState, useEffect, useRef } from 'react';
import { Card, List, Tag, Typography, Button, Space, Tabs, Rate, message, DatePicker, Empty, Popconfirm, Drawer, Timeline, Row, Col, Statistic, Divider, Badge, Modal, Progress } from 'antd';
import { RocketOutlined, HistoryOutlined, ThunderboltOutlined, DeleteOutlined, ClockCircleOutlined, GlobalOutlined, LineChartOutlined, ReloadOutlined, BankOutlined, FireOutlined, SyncOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { getStorylinesByDate, getHistoryStorylines, generateStorylines, archiveStoryline, getStorylineSeries, getAllSeries, startBatchGeneration, getTaskStatus } from '../services/api';

const { Title, Paragraph, Text } = Typography;

// --- Components ---

const SeriesCard = ({ series, onClick }) => {
    const getIcon = (category) => {
        switch(category) {
            case 'macro': return <BankOutlined style={{ color: '#1890ff' }} />;
            case 'geopolitics': return <GlobalOutlined style={{ color: '#f5222d' }} />;
            case 'industry': return <RocketOutlined style={{ color: '#722ed1' }} />;
            default: return <FireOutlined style={{ color: '#fa8c16' }} />;
        }
    };

    const getStatusColor = (status) => status === 'active' ? 'processing' : 'default';

    return (
        <Card 
            hoverable 
            onClick={() => onClick(series)}
            style={{ height: '100%' }}
            actions={[
                <Space><ClockCircleOutlined /> 更新: {dayjs(series.updated_at).format('MM-DD')}</Space>
            ]}
        >
            <Card.Meta
                avatar={getIcon(series.category)}
                title={
                    <Space>
                        {series.title}
                        <Badge status={getStatusColor(series.status)} text={series.status === 'active' ? '活跃' : '归档'} />
                    </Space>
                }
                description={
                    <Paragraph ellipsis={{ rows: 3 }}>
                        {series.description}
                    </Paragraph>
                }
            />
            {series.current_summary && (
                <div style={{ marginTop: 12, background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>最新动态: {series.current_summary}</Text>
                </div>
            )}
            <div style={{ marginTop: 12 }}>
                {series.keywords && series.keywords.slice(0, 3).map(k => (
                    <Tag key={k}>{k}</Tag>
                ))}
            </div>
        </Card>
    );
};

const StorylineCard = ({ item, onArchive }) => {
  return (
    <Card 
      title={
        <Space>
          <Text strong style={{ fontSize: 16 }}>{item.title}</Text>
          <Tag color="blue">{item.date}</Tag>
        </Space>
      }
      extra={
        <Space>
            <Rate disabled defaultValue={item.importance} count={5} style={{ fontSize: 14 }} />
            {item.status === 'active' && onArchive && (
                <Popconfirm title="确定归档这条主线吗？" onConfirm={() => onArchive(item.id)}>
                    <Button type="text" icon={<DeleteOutlined />} size="small">归档</Button>
                </Popconfirm>
            )}
        </Space>
      }
      style={{ marginBottom: 16 }}
      type="inner"
    >
      <Paragraph>{item.description}</Paragraph>
      <div style={{ marginBottom: 8 }}>
        <Text type="secondary">关键词: </Text>
        {item.keywords && item.keywords.map((kw, idx) => (
          <Tag key={idx}>{kw}</Tag>
        ))}
      </div>
      
      {/* Related Info */}
      <Space direction="vertical" style={{ width: '100%', marginTop: 8 }}>
          {item.expected_impact && (
            <div style={{ padding: '8px', background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 4 }}>
               <Text type="success" strong><ThunderboltOutlined /> 预期影响: </Text>
               <Text>{item.expected_impact}</Text>
            </div>
          )}
          
          {(item.related_news_ids && item.related_news_ids.length > 0) && (
              <div style={{ padding: '8px', background: '#e6f7ff', border: '1px solid #91d5ff', borderRadius: 4 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                      关联新闻: {item.related_news_ids.length} 条
                  </Text>
              </div>
          )}
      </Space>
    </Card>
  );
};

// --- Main View ---

const StorylineView = () => {
  // Tabs: 'series' (Level 1) | 'daily' (Old View)
  const [activeTab, setActiveTab] = useState('series');
  
  // Series Data
  const [seriesList, setSeriesList] = useState([]);
  const [loadingSeries, setLoadingSeries] = useState(false);

  // Daily Data
  const [activeStorylines, setActiveStorylines] = useState([]);
  const [loadingDaily, setLoadingDaily] = useState(false);
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [generating, setGenerating] = useState(false);
  
  // Drawer State (For drilling down into a series)
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [currentSeries, setCurrentSeries] = useState(null);
  const [seriesTimeline, setSeriesTimeline] = useState([]);
  const [loadingTimeline, setLoadingTimeline] = useState(false);

  // Batch Generation State
  const [batchModalVisible, setBatchModalVisible] = useState(false);
  const [batchTaskId, setBatchTaskId] = useState(null);
  const [batchProgress, setBatchProgress] = useState(0);
  const [batchStatus, setBatchStatus] = useState(null);
  const [batchMessage, setBatchMessage] = useState('');
  const pollTimerRef = useRef(null);

  // --- Effects ---

  useEffect(() => {
      if (activeTab === 'series') {
          fetchSeries();
      } else if (activeTab === 'daily') {
          fetchDailyStorylines(selectedDate);
      }
  }, [activeTab]);

  useEffect(() => {
      if (activeTab === 'daily') {
          fetchDailyStorylines(selectedDate);
      }
  }, [selectedDate]);

  // Cleanup poll timer
  useEffect(() => {
      return () => {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      };
  }, []);

  // --- API Calls ---

  const fetchSeries = async () => {
      setLoadingSeries(true);
      try {
          const res = await getAllSeries('active');
          setSeriesList(res.data || []);
      } catch (error) {
          message.error('获取主题列表失败');
      } finally {
          setLoadingSeries(false);
      }
  };

  const fetchDailyStorylines = async (date) => {
    if (!date) return;
    setLoadingDaily(true);
    const dateStr = date.format('YYYY-MM-DD');
    try {
      const res = await getStorylinesByDate(dateStr);
      setActiveStorylines(res.data || []);
    } catch (error) {
      message.error('获取每日主线失败');
    } finally {
      setLoadingDaily(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedDate) return;
    setGenerating(true);
    const dateStr = selectedDate.format('YYYY-MM-DD');
    try {
      await generateStorylines(dateStr);
      message.success(`成功生成 ${dateStr} 的主线`);
      fetchDailyStorylines(selectedDate);
      // Also refresh series if we are in series view? No, stay in daily.
    } catch (error) {
      console.error(error);
      message.error('生成失败，请检查后端日志');
    } finally {
      setGenerating(false);
    }
  };

  const handleSeriesClick = async (series) => {
      setCurrentSeries(series);
      setDrawerVisible(true);
      setLoadingTimeline(true);
      setSeriesTimeline([]);
      try {
          const res = await getStorylineSeries(series.id);
          setSeriesTimeline(res.data || []);
      } catch (error) {
          message.error('获取时间线失败');
      } finally {
          setLoadingTimeline(false);
      }
  };

  // --- Batch Generation Logic ---

  const handleStartBatch = async () => {
      try {
          const res = await startBatchGeneration(7); // Default 7 days
          if (res.data && res.data.task_id) {
              setBatchTaskId(res.data.task_id);
              setBatchStatus('pending');
              setBatchProgress(0);
              setBatchMessage('任务已提交...');
              setBatchModalVisible(true);
              
              // Start Polling
              pollTimerRef.current = setInterval(() => checkBatchStatus(res.data.task_id), 2000);
          }
      } catch (error) {
          message.error('启动全量刷新失败');
      }
  };

  const checkBatchStatus = async (taskId) => {
      try {
          const res = await getTaskStatus(taskId);
          const { status, progress, message: msg } = res.data;
          
          setBatchStatus(status);
          setBatchProgress(progress);
          setBatchMessage(msg);
          
          if (status === 'completed' || status === 'failed') {
              clearInterval(pollTimerRef.current);
              if (status === 'completed') {
                  message.success('全量刷新完成！');
                  fetchSeries(); // Refresh list
              } else {
                  message.error('全量刷新失败: ' + msg);
              }
          }
      } catch (error) {
          console.error('Poll failed', error);
      }
  };

  // --- Renderers ---

  const renderSeriesList = () => (
      <div style={{ marginTop: 16 }}>
          <Space style={{ marginBottom: 16 }}>
             <Button icon={<ReloadOutlined />} onClick={fetchSeries}>刷新列表</Button>
             <Button 
                type="primary" 
                danger 
                icon={<SyncOutlined />} 
                onClick={handleStartBatch}
             >
                 全量刷新 (近7天)
             </Button>
          </Space>
          
          {loadingSeries ? <Card loading={true} /> : (
              <Row gutter={[16, 16]}>
                  {seriesList.map(series => (
                      <Col xs={24} sm={12} md={8} lg={6} key={series.id}>
                          <SeriesCard series={series} onClick={handleSeriesClick} />
                      </Col>
                  ))}
                  {seriesList.length === 0 && <Empty description="暂无活跃主题" />}
              </Row>
          )}
      </div>
  );

  const renderDailyView = () => (
      <div>
          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Text>选择日期:</Text>
              <DatePicker value={selectedDate} onChange={setSelectedDate} allowClear={false} />
              <Button 
                type="primary" 
                icon={<ThunderboltOutlined />} 
                loading={generating}
                onClick={handleGenerate}
              >
                AI 生成今日推演
              </Button>
            </Space>
          </Card>
          
          {loadingDaily ? (
             <Card loading={true} />
          ) : activeStorylines.length > 0 ? (
            activeStorylines.map(item => (
              <StorylineCard 
                key={item.id} 
                item={item} 
                // onArchive={handleArchive} // Disable archive in this view for simplicity
              />
            ))
          ) : (
            <Empty description="该日期暂无主线数据，请点击生成" />
          )}
      </div>
  );

  return (
    <div>
      <Title level={2}>深度追踪 (Deep Dive)</Title>
      <Paragraph>
        追踪全球核心宏观与地缘政治主题的演变脉络。
      </Paragraph>

      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab}
        items={[
            {
                key: 'series',
                label: <span><LineChartOutlined /> 核心主题 (Series)</span>,
                children: renderSeriesList()
            },
            {
                key: 'daily',
                label: <span><RocketOutlined /> 每日推演 (Daily)</span>,
                children: renderDailyView()
            }
        ]}
      />

      {/* Series Detail Drawer */}
      <Drawer
        title={
            currentSeries ? (
                <Space direction="vertical" size={0}>
                    <Text strong style={{ fontSize: 18 }}>{currentSeries.title}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>ID: {currentSeries.id}</Text>
                </Space>
            ) : "主题详情"
        }
        placement="right"
        width={700}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
          {currentSeries && (
              <div style={{ marginBottom: 24 }}>
                  <Paragraph>{currentSeries.description}</Paragraph>
                  <Space>
                      {currentSeries.keywords.map(k => <Tag key={k}>{k}</Tag>)}
                  </Space>
                  <Divider />
              </div>
          )}

          {loadingTimeline ? (
              <Card loading={true} />
          ) : (
            <Timeline mode="left">
                {seriesTimeline.length > 0 ? seriesTimeline.map(item => (
                    <Timeline.Item label={item.date} key={item.id}>
                        <Card 
                            size="small" 
                            title={item.title} 
                            extra={<Rate disabled defaultValue={item.importance} count={5} style={{ fontSize: 12 }} />}
                            style={{ borderColor: item.importance >= 4 ? '#ffccc7' : '#f0f0f0' }}
                        >
                            <Paragraph ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}>
                                {item.description}
                            </Paragraph>
                            {item.expected_impact && (
                                <div style={{ marginTop: 8 }}>
                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                        <ThunderboltOutlined /> 影响: {item.expected_impact}
                                    </Text>
                                </div>
                            )}
                        </Card>
                    </Timeline.Item>
                )) : <Empty description="该主题暂无剧情推进" />}
            </Timeline>
          )}
      </Drawer>

      {/* Batch Generation Modal */}
      <Modal
          title="全量刷新历史数据"
          open={batchModalVisible}
          footer={null}
          onCancel={() => {
              if (batchStatus === 'processing') {
                  message.warning('任务正在后台运行，您可以关闭窗口，稍后刷新列表查看结果。');
              }
              setBatchModalVisible(false);
          }}
          maskClosable={false}
      >
          <div style={{ textAlign: 'center', padding: 24 }}>
              <Progress type="circle" percent={batchProgress} status={batchStatus === 'failed' ? 'exception' : (batchStatus === 'completed' ? 'success' : 'active')} />
              <div style={{ marginTop: 16 }}>
                  <Text strong>{batchMessage}</Text>
              </div>
              <div style={{ marginTop: 8 }}>
                  <Text type="secondary">正在重新分析过去7天的新闻与事件，重构主题脉络...</Text>
              </div>
          </div>
      </Modal>
    </div>
  );
};

export default StorylineView;
