// API Types
export interface User {
    id: number;
    company_id: number;
    email: string;
    full_name: string;
    role: 'company_admin' | 'hr_manager' | 'employee';
    is_active: boolean;
    last_login: string | null;
    created_at: string;
    updated_at: string;
}

export interface Company {
    id: number;
    name: string;
    slug: string;
    domain: string | null;
    settings: Record<string, any>;
    subscription_tier: string;
    max_employees: number;
    max_documents: number;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
    user: User;
}

export interface LoginRequest {
    email: string;
    password: string;
}

export interface RegisterCompanyRequest {
    name: string;
    slug: string;
    domain?: string;
    admin_email: string;
    admin_password: string;
    admin_full_name: string;
}

export interface InvitationAcceptRequest {
    token: string;
    password: string;
    full_name: string;
}
