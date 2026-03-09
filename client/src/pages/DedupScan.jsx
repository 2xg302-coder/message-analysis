import React, { useMemo, useState } from 'react';
import { Button, Card, Col, Form, InputNumber, Modal, Row, Space, Statistic, Table, Tag, Typography, message } from 'antd';
import { DeleteOutlined, ScanOutlined } from '@ant-design/icons';
import { deleteDedupNews, scanDedupNews } from '../services/api';

const { Title, Text } = Typography;

const DEFAULT_SCAN_PARAMS = {
  lookback_hours: 24,
  limit: 600,
  distance_threshold: 6,
  min_text_len: 20,
};

const buildDeleteCandidates = (pairs = []) => {
  const candidatesMap = new Map();

  pairs.forEach((pair) => {
    const deleteId = pair?.delete_id;
    if (!deleteId) return;

    const target = pair.left?.id === deleteId ? pair.left : pair.right;
    const source = target?.source || '-';
    const title = target?.title || '(无标题)';
    const createdAt = target?.created_at || '-';

    if (!candidatesMap.has(deleteId)) {
      candidatesMap.set(deleteId, {
        id: deleteId,
        source,
        title,
        created_at: createdAt,
        pair_count: 1,
        reasons: new Set([pair.reason || 'simhash']),
      });
      return;
    }

    const existing = candidatesMap.get(deleteId);
    existing.pair_count += 1;
    existing.reasons.add(pair.reason || 'simhash');
  });

  return Array.from(candidatesMap.values()).map((item) => ({
    ...item,
    reasons: Array.from(item.reasons),
  }));
};

