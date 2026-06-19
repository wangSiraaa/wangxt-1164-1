import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  ScheduleOutlined,
  CarOutlined,
  SafetyCertificateOutlined,
  AuditOutlined,
} from '@ant-design/icons';

const { Sider, Content, Header } = Layout;

const menuItems = [
  { key: '/plans', icon: <ScheduleOutlined />, label: '运维计划管理' },
  { key: '/vessels', icon: <CarOutlined />, label: '船舶与海况' },
  { key: '/certificates', icon: <SafetyCertificateOutlined />, label: '人员证书管理' },
  { key: '/permits', icon: <AuditOutlined />, label: '登乘放行' },
];

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div style={{ height: 32, margin: 16, color: '#fff', textAlign: 'center', fontSize: collapsed ? 14 : 16, fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden' }}>
          {collapsed ? '风电' : '海上风电登乘许可'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', fontSize: 18, fontWeight: 600, borderBottom: '1px solid #f0f0f0' }}>
          海上风电登乘许可系统
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
