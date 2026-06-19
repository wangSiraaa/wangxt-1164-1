import { useEffect, useState } from 'react';
import { Table, Card, Tag, Descriptions, Row, Col, message } from 'antd';
import { vesselApi, seaConditionApi, type Vessel, type SeaCondition } from '../api/client';

const VesselPage: React.FC = () => {
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [selectedVessel, setSelectedVessel] = useState<Vessel | null>(null);
  const [latestCondition, setLatestCondition] = useState<SeaCondition | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    vesselApi.list().then((data) => {
      setVessels(data);
      if (data.length > 0) setSelectedVessel(data[0]);
    }).catch(() => message.error('加载船舶数据失败')).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedVessel?.id) return;
    seaConditionApi.latestByVessel(selectedVessel.id).then(setLatestCondition).catch(() => setLatestCondition(null));
  }, [selectedVessel]);

  const vesselColumns = [
    { title: '船名', dataIndex: 'name', key: 'name' },
    { title: '船舶编码', dataIndex: 'code', key: 'code' },
    { title: '载客量', dataIndex: 'capacity', key: 'capacity' },
    { title: '船舶类型', dataIndex: 'vessel_type', key: 'vessel_type' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={status === 'active' ? 'green' : 'red'}>{status === 'active' ? '在航' : '停航'}</Tag>,
    },
  ];

  return (
    <Row gutter={16}>
      <Col span={14}>
        <Card title="船舶列表">
          <Table
            rowKey="id"
            columns={vesselColumns}
            dataSource={vessels}
            loading={loading}
            pagination={{ pageSize: 10 }}
            onRow={(record) => ({
              onClick: () => setSelectedVessel(record),
              style: { cursor: 'pointer', background: selectedVessel?.id === record.id ? '#e6f7ff' : undefined },
            })}
          />
        </Card>
      </Col>
      <Col span={10}>
        <Card title={selectedVessel ? `${selectedVessel.name} - 最新海况` : '最新海况'}>
          {latestCondition ? (
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="记录时间">{latestCondition.record_time}</Descriptions.Item>
              <Descriptions.Item label="浪高 (m)">{latestCondition.wave_height}</Descriptions.Item>
              <Descriptions.Item label="风速 (m/s)">{latestCondition.wind_speed}</Descriptions.Item>
              <Descriptions.Item label="能见度 (km)">{latestCondition.visibility}</Descriptions.Item>
              <Descriptions.Item label="海况等级">{latestCondition.sea_state}</Descriptions.Item>
              <Descriptions.Item label="适航状态">
                <Tag color={latestCondition.is_navigable ? 'green' : 'red'}>
                  {latestCondition.is_navigable ? '适航' : '不适航'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="记录人">{latestCondition.recorder_name}</Descriptions.Item>
            </Descriptions>
          ) : (
            <div style={{ color: '#999', textAlign: 'center', padding: 40 }}>
              {selectedVessel ? '暂无海况数据' : '请选择船舶查看海况'}
            </div>
          )}
        </Card>
      </Col>
    </Row>
  );
};

export default VesselPage;
