import React, { useState } from 'react';
import { Typography, List, Input, Button, Card, Tag, Space, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { updateWatchlist } from '../services/api';

const { Title } = Typography;

const Watchlist = () => {
  // 初始关键词
  const [items, setItems] = useState(['半导体', '人工智能', '新能源']);
  const [inputValue, setInputValue] = useState('');

  const handleAdd = () => {
    if (inputValue && !items.includes(inputValue)) {
      const newItems = [...items, inputValue];
      setItems(newItems);
      setInputValue('');
      // 这里可以调用API保存配置
      // updateWatchlist({ keywords: newItems });
      message.success('已添加关注词');
    }
  };

  const handleClose = (removedTag) => {
    const newTags = items.filter((tag) => tag !== removedTag);
    setItems(newTags);
    // 这里可以调用API保存配置
    // updateWatchlist({ keywords: newTags });
  };

  return (
    <div>
      <Title level={2}>关注配置</Title>
      <Card title="关注关键词">
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
      </Card>
    </div>
  );
};

export default Watchlist;
