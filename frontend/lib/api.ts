// API client for Agentic Fraud Investigation

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

export async function getAlerts(params?: {
  status?: string;
  risk_bucket?: string;
  limit?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.risk_bucket) searchParams.set('risk_bucket', params.risk_bucket);
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  
  const url = `${API_URL}/api/alerts?${searchParams}`;
  const response = await fetch(url, { cache: 'no-store' });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch alerts: ${response.statusText}`);
  }
  
  return response.json();
}

export async function getAlert(alertId: string) {
  const response = await fetch(`${API_URL}/api/alerts/${alertId}`, {
    cache: 'no-store'
  });
  
  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error(`Failed to fetch alert: ${response.statusText}`);
  }
  
  return response.json();
}

export async function startCase(params: {
  alert_id: string;
  max_hops?: number;
  cost_budget?: number;
  max_nodes?: number;
}) {
  const response = await fetch(`${API_URL}/api/case/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      alert_id: params.alert_id,
      max_hops: params.max_hops || 3,
      cost_budget: params.cost_budget || 1.0,
      max_nodes: params.max_nodes || 80
    })
  });
  
  if (!response.ok) {
    throw new Error(`Failed to start case: ${response.statusText}`);
  }
  
  return response.json();
}

export async function getCase(caseId: string) {
  const response = await fetch(`${API_URL}/api/case/${caseId}`, {
    cache: 'no-store'
  });
  
  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error(`Failed to fetch case: ${response.statusText}`);
  }
  
  return response.json();
}

export async function runCase(caseId: string) {
  const response = await fetch(`${API_URL}/api/case/${caseId}/run`, {
    method: 'POST'
  });
  
  if (!response.ok) {
    throw new Error(`Failed to run case: ${response.statusText}`);
  }
  
  return response.json();
}

export function streamCase(caseId: string): EventSource {
  return new EventSource(`${API_URL}/api/case/${caseId}/stream`);
}

export async function getWorkflowStructure() {
  const response = await fetch(`${API_URL}/api/workflow/structure`, {
    cache: 'no-store'
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch workflow structure: ${response.statusText}`);
  }
  
  return response.json();
}

export async function getManifest() {
  const response = await fetch(`${API_URL}/api/manifest`, {
    cache: 'no-store'
  });
  
  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error(`Failed to fetch manifest: ${response.statusText}`);
  }
  
  return response.json();
}
