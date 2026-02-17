export interface HREscalation {
    id: number;
    company_id: number;
    user_id: number;
    question: string;
    reason: string;
    status: 'pending' | 'contacted' | 'resolved';
    query_log_id: number | null;
    hr_response: string | null;
    resolved_by: number | null;
    resolved_at: string | null;
    created_at: string;
}

export interface HRAnalytics {
    total_queries: number;
    total_escalations: number;
    escalation_rate: number;
    avg_confidence_score: number;
    pending_escalations: number;
    resolved_escalations: number;
    top_escalation_reasons: Array<{
        reason: string;
        count: number;
    }>;
}
