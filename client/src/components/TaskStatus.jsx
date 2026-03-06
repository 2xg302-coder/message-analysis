import React, { useState, useEffect } from 'react';
import { Tag } from 'antd';
import { SyncOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { getAnalysisStatus } from '../services/api';

const TaskStatus = () => {
  const [task, setTask] = useState(null);

  const fetchStatus = async () => {
    try {
      const response = await getAnalysisStatus();
      if (response.data && response.data.currentTask) {
        setTask(response.data.currentTask);
      } else {
        setTask(null);
      }
    } catch (error) {
      console.error('Failed to fetch analysis status', error);
      setTask(null);
    }
  };

  useEffect(() => {
    fetchStatus();
    // 每 5 秒轮询一次
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!task) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', padding: '0 16px' }}>
             <Tag icon={<CheckCircleOutlined />} color="success">系统空闲</Tag>
        </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', padding: '0 16px' }}>
      <span style={{ marginRight: 8, fontSize: '14px', color: '#666' }}>正在处理:</span>
      <Tag icon={<SyncOutlined spin />} color="processing">
        {task.title ? (task.title.length > 20 ? task.title.substring(0, 20) + '...' : task.title) : '未知任务'}
      </Tag>
    </div>
  );
};

export default TaskStatus;
