export type AgentType = 'security' | 'performance' | 'maintainability' | 'synthesizer'
export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low'
export type Language = 'python' | 'javascript'
export type Category = 'security' | 'performance' | 'maintainability'

export interface Issue {
    agent: AgentType
    category: Category
    issue_type: string
    severity: SeverityLevel
    file: string
    line: number
    evidence: string
    llm_reasoning: string
    suggested_fix: string
    confidence: number
    agent_agreement: AgentType[]
    cross_domain_notes: string | null
}

export interface ReviewRequest {
    code: string
    filename?: string
    language?: Language
}

export interface ReviewResponse {
    session_id: string
    language: Language
    issues: Issue[]
    total_issues: number
    summary: string
    fixed_code: string
    processing_time_ms: number
}

// SSE stream event types
export type StreamEvent =
    | { event: 'language'; language: Language }
    | { event: 'tools_done' }
    | { event: 'security_done'; issues: Issue[] }
    | { event: 'performance_done'; issues: Issue[] }
    | { event: 'maintainability_done'; issues: Issue[] }
    | { event: 'synthesis_done'; issues: Issue[]; summary: string; fixed_code: string }
    | { event: 'done' }