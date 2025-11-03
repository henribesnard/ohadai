/**
 * Service d'authentification
 */
import apiClient from '@/lib/api/axios';
import type { LoginRequest, RegisterRequest, LoginResponse, User } from '../types';

const TOKEN_KEY = 'access_token';
const USER_KEY = 'user_data';

export const authService = {
  /**
   * Connexion d'un utilisateur
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
    const { user, token } = response.data;

    // Stocker le token et les données utilisateur
    localStorage.setItem(TOKEN_KEY, token.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));

    return response.data;
  },

  /**
   * Inscription d'un nouvel utilisateur
   */
  async register(data: RegisterRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/register', data);
    const { user, token } = response.data;

    // Stocker le token et les données utilisateur
    localStorage.setItem(TOKEN_KEY, token.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));

    return response.data;
  },

  /**
   * Déconnexion
   */
  async logout(): Promise<void> {
    try {
      // Appeler l'endpoint de déconnexion si disponible
      await apiClient.post('/auth/logout');
    } catch (error) {
      // Ignorer les erreurs de l'API lors de la déconnexion
      console.error('Erreur lors de la déconnexion:', error);
    } finally {
      // Toujours nettoyer le localStorage
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
  },

  /**
   * Récupère l'utilisateur actuel depuis l'API
   */
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me');

    // Mettre à jour les données utilisateur dans le localStorage
    localStorage.setItem(USER_KEY, JSON.stringify(response.data));

    return response.data;
  },

  /**
   * Récupère le token stocké
   */
  getStoredToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },

  /**
   * Récupère les données utilisateur stockées
   */
  getStoredUser(): User | null {
    const userData = localStorage.getItem(USER_KEY);
    return userData ? JSON.parse(userData) : null;
  },

  /**
   * Vérifie si l'utilisateur est authentifié
   */
  isAuthenticated(): boolean {
    return !!this.getStoredToken();
  },
};
