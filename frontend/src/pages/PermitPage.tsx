import { useEffect, useState } from 'react';
import { Table, Tag, Button, Space, Modal, Form, Select, DatePicker, Input, message, Steps, Popconfirm } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  boardingPermitApi,
  maintenancePlanApi,
  vesselApi,
  personnelApi,
  type BoardingPermit,
  type MaintenancePlan,
  type Vessel,
  type Personnel,
  type PermitStatus,
} from '../api/client';

const statusConfig: Record<PermitStatus, { label: string; color: string; step: number }> = {
  submitted: { label: '已提交', color: 'blue', step: 0 },
  captain_confirmed: { label: '船长确认', color: 'orange', step: 1 },
  safety_cleared: { label: '安全放行', color: 'green', step: 2 },
  rejected: { label: '已驳回', color: 'red', step: -1 },
};

const PermitPage: React.FC = () => {
  const [permits, setPermits] = useState<BoardingPermit[]>([]);
  const [plans, setPlans] = useState<MaintenancePlan[]>([]);
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [personnel, setPersonnel] = useState<Personnel[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectTarget, setRejectTarget] = useState<number | null>(null);
  const [rejectForm] = Form.useForm();
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [p, pl, v, ppl] = await Promise.all([
        boardingPermitApi.list(),
        maintenancePlanApi.list(),
        vesselApi.list(),
        personnelApi.list(),
      ]);
      setPermits(p);
      setPlans(pl);
      setVessels(v);
      setPersonnel(ppl);
    } catch {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = async (values: any) => {
    try {
      const personnelList = (values.personnel_ids || []).map((pid: number, idx: number) => ({
        personnel_id: pid,
        role_on_board: values.roles?.[idx] || '船员',
      }));
      await boardingPermitApi.create({
        permit_code: values.permit_code,
        maintenance_plan_id: values.maintenance_plan_id,
        vessel_id: values.vessel_id,
        boarding_date: values.boarding_date?.format('YYYY-MM-DD'),
        submitted_by: values.submitted_by,
        personnel: personnelList,
      });
      message.success('登乘许可创建成功');
      setModalOpen(false);
      form.resetFields();
      fetchData();
    } catch (e) {
      message.error((e as Error).message || '创建失败');
    }
  };

  const handleCaptainConfirm = async (id: number) => {
    const captains = personnel.filter((p) => p.role === 'captain');
    if (captains.length === 0) {
      message.error('未找到船长人员');
      return;
    }
    try {
      await boardingPermitApi.captainConfirm(id, captains[0].id!);
      message.success('船长确认成功');
      fetchData();
    } catch (e) {
      message.error((e as Error).message || '船长确认失败');
    }
  };

  const handleSafetyClear = async (id: number) => {
    const officers = personnel.filter((p) => p.role === 'safety_officer');
    if (officers.length === 0) {
      message.error('未找到安全员');
      return;
    }
    try {
      await boardingPermitApi.safetyClear(id, officers[0].id!);
      message.success('安全放行成功');
      fetchData();
    } catch (e) {
      message.error((e as Error).message || '安全放行失败');
    }
  };

  const handleReject = async (values: { rejection_reason: string }) => {
    if (!rejectTarget) return;
    try {
      await boardingPermitApi.reject(rejectTarget, values.rejection_reason);
      message.success('已驳回');
      setRejectModalOpen(false);
      setRejectTarget(null);
      rejectForm.resetFields();
      fetchData();
    } catch (e) {
      message.error((e as Error).message || '驳回失败');
    }
  };

  const columns = [
    { title: '许可编号', dataIndex: 'permit_code', key: 'permit_code' },
    {
      title: '运维计划',
      dataIndex: 'maintenance_plan_id',
      key: 'maintenance_plan_id',
      render: (id: number) => plans.find((p) => p.id === id)?.title || id,
    },
    {
      title: '船舶',
      dataIndex: 'vessel_id',
      key: 'vessel_id',
      render: (id: number) => vessels.find((v) => v.id === id)?.name || id,
    },
    { title: '登乘日期', dataIndex: 'boarding_date', key: 'boarding_date' },
    { title: '提交人', dataIndex: 'submitted_by', key: 'submitted_by' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: PermitStatus) => {
        const cfg = statusConfig[status];
        return cfg ? <Tag color={cfg.color}>{cfg.label}</Tag> : status;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: BoardingPermit) => (
        <Space>
          {record.status === 'submitted' && (
            <>
              <Button size="small" type="primary" onClick={() => handleCaptainConfirm(record.id!)}>
                船长确认
              </Button>
              <Button size="small" danger onClick={() => { setRejectTarget(record.id!); setRejectModalOpen(true); }}>
                驳回
              </Button>
            </>
          )}
          {record.status === 'captain_confirmed' && (
            <>
              <Button size="small" type="primary" style={{ background: '#52c41a', borderColor: '#52c41a' }} onClick={() => handleSafetyClear(record.id!)}>
                安全放行
              </Button>
              <Button size="small" danger onClick={() => { setRejectTarget(record.id!); setRejectModalOpen(true); }}>
                驳回
              </Button>
            </>
          )}
          {record.status === 'safety_cleared' && <Tag color="green">已放行</Tag>}
          {record.status === 'rejected' && <Tag color="red">已驳回</Tag>}
        </Space>
      ),
    },
  ];

  const expandedRowRender = (record: BoardingPermit) => {
    const currentStep = statusConfig[record.status as PermitStatus]?.step ?? -1;
    return (
      <div style={{ padding: '8px 16px' }}>
        <Steps
          size="small"
          current={currentStep}
          items={[
            { title: '已提交' },
            { title: '船长确认' },
            { title: '安全放行' },
          ]}
        />
        {record.personnel && record.personnel.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <strong>登乘人员：</strong>
            {record.personnel.map((p, idx) => {
              const person = personnel.find((pp) => pp.id === p.personnel_id);
              return (
                <Tag key={idx} style={{ marginBottom: 4 }}>
                  {person?.name || p.personnel_id} - {p.role_on_board}
                </Tag>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新建登乘许可
        </Button>
      </div>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={permits}
        loading={loading}
        pagination={{ pageSize: 10 }}
        expandable={{ expandedRowRender }}
      />

      <Modal
        title="新建登乘许可"
        open={modalOpen}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
        onOk={() => form.submit()}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="permit_code" label="许可编号" rules={[{ required: true, message: '请输入许可编号' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="maintenance_plan_id" label="运维计划" rules={[{ required: true, message: '请选择运维计划' }]}>
            <Select>
              {plans.map((p) => (
                <Select.Option key={p.id} value={p.id}>{p.plan_code} - {p.title}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="vessel_id" label="船舶" rules={[{ required: true, message: '请选择船舶' }]}>
            <Select>
              {vessels.map((v) => (
                <Select.Option key={v.id} value={v.id}>{v.name} ({v.code})</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="boarding_date" label="登乘日期" rules={[{ required: true, message: '请选择登乘日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="submitted_by" label="提交人" rules={[{ required: true, message: '请输入提交人' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="personnel_ids" label="登乘人员" rules={[{ required: true, message: '请选择登乘人员' }]}>
            <Select mode="multiple" optionFilterProp="children">
              {personnel.map((p) => (
                <Select.Option key={p.id} value={p.id}>{p.name} ({p.role})</Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="驳回登乘许可"
        open={rejectModalOpen}
        onCancel={() => { setRejectModalOpen(false); setRejectTarget(null); rejectForm.resetFields(); }}
        onOk={() => rejectForm.submit()}
        destroyOnClose
      >
        <Form form={rejectForm} layout="vertical" onFinish={handleReject}>
          <Form.Item name="rejection_reason" label="驳回原因" rules={[{ required: true, message: '请输入驳回原因' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default PermitPage;
