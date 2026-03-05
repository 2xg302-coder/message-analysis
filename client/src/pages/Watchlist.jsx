import React, { useState, useEffect } from 'react';
import { Typography, List, Input, Button, Card, Tag, Space, message, Spin } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { updateWatchlist, getWatchlist } from '../services/api';

const { Title } = Typography;

const Watchlist = () => {
  const [items, setItems] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      const res = await getWatchlist();
      if (res.data && res.data.success) {
        setItems(res.data.data);
      }
    } catch (err) {
      console.error(err);
      message.error('获取关注列表失败');
    } finally {
      setLoading(false);
    }
  };

  const syncUpdate = async (newItems) => {
      try {
          await updateWatchlist({ keywords: newItems });
          message.success('配置已保存');
      } catch (e) {
          message.error('保存失败');
      }
  };

  const handleAdd = () => {
    if (inputValue && !items.includes(inputValue)) {
      const newItems = [...items, inputValue];
      setItems(newItems);
      setInputValue('');
      syncUpdate(newItems);
    }
  };

  const handleClose = (removedTag) => {
    const newTags = items.filter((tag) => tag !== removedTag);
    setItems(newTags);
    syncUpdate(newTags);
  };

  return (
    <div>
      <Title level={2}>关注配置</Title>
      <Card title="关注关键词">
        <Spin spinning={loading}>
            <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ marginBottom: 16 }}>
                    {items.map((tag) => (
                    <Tag
                        key={tag}
                        closable
                        onClose={(e) => {
                            e.preventDefault();
                            handleClose(tag);
                        }}
                        color="geekblue"
                    >
                        {tag}
                    </Tag>
                    ))}
                    {items.length === 0 && !loading && <span style={{color: '#999'}}>暂无关注词</span>}
                </div>
                <Space.Compact style={{ width: '100%' }}>
                    <Input 
                        value={inputValue} 
                        onChange={(e) => setInputValue(e.target.value)} 
                        placeholder="输入关键词，按回车添加" 
                        onPressEnter={handleAdd}
                    />
                    <Button type="primary" onClick={handleAdd} icon={<PlusOutlined />}>添加</Button>
                </Space.Compact>
            </Space>
        </Spin>
      </Card>
    </div>
  );
};

export default Watchlist;
