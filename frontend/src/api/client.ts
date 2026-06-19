const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    let detail = text || res.statusText;
    try {
      const json = JSON.parse(text);
      if (json.detail) {
        detail = typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail);
      }
    } catch {
    }
    throw new Error(detail);
  }
  return res.json();
}

export interface WorkPosition {
  id?: number;
  code: string;
  name: string;
  description?: string;
  risk_level: 'low' | 'medium' | 'high';
  is_active: boolean;
}

export interface Vessel {
  id?: number;
  name: string;
  code: string;
  capacity: number;
  vessel_type: string;
  status: string;
}

export interface Personnel {
  id?: number;
  name: string;
  employee_id: string;
  role: 'maintenance_lead' | 'captain' | 'safety_officer' | 'crew';
  phone: string;
}

export interface PersonnelCertificate {
  id?: number;
  personnel_id: number;
  cert_type: string;
  cert_number: string;
  issue_date: string;
  expiry_date: string;
  is_valid: boolean;
  personnel_name?: string;
}

export interface SeaCondition {
  id?: number;
  vessel_id: number;
  record_time: string;
  wave_height: number;
  wind_speed: number;
  visibility: number;
  sea_state: string;
  is_navigable: boolean;
  recorder_name: string;
}

export interface OperationWindow {
  id?: number;
  work_position_id: number;
  start_time: string;
  end_time: string;
  max_wave_height: number;
  max_wind_speed: number;
  min_visibility: number;
}

export type PlanStatus = 'draft' | 'submitted' | 'approved' | 'completed';

export interface MaintenancePlan {
  id?: number;
  plan_code: string;
  title: string;
  work_position_id: number;
  plan_date: string;
  description?: string;
  risk_level: 'low' | 'medium' | 'high';
  status: PlanStatus;
  created_by: string;
  work_position_name?: string;
}

export type PermitStatus = 'submitted' | 'captain_confirmed' | 'safety_cleared' | 'rejected';

export interface BoardingPermit {
  id?: number;
  permit_code: string;
  maintenance_plan_id: number;
  vessel_id: number;
  boarding_date: string;
  submitted_by: string;
  status?: PermitStatus;
  personnel: BoardingPermitPersonnel[];
  plan_title?: string;
  vessel_name?: string;
}

export interface BoardingPermitPersonnel {
  personnel_id: number;
  role_on_board: string;
  personnel_name?: string;
}

export const workPositionApi = {
  list: () => request<WorkPosition[]>('/work-positions/'),
  create: (data: WorkPosition) => request<WorkPosition>('/work-positions/', { method: 'POST', body: JSON.stringify(data) }),
};

export const vesselApi = {
  list: () => request<Vessel[]>('/vessels/'),
  create: (data: Vessel) => request<Vessel>('/vessels/', { method: 'POST', body: JSON.stringify(data) }),
};

export const personnelApi = {
  list: () => request<Personnel[]>('/personnel/'),
  create: (data: Personnel) => request<Personnel>('/personnel/', { method: 'POST', body: JSON.stringify(data) }),
};

export const certificateApi = {
  list: () => request<PersonnelCertificate[]>('/personnel-certificates/'),
  expired: () => request<PersonnelCertificate[]>('/personnel-certificates/expired'),
  create: (data: PersonnelCertificate) => request<PersonnelCertificate>('/personnel-certificates/', { method: 'POST', body: JSON.stringify(data) }),
};

export const seaConditionApi = {
  list: () => request<SeaCondition[]>('/sea-conditions/'),
  create: (data: SeaCondition) => request<SeaCondition>('/sea-conditions/', { method: 'POST', body: JSON.stringify(data) }),
  latestByVessel: (vesselId: number) => request<SeaCondition>(`/sea-conditions/vessel/${vesselId}/latest`),
};

export const operationWindowApi = {
  list: () => request<OperationWindow[]>('/operation-windows/'),
  create: (data: OperationWindow) => request<OperationWindow>('/operation-windows/', { method: 'POST', body: JSON.stringify(data) }),
  activeByPosition: (positionId: number) => request<OperationWindow>(`/operation-windows/position/${positionId}/active`),
};

export const maintenancePlanApi = {
  list: () => request<MaintenancePlan[]>('/maintenance-plans/'),
  create: (data: MaintenancePlan) => request<MaintenancePlan>('/maintenance-plans/', { method: 'POST', body: JSON.stringify(data) }),
  updateStatus: (id: number, status: PlanStatus) =>
    request<MaintenancePlan>(`/maintenance-plans/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
};

export const boardingPermitApi = {
  list: () => request<BoardingPermit[]>('/boarding-permits/'),
  create: (data: BoardingPermit) => request<BoardingPermit>('/boarding-permits/', { method: 'POST', body: JSON.stringify(data) }),
  captainConfirm: (id: number, captainId: number) =>
    request<BoardingPermit>(`/boarding-permits/${id}/captain-confirm`, {
      method: 'POST',
      body: JSON.stringify({ captain_id: captainId }),
    }),
  safetyClear: (id: number, safetyOfficerId: number) =>
    request<BoardingPermit>(`/boarding-permits/${id}/safety-clear`, {
      method: 'POST',
      body: JSON.stringify({ safety_officer_id: safetyOfficerId }),
    }),
  reject: (id: number, rejectionReason: string) =>
    request<BoardingPermit>(`/boarding-permits/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ rejection_reason: rejectionReason }),
    }),
};
