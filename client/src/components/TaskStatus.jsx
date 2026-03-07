import React, { useState, useEffect } from 'react';
import { Tag, Tooltip, Badge } from 'antd';
import { SyncOutlined, CheckCircleOutlined, DashboardOutlined, WarningOutlined } from '@ant-design/icons';
import { getMonitorStats } from '../services/api';
import MonitorDrawer from './MonitorDrawer';

const TaskStatus = () => {
  const [stats, setStats] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const fetchStatus = async () => {
    try {
      const response = await getMonitorStats();
      if (response.data) {
        setStats(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch monitor stats', error);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Poll every 5 seconds
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleOpenDrawer = () => {
    setDrawerOpen(true);
  };

  if (!stats) {
    return (
       <div style={{ display: 'flex', alignItems: 'center', padding: '0 16px', cursor: 'pointer' }} onClick={handleOpenDrawer}>
            <Tag icon={<SyncOutlined spin />} color="default">Loading...</Tag>
       </div>
    );
  }

  const { analyzer, collection } = stats;
  const isProcessing = analyzer.processingCount > 0;
  const hasBacklog = collection.backlog > 0;
  const hasFailures = collection.failedToday > 0;

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', padding: '0 16px', cursor: 'pointer' }} onClick={handleOpenDrawer}>
        <Tooltip title="点击查看系统监控面板">
            <span style={{ display: 'flex', alignItems: 'center' }}>
                {isProcessing ? (
                    <Tag icon={<SyncOutlined spin />} color="processing">
                        处理中: {analyzer.processingCount}
                    </Tag>
                ) : (
                    <Tag icon={<CheckCircleOutlined />} color="success">
                        系统空闲
                    </Tag>
                )}
                
                {hasBacklog && (
                    <Tag icon={<DashboardOutlined />} color="warning">
                        积压: {collection.backlog}
                    </Tag>
                )}

                {hasFailures && (
                    <Tag icon={<WarningOutlined />} color="error">
                        失败: {collection.failedToday}
                    </Tag>
                )}
                
                <Badge dot={hasBacklog || hasFailures} offset={[-5, 5]}>
                    <DashboardOutlined style={{ fontSize: '18px', marginLeft: 8, color: '#1890ff' }} />
                </Badge>
            </span>
        </Tooltip>
      </div>
      
      <MonitorDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  );
};

export default TaskStatus;
