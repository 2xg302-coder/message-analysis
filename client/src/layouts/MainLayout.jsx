import React from 'react';
import { Layout, Menu, theme } from 'antd';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import {
  DesktopOutlined,
  PieChartOutlined,
  SettingOutlined,
} from '@ant-design/icons';

const { Header, Content, Footer, Sider } = Layout;

const items = [
  { key: '/', icon: <DesktopOutlined />, label: '新闻流' },
  { key: '/trends', icon: <PieChartOutlined />, label: '趋势分析' },
  { key: '/watchlist', icon: <SettingOutlined />, label: '关注配置' },
];

const MainLayout = () => {
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible>
        <div style={{ height: 32, margin: 16, background: 'rgba(255, 255, 255, 0.2)', textAlign: 'center', color: 'white', lineHeight: '32px' }}>
           MA Dashboard
        </div>
        <Menu
          theme="dark"
          defaultSelectedKeys={['/']}
          selectedKeys={[location.pathname]}
          mode="inline"
          items={items}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: 0, background: colorBgContainer }} />
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
