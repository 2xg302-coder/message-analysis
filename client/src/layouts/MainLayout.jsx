import React from 'react';
import { Layout, Menu, theme } from 'antd';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import {
  DesktopOutlined,
  PieChartOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import TaskStatus from '../components/TaskStatus';

const { Header, Content, Footer, Sider } = Layout;

const items = [
  {
    key: 'monitor',
    label: '市场监控',
    icon: <DesktopOutlined />,
    children: [
      { key: '/', label: '新闻流' },
      { key: '/ithome', label: 'IT之家' },
      { key: '/calendar', label: '财经日历' },
    ],
  },
  {
    key: 'analysis',
    label: '分析工具',
    icon: <PieChartOutlined />,
    children: [
      { key: '/trends', label: '趋势分析' },
      { key: '/storylines', label: '每日主线' },
      { key: '/series', label: '连续剧追踪' },
    ],
  },
  {
    key: 'management',
    label: '数据管理',
    icon: <DatabaseOutlined />,
    children: [
      { key: '/explorer', label: '数据资产' },
      { key: '/watchlist', label: '关注配置' },
    ],
  },
];

const MainLayout = () => {
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();
  const navigate = useNavigate();
  const location = useLocation();
  
  const selectedKey = location.pathname.startsWith('/series') ? '/series' : location.pathname;

  // Determine the default open key based on the current path
  const getOpenKey = (path) => {
    if (path === '/' || path === '/ithome' || path === '/calendar') return 'monitor';
    if (path === '/trends' || path === '/storylines' || path.startsWith('/series')) return 'analysis';
    if (path === '/explorer' || path === '/watchlist') return 'management';
    return 'monitor';
  };

  const [openKeys, setOpenKeys] = React.useState([getOpenKey(location.pathname)]);

  const onOpenChange = (keys) => {
    const rootSubmenuKeys = ['monitor', 'analysis', 'management'];
    const latestOpenKey = keys.find((key) => openKeys.indexOf(key) === -1);
    if (rootSubmenuKeys.indexOf(latestOpenKey) === -1) {
      setOpenKeys(keys);
    } else {
      setOpenKeys(latestOpenKey ? [latestOpenKey] : []);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible>
        <div style={{ height: 32, margin: 16, background: 'rgba(255, 255, 255, 0.2)', textAlign: 'center', color: 'white', lineHeight: '32px' }}>
           MA Dashboard
        </div>
        <Menu
          theme="dark"
          defaultSelectedKeys={['/']}
          selectedKeys={[selectedKey]}
          openKeys={openKeys}
          onOpenChange={onOpenChange}
          mode="inline"
          items={items}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: 0, background: colorBgContainer, display: 'flex', justifyContent: 'flex-end', alignItems: 'center', paddingRight: 24 }}>
          <TaskStatus />
        </Header>
        <Content style={{ margin: '0 16px' }}>
          <div
            style={{
              padding: 24,
              minHeight: 360,
              background: colorBgContainer,
              borderRadius: borderRadiusLG,
              marginTop: 16
            }}
          >
            <Outlet />
          </div>
        </Content>
        <Footer style={{ textAlign: 'center' }}>
          Message Analysis Dashboard ©{new Date().getFullYear()}
        </Footer>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