const DedupScan = () => {
  const [form] = Form.useForm();
  const [scanning, setScanning] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [scanResult, setScanResult] = useState({
    total_candidates: 0,
    pairs_count: 0,
    pairs: [],
    recommended_delete_ids: [],
  });
  const [selectedDeleteIds, setSelectedDeleteIds] = useState([]);

  const deleteCandidates = useMemo(
    () => buildDeleteCandidates(scanResult?.pairs || []),
    [scanResult?.pairs]
  );

  const validateScanParams = (values) => {
    const checks = [
      ['lookback_hours', 1, 240, '回看小时需在 1~240 之间'],
      ['limit', 10, 1000, '扫描上限需在 10~1000 之间'],
      ['distance_threshold', 0, 10, '距离阈值需在 0~10 之间'],
      ['min_text_len', 5, 200, '最短文本长度需在 5~200 之间'],
    ];

    for (const [field, min, max, errorMsg] of checks) {
      const value = Number(values[field]);
      if (Number.isNaN(value) || value < min || value > max) {
        message.warning(errorMsg);
        return false;
      }
    }
    return true;
  };

  const handleScan = async () => {
    const values = form.getFieldsValue();
    if (!validateScanParams(values)) return;

    setScanning(true);
    setSelectedDeleteIds([]);

    try {
      const res = await scanDedupNews(values);
      const data = res?.data?.data || {
        total_candidates: 0,
        pairs_count: 0,
        pairs: [],
        recommended_delete_ids: [],
      };
      setScanResult(data);
      message.success(`扫描完成：发现 ${data.pairs_count || 0} 组疑似重复`);
    } catch {
      message.error('扫描失败，请稍后重试');
    } finally {
      setScanning(false);
    }
  };

  const handleSelectRecommended = () => {
    const recommended = new Set(scanResult?.recommended_delete_ids || []);
    const candidateIds = deleteCandidates.map((item) => item.id);
    const selected = candidateIds.filter((id) => recommended.has(id));
    setSelectedDeleteIds(selected);
    message.info(`已选中 ${selected.length} 条推荐删除项`);
  };

  const handleBatchDelete = async () => {
    if (!selectedDeleteIds.length) {
      message.warning('请先勾选需要删除的新闻');
      return;
    }

    Modal.confirm({
      title: '确认批量删除',
      content: `将删除 ${selectedDeleteIds.length} 条新闻，删除后不可恢复，是否继续？`,
      okText: '确认删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        setDeleting(true);
        try {
          const res = await deleteDedupNews(selectedDeleteIds);
          const deleted = res?.data?.deleted ?? 0;
          message.success(`删除完成：成功删除 ${deleted} 条`);

          const remain = deleteCandidates.filter((item) => !selectedDeleteIds.includes(item.id));
          const remainIds = new Set(remain.map((item) => item.id));
          const remainPairs = (scanResult?.pairs || []).filter((pair) => remainIds.has(pair.delete_id));

          setScanResult((prev) => ({
            ...prev,
            pairs: remainPairs,
            pairs_count: remainPairs.length,
            recommended_delete_ids: (prev?.recommended_delete_ids || []).filter((id) => remainIds.has(id)),
          }));
          setSelectedDeleteIds([]);
        } catch {
          message.error('删除失败，请稍后重试');
        } finally {
          setDeleting(false);
        }
      },
    });
  };

  const deleteColumns = [
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 120,
      render: (value) => <Tag>{value}</Tag>,
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
    },
    {
      title: '命中次数',
      dataIndex: 'pair_count',
      key: 'pair_count',
      width: 100,
      sorter: (a, b) => a.pair_count - b.pair_count,
    },
    {
      title: '命中原因',
      dataIndex: 'reasons',
      key: 'reasons',
      width: 180,
      render: (reasons) => (
        <Space size={4} wrap>
          {reasons.map((reason) => (
            <Tag key={reason} color={reason === 'containment' ? 'orange' : reason === 'ratio' ? 'green' : 'blue'}>
              {reason}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '发布时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 190,
    },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <div>
        <Title level={2} style={{ marginBottom: 0 }}>去重扫描</Title>
        <Text type="secondary">扫描跨来源疑似重复新闻，勾选后可批量删除。</Text>
      </div>

      <Card title="扫描参数">
        <Form
          form={form}
          layout="inline"
          initialValues={DEFAULT_SCAN_PARAMS}
        >
          <Form.Item name="lookback_hours" label="回看小时">
            <InputNumber min={1} max={240} precision={0} />
          </Form.Item>
          <Form.Item name="limit" label="扫描上限">
            <InputNumber min={10} max={1000} precision={0} />
          </Form.Item>
          <Form.Item name="distance_threshold" label="距离阈值">
            <InputNumber min={0} max={10} precision={0} />
          </Form.Item>
          <Form.Item name="min_text_len" label="最短文本长度">
            <InputNumber min={5} max={200} precision={0} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<ScanOutlined />} loading={scanning} onClick={handleScan}>
              开始扫描
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Row gutter={16}>
        <Col span={8}>
          <Card>
            <Statistic title="候选新闻数" value={scanResult?.total_candidates || 0} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="疑似重复对" value={scanResult?.pairs_count || 0} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="推荐删除数" value={scanResult?.recommended_delete_ids?.length || 0} />
          </Card>
        </Col>
      </Row>

      <Card
        title="建议删除项"
        extra={(
          <Space>
            <Button onClick={handleSelectRecommended}>选中推荐项</Button>
            <Button onClick={() => setSelectedDeleteIds([])}>清空勾选</Button>
            <Button
              danger
              type="primary"
              icon={<DeleteOutlined />}
              loading={deleting}
              disabled={!selectedDeleteIds.length}
              onClick={handleBatchDelete}
            >
              批量删除（{selectedDeleteIds.length}）
            </Button>
          </Space>
        )}
      >
        <Table
          rowKey="id"
          dataSource={deleteCandidates}
          columns={deleteColumns}
          pagination={{ pageSize: 10 }}
          size="small"
          rowSelection={{
            selectedRowKeys: selectedDeleteIds,
            onChange: (keys) => setSelectedDeleteIds(keys),
          }}
          locale={{ emptyText: '暂无扫描结果，请先执行扫描' }}
        />
      </Card>
    </Space>
  );
};

export default DedupScan;
