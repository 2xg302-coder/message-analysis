import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Typography, Spin, Table, Tag, Statistic, Progress, Space, DatePicker, Radio, Button, Modal, List, Empty, Switch, message, Popconfirm, Form, InputNumber, Alert } from 'antd';
import { PieChart, Pie, Cell, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';
import { DatabaseOutlined, RocketOutlined, TagOutlined, DeploymentUnitOutlined, ReloadOutlined, ApartmentOutlined, DeleteOutlined, ClearOutlined } from '@ant-design/icons';
import { getStats, getTagStats, getTypeStats, getTopEntities, getAnalysisStatus, getNews, setAnalysisControl, getIngestionSources, setIngestionSourceEnabled, getEntityGraph, getMaintenanceStats, cleanupNews, deleteSourceNews, vacuumDatabase } from '../services/api';
import dayjs from 'dayjs';
import NewsCard from '../components/NewsCard';
import ReactECharts from 'echarts-for-react';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

const DataExplorer = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, analyzed: 0, pending: 0 });
  const [dbStats, setDbStats] = useState({});
  const [tags, setTags] = useState([]);
  const [types, setTypes] = useState([]);
  const [entities, setEntities] = useState([]);
  const [analysisStatus, setAnalysisStatus] = useState({ isRunning: false, currentTask: null });
  const [toggling, setToggling] = useState(false);
  const [sourceConfigs, setSourceConfigs] = useState([]);
  const [sourceToggling, setSourceToggling] = useState({});

  // Cleanup state
  const [cleanupModalVisible, setCleanupModalVisible] = useState(false);
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [cleanupForm] = Form.useForm();
  const [cleanupPreview, setCleanupPreview] = useState(null);

  // Graph state
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [graphType, setGraphType] = useState('cooccurrence');
  const [graphLoading, setGraphLoading] = useState(false);

  const fetchGraphData = async () => {
    setGraphLoading(true);
    try {
        const res = await getEntityGraph(48, false, graphType); // Default 48 hours
        if (res.data && res.data.success) {
            setGraphData(res.data.data);
        }
    } catch (error) {
        console.error("Failed to fetch graph data", error);
    } finally {
        setGraphLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, [graphType]);
  
  // Date filter state
  const [dateRange, setDateRange] = useState([dayjs().subtract(29, 'day'), dayjs()]);
  const [quickDate, setQuickDate] = useState('month'); // 'day', 'week', 'month', 'all'

  // Tag display state
  const [showAllTags, setShowAllTags] = useState(false);
  const displayedTags = showAllTags ? tags : tags.slice(0, 20);

  // News Modal state
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedTag, setSelectedTag] = useState(null);
  const [tagNews, setTagNews] = useState([]);
  const [tagNewsLoading, setTagNewsLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    let startDate = null;
    let endDate = null;

    if (quickDate !== 'all' && dateRange && dateRange[0] && dateRange[1]) {
      startDate = dateRange[0].format('YYYY-MM-DD');
      endDate = dateRange[1].format('YYYY-MM-DD');
    }

    try {
      const [statsRes, tagsRes, typesRes, entitiesRes, statusRes, sourceRes, dbStatsRes] = await Promise.all([
        getStats(startDate, endDate),
        getTagStats(100, startDate, endDate),
        getTypeStats(startDate, endDate),
        getTopEntities(50, startDate, endDate),
        getAnalysisStatus(),
        getIngestionSources(),
        getMaintenanceStats()
      ]);

      if (statsRes.data.success) setStats(statsRes.data.data);
      if (tagsRes.data.success) setTags(tagsRes.data.data);
      if (typesRes.data.success) setTypes(typesRes.data.data);
      if (entitiesRes.data.success) setEntities(entitiesRes.data.data);
      if (statusRes.data.success) setAnalysisStatus(statusRes.data.data);
      if (sourceRes.data.success) setSourceConfigs(sourceRes.data.data);
      if (dbStatsRes.data) setDbStats(dbStatsRes.data);

    } catch (error) {
      console.error("Failed to fetch explorer data", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Only auto-refresh status, not stats (stats depend on date range which doesn't change automatically)
    const interval = setInterval(async () => {
       const statusRes = await getAnalysisStatus();
       if (statusRes.data.success) setAnalysisStatus(statusRes.data.data);
    }, 10000); 
    return () => clearInterval(interval);
  }, [dateRange, quickDate]); // Trigger when dateRange or quickDate changes

  // Merge sources from config and DB stats
  const getAllSources = () => {
      const configSources = new Set(sourceConfigs.map(s => s.source));
      const dbSources = Object.keys(dbStats.by_source || {});
      
      // Combine all unique source names
      const allSourceNames = Array.from(new Set([...configSources, ...dbSources]));
      
      return allSourceNames.map(name => {
          const config = sourceConfigs.find(s => s.source === name);
          return {
              source: name,
              enabled: config ? config.enabled : false, // Default to false if not in config (likely unknown/legacy)
              is_unknown: !config, // Flag to indicate if it's not in official config
              count: dbStats.by_source?.[name] || 0
          };
      }).sort((a, b) => b.count - a.count); // Sort by count DESC
  };

  const displayedSources = getAllSources();

  const getGraphOption = () => {
    return {
      title: {
          text: graphType === 'cooccurrence' ? '实体共现网络' : '实体因果图谱',
          subtext: '基于最近48小时新闻数据',
          left: 'center',
          textStyle: { fontSize: 14 }
      },
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
            if (params.dataType === 'edge') {
                const label = params.data.label && params.data.label.formatter ? params.data.label.formatter : '';
                return `${params.data.source} ${label ? '→ ' + label + ' →' : '-'} ${params.data.target} (权重: ${params.data.value})`;
            }
            return `${params.name}: ${params.value} (热度)`;
        }
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: graphData.nodes,
          links: graphData.links,
          roam: true,
          label: {
            show: true,
            position: 'right',
            formatter: '{b}'
          },
          force: {
            repulsion: 200,
            edgeLength: [50, 200],
            gravity: 0.1
          },
          edgeSymbol: graphType === 'causal' ? ['none', 'arrow'] : ['none', 'none'],
          edgeSymbolSize: 8,
          edgeLabel: {
            fontSize: 10
          },
          lineStyle: {
            color: 'source',
            curveness: 0.2,
            opacity: 0.6
          },
          draggable: true,
          emphasis: {
            focus: 'adjacency',
            lineStyle: {
              width: 4
            }
          }
        }
      ]
    };
  };

  const handleQuickDateChange = (e) => {
    const value = e.target.value;
    setQuickDate(value);
    
    if (value === 'all') {
      setDateRange(null);
      return;
    }

    const end = dayjs();
    let start = dayjs();
    
    if (value === 'day') start = dayjs(); 
    else if (value === 'week') start = dayjs().subtract(6, 'day');
    else if (value === 'month') start = dayjs().subtract(29, 'day');
    
    setDateRange([start, end]);
  };

  const handleTagClick = async (tag) => {
    setSelectedTag(tag);
    setModalVisible(true);
    setTagNewsLoading(true);
    
    let startDate = null;
    let endDate = null;

    if (quickDate !== 'all' && dateRange && dateRange[0] && dateRange[1]) {
      startDate = dateRange[0].format('YYYY-MM-DD');
      endDate = dateRange[1].format('YYYY-MM-DD');
    }
    
    try {
      const res = await getNews({ 
        tag: tag.name, 
        startDate, 
        endDate,
        limit: 50 
      });
      if (res.data && res.data.data) {
        setTagNews(res.data.data);
      }
    } catch (error) {
      console.error("Failed to fetch tag news", error);
    } finally {
      setTagNewsLoading(false);
    }
  };

  // Entity Table Columns
  const entityColumns = [
    { title: '实体名称', dataIndex: 'name', key: 'name', render: text => <Text strong>{text}</Text> },
    { title: '提及次数', dataIndex: 'count', key: 'count', sorter: (a, b) => a.count - b.count, defaultSortOrder: 'descend' },
    { 
      title: '热度', 
      key: 'hotness', 
      render: (_, record) => (
        <Progress percent={Math.min(100, (record.count / (entities[0]?.count || 1)) * 100)} showInfo={false} size="small" />
      ) 
    }
  ];

    const handleToggleAnalysis = async () => {
        setToggling(true);
        try {
            const newStatus = !analysisStatus.isRunning;
            const res = await setAnalysisControl(newStatus);
            if (res.data.success) {
                setAnalysisStatus(prev => ({ ...prev, isRunning: newStatus }));
            }
        } catch (error) {
            console.error("Failed to toggle analysis", error);
        } finally {
            setToggling(false);
        }
    };

  const handleToggleSource = async (source, enabled) => {
    setSourceToggling(prev => ({ ...prev, [source]: true }));
    try {
      const res = await setIngestionSourceEnabled(source, enabled);
      if (res.data.success) {
        setSourceConfigs(prev => prev.map(item => item.source === source ? { ...item, enabled } : item));
        message.success(`${source} 拉取已${enabled ? '开启' : '关闭'}`);
      }
    } catch (error) {
      message.error(`${source} 开关更新失败`);
    } finally {
      setSourceToggling(prev => ({ ...prev, [source]: false }));
    }
  };

  // Maintenance Handlers
  const handlePreviewCleanup = async () => {
      try {
          const values = await cleanupForm.validateFields();
          setCleanupLoading(true);
          const res = await cleanupNews({ ...values, dry_run: true });
          if (res.data) {
              setCleanupPreview(res.data);
          }
      } catch (error) {
          message.error("预览失败");
      } finally {
          setCleanupLoading(false);
      }
  };

  const handleExecuteCleanup = async () => {
      try {
          const values = await cleanupForm.validateFields();
          setCleanupLoading(true);
          const res = await cleanupNews({ ...values, dry_run: false });
          if (res.data) {
              message.success(`清理完成，删除了 ${res.data.deleted_count} 条数据`);
              setCleanupModalVisible(false);
              setCleanupPreview(null);
              // 强制刷新所有数据，包括统计信息
              await fetchData();
          }
      } catch (error) {
          message.error("清理失败");
      } finally {
          setCleanupLoading(false);
      }
  };

  const handleDeleteSource = async (source) => {
      try {
          setLoading(true);
          const res = await deleteSourceNews(source);
          if (res.data) {
              message.success(`已删除来源 ${source} 的 ${res.data.deleted_count} 条数据`);
              // 强制刷新所有数据，包括统计信息
              await fetchData();
          }
      } catch (error) {
          message.error("删除失败");
      } finally {
          setLoading(false);
      }
  };

  const handleVacuum = async () => {
      try {
          const res = await vacuumDatabase();
          if (res.data) {
              message.success("已触发数据库 VACUUM (后台执行)");
          }
      } catch (error) {
          message.error("操作失败");
      }
  };

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>数据资产概览</Title>
          <Text type="secondary">实时监控系统数据积累状态与模型分析进度</Text>
        </div>
        <Space>
          <Radio.Group value={quickDate} onChange={handleQuickDateChange}>
            <Radio.Button value="day">今天</Radio.Button>
            <Radio.Button value="week">近一周</Radio.Button>
            <Radio.Button value="month">近一月</Radio.Button>
            <Radio.Button value="all">全部</Radio.Button>
          </Radio.Group>
          <RangePicker 
            value={dateRange} 
            onChange={(dates) => {
              setDateRange(dates);
              setQuickDate('custom');
            }}
            allowClear={false}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchData} />
        </Space>
      </div>

      <Spin spinning={loading}>
        {/* 系统状态看板 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic 
                title="数据总量 (选定范围内)" 
                value={stats.total} 
                prefix={<DatabaseOutlined />} 
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="已智能分析" 
                value={stats.analyzed} 
                suffix={`/ ${stats.total}`} 
                styles={{ content: { color: '#3f8600' } }}
              />
              <Progress percent={Math.round((stats.analyzed / (stats.total || 1)) * 100)} size="small" status="active" />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="待处理队列" 
                value={stats.pending} 
                prefix={<RocketOutlined />} 
                styles={{ content: { color: stats.pending > 100 ? '#cf1322' : '#fa8c16' } }} 
                extra={
                    <Button 
                        size="small" 
                        type={analysisStatus.isRunning ? 'default' : 'primary'}
                        danger={analysisStatus.isRunning}
                        loading={toggling}
                        onClick={handleToggleAnalysis}
                    >
                        {analysisStatus.isRunning ? '暂停分析' : '启动分析'}
                    </Button>
                }
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {analysisStatus.isRunning ? '🟢 分析服务运行中 (Fast Mode)' : '🔴 分析服务已暂停'}
              </Text>
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="热门标签数" 
                value={tags.length} 
                prefix={<TagOutlined />} 
              />
            </Card>
          </Col>
        </Row>
        
        {/* 数据源管理与维护 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col span={16}>
            <Card title="消息源管理">
              <Table 
                dataSource={displayedSources} 
                rowKey="source" 
                pagination={false}
                size="small"
                columns={[
                    { 
                        title: '来源名称', 
                        dataIndex: 'source', 
                        key: 'source', 
                        render: (text, record) => (
                            <Space>
                                <Text strong>{text}</Text>
                                {record.is_unknown && <Tag color="warning">未配置</Tag>}
                            </Space>
                        ) 
                    },
                    { 
                        title: '当前数据量', 
                        key: 'count', 
                        render: (_, record) => (
                            <Text>{record.count}</Text>
                        ) 
                    },
                    { 
                        title: '状态', 
                        key: 'enabled', 
                        render: (_, record) => (
                            <Switch
                                checked={record.enabled}
                                loading={sourceToggling[record.source]}
                                checkedChildren="开启"
                                unCheckedChildren="关闭"
                                disabled={record.is_unknown} // Disable switch for unknown sources
                                onChange={(checked) => handleToggleSource(record.source, checked)}
                            />
                        ) 
                    },
                    {
                        title: '操作',
                        key: 'action',
                        render: (_, record) => (
                            <Popconfirm
                                title={`确定要清空 ${record.source} 的所有数据吗？`}
                                description="此操作不可恢复！"
                                onConfirm={() => handleDeleteSource(record.source)}
                                okText="确定删除"
                                cancelText="取消"
                                okButtonProps={{ danger: true }}
                            >
                                <Button type="text" danger icon={<DeleteOutlined />}>清空数据</Button>
                            </Popconfirm>
                        )
                    }
                ]}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card title="数据库维护" extra={<Tag color="blue">Size: {dbStats.db_size_mb || 0} MB</Tag>}>
                <Space direction="vertical" style={{ width: '100%' }}>
                    <Alert 
                        message="低价值数据占比" 
                        description={
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span>Low Value (Score &lt; 4):</span>
                                <Text strong>{dbStats.by_score?.low || 0}</Text>
                            </div>
                        }
                        type="info" 
                        showIcon 
                    />
                    <Button block icon={<ClearOutlined />} onClick={() => setCleanupModalVisible(true)}>
                        清理过期/低价值数据
                    </Button>
                    <Popconfirm
                        title="确定执行 VACUUM？"
                        description="这将重建数据库文件以释放空间，可能会暂时阻塞写入。"
                        onConfirm={handleVacuum}
                    >
                        <Button block>释放磁盘空间 (VACUUM)</Button>
                    </Popconfirm>
                </Space>
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          {/* 事件类型分布 */}
          <Col span={12}>
            <Card title="事件类型分布 (Event Types)">
              {types.length > 0 ? (
                <div style={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={types}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {types.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <RechartsTooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" style={{ height: 300, display: 'flex', flexDirection: 'column', justifyContent: 'center' }} />
              )}
            </Card>
          </Col>

          {/* 标签云 (Tags Cloud) */}
          <Col span={12}>
            <Card title="热门标签云 (Tags Cloud)" extra={
              tags.length > 20 && (
                <Button type="link" onClick={() => setShowAllTags(!showAllTags)}>
                  {showAllTags ? '收起' : '查看更多'}
                </Button>
              )
            } style={{ height: '100%' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', maxHeight: showAllTags ? 400 : 300, overflowY: 'auto' }}>
                {displayedTags.map((tag, index) => {
                  const isHot = index < 10;
                  const color = isHot ? 'magenta' : index < 30 ? 'geekblue' : 'default';
                  const fontSize = isHot ? 16 : 14;
                  return (
                    <Tag 
                      key={tag.name} 
                      color={color} 
                      style={{ fontSize: fontSize, padding: '4px 8px', cursor: 'pointer' }}
                      onClick={() => handleTagClick(tag)}
                    >
                      {tag.name} ({tag.value})
                    </Tag>
                  );
                })}
              </div>
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {/* 实体关系图谱 */}
          <Col span={24}>
            <Card 
                title={<Space><ApartmentOutlined /> 实体关系图谱 (Entity Graph)</Space>}
                extra={
                    <Space>
                        <Switch 
                            checkedChildren="因果图 (Causal)" 
                            unCheckedChildren="共现图 (Co-occurrence)" 
                            checked={graphType === 'causal'}
                            onChange={(checked) => setGraphType(checked ? 'causal' : 'cooccurrence')}
                        />
                        <Button icon={<ReloadOutlined />} onClick={fetchGraphData} loading={graphLoading} size="small" />
                    </Space>
                }
            >
                <Spin spinning={graphLoading}>
                    {graphData.nodes.length > 0 ? (
                        <ReactECharts option={getGraphOption()} style={{ height: 500 }} />
                    ) : (
                        <Empty description="暂无图谱数据" style={{ height: 500, display: 'flex', flexDirection: 'column', justifyContent: 'center' }} />
                    )}
                </Spin>
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {/* 实体排行 */}
          <Col span={24}>
            <Card title={<Space><DeploymentUnitOutlined /> 核心实体排行 (Top Entities)</Space>}>
              <Table 
                dataSource={entities} 
                columns={entityColumns} 
                rowKey="name" 
                pagination={{ pageSize: 10 }} 
                size="small"
              />
            </Card>
          </Col>
        </Row>
      </Spin>

      {/* 新闻详情弹框 */}
      <Modal
        title={selectedTag ? `标签：#${selectedTag.name} 相关新闻` : '相关新闻'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={800}
        styles={{ body: { maxHeight: '60vh', overflowY: 'auto' } }}
      >
        <Spin spinning={tagNewsLoading}>
          {tagNews.length > 0 ? (
            <List
              itemLayout="vertical"
              dataSource={tagNews}
              renderItem={item => (
                <List.Item key={item.id}>
                  <NewsCard item={item} />
                </List.Item>
              )}
            />
          ) : (
            <Empty description="暂无相关新闻" />
          )}
        </Spin>
      </Modal>

      {/* 清理数据弹框 */}
      <Modal
          title="清理过期/低价值数据"
          open={cleanupModalVisible}
          onCancel={() => {
              setCleanupModalVisible(false);
              setCleanupPreview(null);
              cleanupForm.resetFields();
          }}
          footer={[
              <Button key="cancel" onClick={() => setCleanupModalVisible(false)}>取消</Button>,
              <Button key="preview" onClick={handlePreviewCleanup} loading={cleanupLoading}>预览删除量</Button>,
              <Button 
                  key="submit" 
                  type="primary" 
                  danger 
                  onClick={handleExecuteCleanup} 
                  loading={cleanupLoading}
                  disabled={!cleanupPreview}
              >
                  确认删除
              </Button>
          ]}
      >
          <Form form={cleanupForm} layout="vertical" initialValues={{ days: 30, min_score: 3 }}>
              <Form.Item name="days" label="保留最近多少天 (Days Retention)" tooltip="早于此时段的数据将被删除">
                  <InputNumber min={1} max={365} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="min_score" label="最低分数阈值 (Min Impact Score)" tooltip="分数低于此值的数据将被删除 (0-10)">
                  <InputNumber min={0} max={10} style={{ width: '100%' }} />
              </Form.Item>
              <Alert message="提示：高价值数据 (Score >= 7) 将始终被保留，不受此规则影响。" type="info" showIcon style={{ marginBottom: 16 }} />
              
              {cleanupPreview && (
                  <Alert 
                      message={`预计将删除 ${cleanupPreview.estimated_count} 条数据`}
                      type="warning"
                      showIcon
                  />
              )}
          </Form>
      </Modal>
    </div>
  );
};

export default DataExplorer;