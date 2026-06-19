import { useEffect, useState } from 'react';
import { Table, Tabs, Tag, Modal, Form, Input, Select, DatePicker, Button, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { certificateApi, personnelApi, type PersonnelCertificate, type Personnel } from '../api/client';

const CertificatePage: React.FC = () => {
  const [certificates, setCertificates] = useState<PersonnelCertificate[]>([]);
  const [expiredCerts, setExpiredCerts] = useState<PersonnelCertificate[]>([]);
  const [personnel, setPersonnel] = useState<Personnel[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchCertificates = async () => {
    setLoading(true);
    try {
      const [certs, expired, ppl] = await Promise.all([
        certificateApi.list(),
        certificateApi.expired(),
        personnelApi.list(),
      ]);
      setCertificates(certs);
      setExpiredCerts(expired);
      setPersonnel(ppl);
    } catch {
      message.error('加载证书数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCertificates();
  }, []);

  const handleCreate = async (values: any) => {
    try {
      await certificateApi.create({
        ...values,
        issue_date: values.issue_date?.format('YYYY-MM-DD'),
        expiry_date: values.expiry_date?.format('YYYY-MM-DD'),
      });
      message.success('证书创建成功');
      setModalOpen(false);
      form.resetFields();
      fetchCertificates();
    } catch {
      message.error('证书创建失败');
    }
  };

  const getExpiryStatus = (expiryDate: string, isValid: boolean) => {
    if (!isValid) return { label: '已失效', color: 'red' };
    const daysLeft = dayjs(expiryDate).diff(dayjs(), 'day');
    if (daysLeft < 0) return { label: '已过期', color: 'red' };
    if (daysLeft <= 30) return { label: `即将过期(${daysLeft}天)`, color: 'orange' };
    return { label: '有效', color: 'green' };
  };

  const columns = [
    {
      title: '人员',
      dataIndex: 'personnel_id',
      key: 'personnel_id',
      render: (id: number) => personnel.find((p) => p.id === id)?.name || id,
    },
    { title: '证书类型', dataIndex: 'cert_type', key: 'cert_type' },
    { title: '证书编号', dataIndex: 'cert_number', key: 'cert_number' },
    { title: '签发日期', dataIndex: 'issue_date', key: 'issue_date' },
    { title: '到期日期', dataIndex: 'expiry_date', key: 'expiry_date' },
    {
      title: '状态',
      key: 'status',
      render: (_: unknown, record: PersonnelCertificate) => {
        const s = getExpiryStatus(record.expiry_date, record.is_valid);
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
  ];

  const tabItems = [
    {
      key: 'all',
      label: '全部证书',
      children: (
        <>
          <div style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
              新增证书
            </Button>
          </div>
          <Table rowKey="id" columns={columns} dataSource={certificates} loading={loading} pagination={{ pageSize: 10 }} />
        </>
      ),
    },
    {
      key: 'expired',
      label: (
        <span>
          已过期/失效 <Tag color="red">{expiredCerts.length}</Tag>
        </span>
      ),
      children: <Table rowKey="id" columns={columns} dataSource={expiredCerts} loading={loading} pagination={{ pageSize: 10 }} />,
    },
  ];

  return (
    <>
      <Tabs items={tabItems} />
      <Modal
        title="新增证书"
        open={modalOpen}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="personnel_id" label="人员" rules={[{ required: true, message: '请选择人员' }]}>
            <Select showSearch optionFilterProp="children">
              {personnel.map((p) => (
                <Select.Option key={p.id} value={p.id}>{p.name} ({p.employee_id})</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="cert_type" label="证书类型" rules={[{ required: true, message: '请输入证书类型' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="cert_number" label="证书编号" rules={[{ required: true, message: '请输入证书编号' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="issue_date" label="签发日期" rules={[{ required: true, message: '请选择签发日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="expiry_date" label="到期日期" rules={[{ required: true, message: '请选择到期日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default CertificatePage;
