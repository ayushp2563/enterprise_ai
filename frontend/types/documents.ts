export interface Document {
    id: number;
    public_id: string;
    title: string;
    file_type: string;
    file_size: number;
    category: string | null;
    metadata: Record<string, unknown>;
    original_filename: string;
    media_type: string;
    ingestion_status: 'pending' | 'processing' | 'completed' | 'failed';
    ingestion_error?: string | null;
    created_at: string;
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
    conversation_id?: string;
}

export interface QueryResponse {
    answer: string;
    conversation_id: string;
    message_id: string;
    sources: Array<{
        citation_id: number;
        chunk_id: number;
        document_id: number;
        title: string;
        excerpt: string;
        page_number?: number | null;
        chunk_index: number;
        similarity: number;
        category?: string;
    }>;
    confidence_score: number;
    should_escalate: boolean;
    escalation_reason?: string;
    hr_contact?: Record<string, string>;
    query_time: number;
    model_used: string;
}

export interface QueryHistory {
    id: number;
    company_id: number;
    user_id: number;
    question: string;
    answer: string;
    sources: Record<string, unknown>;
    query_time: number;
    created_at: string;
}
