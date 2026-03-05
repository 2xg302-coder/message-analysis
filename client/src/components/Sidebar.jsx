import React from 'react';
import { Card, Form, Radio, Select, Button, Divider, Space, Typography, Tag, Checkbox, AutoComplete } from 'antd';
import { FilterOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const Sidebar = ({ onFilterChange, loading }) => {
  const [form] = Form.useForm();

  const handleFinish = (values) => {
    onFilterChange(values);
  };

  return (
    <Card 
      title={<Space><FilterOutlined /> <span>筛选条件</span></Space>}
      size="small"
      style={{ height: '100%', overflowY: 'auto' }}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={{
          type: 'all',
          sentiment: 'all',
          importance: []
        }}
      >
        <Form.Item name="type" label="内容类型">
          <Radio.Group buttonStyle="solid" style={{ width: '100%' }}>
            <Radio.Button value="all" style={{ width: '33%', textAlign: 'center' }}>全部</Radio.Button>
            <Radio.Button value="flash" style={{ width: '33%', textAlign: 'center' }}>快讯</Radio.Button>
            <Radio.Button value="article" style={{ width: '33%', textAlign: 'center' }}>深度</Radio.Button>
          </Radio.Group>
        </Form.Item>

        <Divider style={{ margin: '12px 0' }} />

        <Form.Item name="importance" label="重要程度 (最低)">
           <Checkbox.Group style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
             <Checkbox value={8}>
               <Space>
                 <Text type="danger">⭐⭐⭐⭐⭐</Text>
                 <Tag color="red">极高</Tag>
               </Space>
             </Checkbox>
             <Checkbox value={6}>
               <Space>
                 <Text type="warning">⭐⭐⭐⭐</Text>
                 <Tag color="orange">高</Tag>
               </Space>
             </Checkbox>
             <Checkbox value={4}>
               <Space>
                 <Text type="secondary">⭐⭐⭐</Text>
                 <Tag color="blue">中</Tag>
               </Space>
             </Checkbox>
           </Checkbox.Group>
        </Form.Item>

        <Divider style={{ margin: '12px 0' }} />

        <Form.Item name="sentiment" label="情感倾向">
          <Radio.Group style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <Radio value="all">全部</Radio>
            <Radio value="positive">
              <Space>
                <span style={{ color: '#52c41a' }}>●</span> 利好
              </Space>
            </Radio>
            <Radio value="negative">
              <Space>
                <span style={{ color: '#ff4d4f' }}>●</span> 利空
              </Space>
            </Radio>
            <Radio value="neutral">
              <Space>
                <span style={{ color: '#faad14' }}>●</span> 中性
              </Space>
            </Radio>
          </Radio.Group>
        </Form.Item>
        
        <Divider style={{ margin: '12px 0' }} />

        <Form.Item name="entity" label="关联实体/股票">
          <AutoComplete
            placeholder="输入代码或名称"
            options={[]} // 这里可以后续接入搜索 API
            filterOption={(inputValue, option) =>
              option.value.toUpperCase().indexOf(inputValue.toUpperCase()) !== -1
            }
          />
        </Form.Item>
        
        <Form.Item style={{ marginTop: 24 }}>
          <Button type="primary" htmlType="submit" block loading={loading} icon={<FilterOutlined />}>
            应用筛选
          </Button>
          <Button 
            style={{ marginTop: 8 }} 
            block 
            onClick={() => {
              form.resetFields();
              onFilterChange({});
            }}
          >
            重置
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default Sidebar;
