import React, { useState, useEffect, useRef } from 'react';
import { Card, List, Tag, Typography, Button, Space, Tabs, Rate, message, DatePicker, Empty, Popconfirm, Drawer, Timeline, Row, Col, Statistic, Divider, Badge, Modal, Progress } from 'antd';
import { RocketOutlined, HistoryOutlined, ThunderboltOutlined, DeleteOutlined, ClockCircleOutlined, GlobalOutlined, LineChartOutlined, ReloadOutlined, BankOutlined, FireOutlined, SyncOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { getStorylinesByDate, getHistoryStorylines, generateStorylines, archiveStoryline, getStorylineSeries, getAllSeries, startBatchGeneration, getTaskStatus } from '../services/api';

const { Title, Paragraph, Text } = Typography;

// Helper
const getIcon = (category) => {
    switch(category) {
        case 'macro': return <BankOutlined style={{ color: '#1890ff', fontSize: 24 }} />;
        case 'geopolitics': return <GlobalOutlined style={{ color: '#f5222d', fontSize: 24 }} />;
        case 'industry': return <RocketOutlined style={{ color: '#722ed1', fontSize: 24 }} />;
        default: return <FireOutlined style={{ color: '#fa8c16', fontSize: 24 }} />;
    }
};

// --- Components ---

const SeriesCard = ({ series, onClick }) => {
    const getStatusColor = (status) => status === 'active' ? 'processing' : 'default';

    return (
        <Card 
            hoverable 
            onClick={() => onClick(series)}
            style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
            bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column' }}
            actions={[
                <Space style={{ fontSize: 12, color: '#8c8c8c' }}><ClockCircleOutlined /> 更新: {dayjs(series.updated_at).format('MM-DD HH:mm')}</Space>
            ]}
        >
            <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 16 }}>
                <div style={{ marginRight: 12, paddingTop: 4 }}>
                    {getIcon(series.category)}
                </div>
                <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <Text strong style={{ fontSize: 16 }}>{series.title}</Text>
                        <Badge status={getStatusColor(series.status)} text={series.status === 'active' ? '活跃' : '归档'} />
                    </div>
                    <Paragraph ellipsis={{ rows: 2 }} type="secondary" style={{ fontSize: 13, marginBottom: 0 }}>
                        {series.description}
                    </Paragraph>
                </div>
            </div>

            {series.current_summary ? (
                <div style={{ 
                    marginTop: 'auto', 
                    background: '#f0f5ff', 
                    border: '1px solid #adc6ff',
                    padding: '8px 12px', 
                    borderRadius: 6 
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                        <ThunderboltOutlined style={{ color: '#1890ff', marginRight: 6 }} />
                        <Text strong style={{ color: '#1d39c4', fontSize: 13 }}>最新进展</Text>
                    </div>
                    <Paragraph 
                        ellipsis={{ rows: 4, expandable: true, symbol: '展开' }} 
                        style={{ fontSize: 13, color: '#262626', marginBottom: 0 }}
                    >
                        {series.current_summary}
                    </Paragraph>
                </div>
            ) : (
                <div style={{ marginTop: 'auto', padding: '16px 0', textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>暂无最新进展摘要</Text>
                </div>
            )}
            
            <div style={{ marginTop: 12 }}>
                {series.keywords && series.keywords.slice(0, 3).map(k => (
                    <Tag key={k} style={{ fontSize: 12 }}>{k}</Tag>
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
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Space align="center">
                        {getIcon(currentSeries.category)}
                        <Space direction="vertical" size={0}>
                            <Text strong style={{ fontSize: 18 }}>{currentSeries.title}</Text>
                            <Text type="secondary" style={{ fontSize: 12 }}>ID: {currentSeries.id}</Text>
                        </Space>
                    </Space>
                    <Badge 
                        status={currentSeries.status === 'active' ? 'processing' : 'default'} 
                        text={currentSeries.status === 'active' ? '活跃' : '归档'} 
                    />
                </div>
            ) : "主题详情"
        }
        placement="right"
        width={720}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        bodyStyle={{ padding: '24px', background: '#fcfcfc' }}
      >
          {currentSeries && (
              <>
                {currentSeries.current_summary ? (
                    <div style={{ 
                        marginBottom: 24, 
                        padding: '16px 20px', 
                        background: '#f0f5ff', 
                        borderRadius: 8, 
                        border: '1px solid #adc6ff',
                        boxShadow: '0 2px 6px rgba(24, 144, 255, 0.08)'
                    }}>
                        <Space align="center" style={{ marginBottom: 12 }}>
                            <ThunderboltOutlined style={{ color: '#1890ff', fontSize: 18 }} />
                            <Text strong style={{ fontSize: 16, color: '#1d39c4' }}>最新进展 (Prior Knowledge)</Text>
                        </Space>
                        <Paragraph style={{ marginBottom: 0, fontSize: 14, lineHeight: '1.6', color: '#262626' }}>
                            {currentSeries.current_summary}
                        </Paragraph>
                    </div>
                ) : (
                    <div style={{ marginBottom: 24, padding: '16px', background: '#fafafa', borderRadius: 8, textAlign: 'center', border: '1px dashed #d9d9d9' }}>
                        <Text type="secondary">暂无最新进展摘要</Text>
                    </div>
                )}

                <div style={{ marginBottom: 32, padding: '0 8px' }}>
                    <Text strong style={{ fontSize: 14, color: '#595959' }}>背景描述</Text>
                    <Paragraph style={{ marginTop: 8, color: '#595959', fontSize: 14 }}>
                        {currentSeries.description}
                    </Paragraph>
                    <div style={{ marginTop: 12 }}>
                        {currentSeries.keywords && currentSeries.keywords.map(k => (
                            <Tag key={k} style={{ background: '#f5f5f5', border: '1px solid #d9d9d9' }}>{k}</Tag>
                        ))}
                    </div>
                </div>

                <Divider orientation="left" style={{ borderColor: '#e8e8e8' }}>
                    <Space>
                        <HistoryOutlined />
                        <span style={{ fontSize: 15, fontWeight: 600 }}>演变时间线</span>
                    </Space>
                </Divider>
              </>
          )}

          {loadingTimeline ? (
              <Card loading={true} bordered={false} />
          ) : (
            <Timeline 
                mode="left" 
                style={{ marginTop: 24, paddingLeft: 0 }}
            >
                {seriesTimeline.length > 0 ? seriesTimeline.map(item => (
                    <Timeline.Item 
                        key={item.id} 
                        label={
                            <div style={{ width: 50, textAlign: 'right', paddingRight: 8 }}>
                                <div style={{ fontWeight: 'bold', fontSize: 13, color: '#262626' }}>
                                    {dayjs(item.date).format('MM-DD')}
                                </div>
                            </div>
                        }
                        color={item.importance >= 4 ? 'red' : 'blue'}
                    >
                       <div 
                           style={{ 
                               background: '#fff', 
                               borderRadius: 8,
                               boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                               border: '1px solid #f0f0f0',
                               marginBottom: 12,
                               padding: '16px'
                           }}
                       >
                           <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                               <Text strong style={{ fontSize: 15, color: '#262626' }}>{item.title}</Text>
                               <Rate disabled defaultValue={item.importance} count={5} style={{ fontSize: 12, flexShrink: 0, marginLeft: 8 }} />
                           </div>
                           
                           <Paragraph style={{ marginBottom: 16, color: '#595959', fontSize: 14, lineHeight: '1.6' }}>
                               {item.description}
                           </Paragraph>

                           <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                               {item.expected_impact && (
                                   <div style={{ 
                                       padding: '10px 12px', 
                                       background: '#f6ffed', 
                                       border: '1px solid #b7eb8f', 
                                       borderRadius: 6,
                                       display: 'flex',
                                       alignItems: 'flex-start'
                                   }}>
                                       <ThunderboltOutlined style={{ color: '#52c41a', marginTop: 3, marginRight: 8, fontSize: 14 }} />
                                       <div style={{ flex: 1 }}>
                                           <Text strong style={{ fontSize: 12, color: '#389e0d' }}>预期影响</Text>
                                           <div style={{ fontSize: 13, color: '#262626', marginTop: 2 }}>{item.expected_impact}</div>
                                       </div>
                                   </div>
                               )}
                               
                               {item.keywords && item.keywords.length > 0 && (
                                   <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
                                       <Text type="secondary" style={{ fontSize: 12 }}>关键词:</Text>
                                       {item.keywords.map(k => (
                                           <Tag key={k} style={{ margin: 0, fontSize: 12, border: 'none', background: 'rgba(0,0,0,0.04)', color: '#595959' }}>#{k}</Tag>
                                       ))}
                                   </div>
                               )}
                           </div>
                       </div>
                    </Timeline.Item>
                )) : <Empty description="该主题暂无剧情推进" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
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
