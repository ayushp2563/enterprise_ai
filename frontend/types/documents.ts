export interface Document {
    id: number;
    company_id: number;
    title: string;
    file_path: string;
    file_type: string;
    file_size: number;
    category: string | null;
    metadata: Record<string, any>;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    uploaded_by: number;
}

export interface DocumentUploadRequest {
    file: File;
    title: string;
    category?: string;
}

export interface QueryRequest {
    question: string;
    top_k?: number;
}

export interface QueryResponse {
    answer: string;
    sources: Array<{
        document_id: number;
        title: string;
        chunk_text: string;
        similarity: number;
        category?: string;
    }>;
    confidence_score: number;
    should_escalate: boolean;
    escalation_reason?: string;
    hr_contact?: {
        name: string;
        email: string;
    };
}

export interface QueryHistory {
    id: number;
    company_id: number;
    user_id: number;
    question: string;
    answer: string;
    sources: Record<string, any>;
    query_time: number;
    created_at: string;
}
