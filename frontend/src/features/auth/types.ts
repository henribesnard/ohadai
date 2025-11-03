/**
 * Types pour l'authentification
 */

export interface User {
  user_id: string;
  email: string;
  name?: string;
  auth_provider?: string;
  created_at?: string;
  last_login?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
}

export interface TokenData {
  access_token: string;
  token_type: string;
  expires_at: string;
}

export interface LoginResponse {
  user: User;
  token: TokenData;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// Force reload
