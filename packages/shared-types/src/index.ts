// --- COGNITIVE WORKFLOW DEFINITIONS ---
export interface WorkflowStep {
  id: string;
  name: string;
  agentRole: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  dependencies: string[];
  commandPrompt: string;
  resultPayloadPath?: string;
  completedAt?: string;
}

export interface OrchestrationWorkflow {
  id: string;
  title: string;
  creatorId: string;
  status: 'queued' | 'active' | 'success' | 'failed' | 'paused';
  steps: WorkflowStep[];
  metaData: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

// --- SYSTEM TELEMETRY AND METRICS ---
export interface EngineMetrics {
  cpuLoad: number;
  memoryUsageBytes: number;
  activeWorkers: number;
  tasksCompleted: number;
  queueDepth: number;
  telemetrySpanCount: number;
}

// --- MEMORY AND SECURITY POLICIES ---
export interface SecurityContext {
  userId: string;
  roles: ('admin' | 'operator' | 'auditor')[];
  clearanceLevel: number;
  redactionPolicy: 'strict' | 'standard' | 'none';
}

export interface EpisodicMemoryNode {
  key: string;
  sessionToken: string;
  payloadJson: string;
  expirationSeconds: number;
}

export interface SemanticMemoryRecord {
  id: string;
  vector: number[];
  payloadText: string;
  metadata: {
    originTask: string;
    timestamp: string;
    tokenCount: number;
  };
}

// --- PHASE 2: AGENT COGNITIVE TYPES ---

export type AgentTier = 'ORCHESTRATOR' | 'SPECIALIST' | 'WORKER';

export interface ToolCall {
  tool_name: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  error?: string;
  duration_ms?: number;
  timestamp: string;
}

export interface Plan {
  steps: string[];
  rationale: string;
  estimated_steps: number;
}

export interface ActionResult {
  success: boolean;
  output: string;
  tool_calls_made: ToolCall[];
  duration_ms: number;
  step_index: number;
}

export type ReflectionRecommendation =
  | 'continue'
  | 'retry'
  | 'escalate_hitl'
  | 'abort';

export interface Reflection {
  passed: boolean;
  tool_success: boolean;
  schema_valid: boolean;
  logic_sound: boolean;
  issues: string[];
  recommendation: ReflectionRecommendation;
  retry_count: number;
  rationale: string;
}

export type AgentEventType =
  | 'agent.think.start'
  | 'agent.think.complete'
  | 'agent.act.start'
  | 'agent.act.complete'
  | 'agent.reflect.start'
  | 'agent.reflect.complete'
  | 'agent.memory.retrieve'
  | 'agent.memory.store'
  | 'agent.hitl.requested'
  | 'agent.run.completed'
  | 'agent.run.failed';

export interface AgentEvent {
  event_type: AgentEventType;
  run_id: string;
  agent_name: string;
  agent_tier: AgentTier;
  timestamp: string;
  duration_ms?: number;
  payload: Record<string, unknown>;
  trace_id?: string;
  span_id?: string;
}

export interface SubTask {
  id: string;
  parent_run_id: string;
  specialist_type: string;
  task_description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: string;
  created_at: string;
}

export interface OrchestratorResult {
  run_id: string;
  final_output: string;
  subtasks_completed: number;
  subtasks_failed: number;
  total_duration_ms: number;
  tool_calls_total: number;
}
