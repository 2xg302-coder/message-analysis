import React from 'react';
import { Card, Space, Input, Select, Radio, Button, Tooltip, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

const { Option } = Select;
const { Text } = Typography;

const FilterBar = ({ filters, onFilterChange, viewMode, onViewModeChange, onRefresh, loading }) => {
  
  const handleTypeChange = (e) => {
    onFilterChange({ ...filters, type: e.target.value });
  };

  const handleImpactChange = (value) => {
    onFilterChange({ ...filters, min_impact: value });
  };

  const handleSentimentChange = (value) => {
    onFilterChange({ ...filters, sentiment: value });
  };

  const handleSearch = (value) => {
    onFilterChange({ ...filters, keyword: value });
  };

  return (
    <Card 
      size="small" 
      styles={{ body: { padding: '12px 24px' } }}
      style={{ marginBottom: 16 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <Space size="middle" wrap>
          {/* 类型筛选 */}
          <Radio.Group 
            value={filters.type || 'all'} 
            onChange={handleTypeChange}
            buttonStyle="solid"
          >
            <Radio.Button value="all">全部</Radio.Button>
            <Radio.Button value="flash">快讯</Radio.Button>
            <Radio.Button value="article">深度</Radio.Button>
          </Radio.Group>

          {/* 重要程度 */}
          <Select 
            placeholder="重要程度" 
            style={{ width: 140 }}
            value={filters.min_impact}
            onChange={handleImpactChange}
            allowClear
            options={[
              { value: 0, label: '全部' },
              { value: 4, label: '🔥 重要 (≥4)' },
              { value: 6, label: '⭐⭐ 高价值 (≥6)' },
              { value: 8, label: '💎 核心 (≥8)' },
            ]}
          />

          {/* 情感倾向 */}
          <Select 
            placeholder="情感倾向" 
            style={{ width: 120 }}
            value={filters.sentiment}
            onChange={handleSentimentChange}
            allowClear
            options={[
              { value: 'all', label: '全部' },
              { value: 'positive', label: <Text type="success">利好</Text> },
              { value: 'negative', label: <Text type="danger">利空</Text> },
              { value: 'neutral', label: <Text type="warning">中性</Text> },
            ]}
          />
        </Space>

        <Space size="middle">
          {/* 视图模式切换 */}
          <Radio.Group 
            value={viewMode} 
            onChange={(e) => onViewModeChange(e.target.value)} 
            buttonStyle="solid"
          >
            <Radio.Button value="list">快讯</Radio.Button>
            <Radio.Button value="card">深度</Radio.Button>
          </Radio.Group>

          {/* 搜索框 */}
          <Input.Search
            placeholder="搜索..."
            onSearch={handleSearch}
            style={{ width: 200 }}
            allowClear
          />
          
          {/* 刷新按钮 */}
          <Tooltip title="刷新列表">
            <Button 
              icon={<ReloadOutlined spin={loading} />} 
              onClick={onRefresh} 
            />
          </Tooltip>
        </Space>
      </div>
    </Card>
  );
};

export default FilterBar;
