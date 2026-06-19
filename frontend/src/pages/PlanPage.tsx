import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, DatePicker, Tag, Space, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { maintenancePlanApi, workPositionApi, type MaintenancePlan, type WorkPosition, type PlanStatus } from '../api/client';

const statusMap: Record<PlanStatus, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'default' },
  submitted: { label: '已提交', color: 'blue' },
  approved: { label: '已审批', color: 'orange' },
  completed: { label: '已完成', color: 'green' },
};

const riskMap: Record<string, { label: string; color: string }> = {
  low: { label: '低', color: 'green' },
  medium: { label: '中', color: 'orange' },
  high: { label: '高', color: 'red' },
};

const statusFlow: Record<PlanStatus, PlanStatus | null> = {
  draft: 'submitted',
  submitted: 'approved',
  approved: 'completed',
  completed: null,
};

const statusButtonLabel: Record<PlanStatus, string> = {
  draft: '提交',
  submitted: '审批通过',
  approved: '标记完成',
  completed: '',
};

const PlanPage: React.FC = () => {
  const [plans, setPlans] = useState<MaintenancePlan[]>([]);
  const [positions, setPositions] = useState<WorkPosition[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [planData, posData] = await Promise.all([
        maintenancePlanApi.list(),
        workPositionApi.list(),
      ]);
      setPlans(planData);
      setPositions(posData);
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
      await maintenancePlanApi.create({
        ...values,
        plan_date: values.plan_date?.format('YYYY-MM-DD'),
        status: 'draft',
      });
      message.success('创建成功');
      setModalOpen(false);
      form.resetFields();
      fetchData();
    } catch {
      message.error('创建失败');
    }
  };

  const handleStatusChange = async (id: number, currentStatus: PlanStatus) => {
    const next = statusFlow[currentStatus];
    if (!next) return;
    try {
      await maintenancePlanApi.updateStatus(id, next);
      message.success('状态更新成功');
      fetchData();
    } catch {
      message.error('状态更新失败');
    }
  };

  const columns = [
    { title: '计划编号', dataIndex: 'plan_code', key: 'plan_code' },
    { title: '计划名称', dataIndex: 'title', key: 'title' },
    {
      title: '作业机位',
      dataIndex: 'work_position_id',
      key: 'work_position_id',
      render: (id: number) => positions.find((p) => p.id === id)?.name || id,
    },
    { title: '计划日期', dataIndex: 'plan_date', key: 'plan_date' },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      render: (level: string) => {
        const r = riskMap[level];
        return r ? <Tag color={r.color}>{r.label}</Tag> : level;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: PlanStatus) => {
        const s = statusMap[status];
        return s ? <Tag color={s.color}>{s.label}</Tag> : status;
      },
    },
    { title: '创建人', dataIndex: 'created_by', key: 'created_by' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: MaintenancePlan) => {
        const next = statusFlow[record.status];
        if (!next) return null;
        return (
          <Button size="small" type="primary" onClick={() => handleStatusChange(record.id!, record.status)}>
            {statusButtonLabel[record.status]}
          </Button>
        );
      },
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新建计划
        </Button>
      </div>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={plans}
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
      <Modal
        title="新建运维计划"
        open={modalOpen}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="plan_code" label="计划编号" rules={[{ required: true, message: '请输入计划编号' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="title" label="计划名称" rules={[{ required: true, message: '请输入计划名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="work_position_id" label="作业机位" rules={[{ required: true, message: '请选择作业机位' }]}>
            <Select>
              {positions.filter((p) => p.is_active).map((p) => (
                <Select.Option key={p.id} value={p.id}>{p.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="plan_date" label="计划日期" rules={[{ required: true, message: '请选择计划日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="risk_level" label="风险等级" rules={[{ required: true, message: '请选择风险等级' }]}>
            <Select>
              <Select.Option value="low">低</Select.Option>
              <Select.Option value="medium">中</Select.Option>
              <Select.Option value="high">高</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="created_by" label="创建人" rules={[{ required: true, message: '请输入创建人' }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default PlanPage;
