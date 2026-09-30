/**
 * Funções de autenticação e gerenciamento de usuário
 */

import { apiGet, apiPost, apiPut, apiDelete, API_BASE_URL } from './api'

export interface SignupData {
  fullName: string
  email: string
  password: string
  code: string
  birthDate: string
  taxID: string
  zipCode: string
  phone?: string
  affiliateCode?: string
}

export interface LoginData {
  email: string
  password: string
}

export interface VerifyCodeData {
  email: string
  code: string
  trustDevice?: boolean
}

export interface AuthResponse {
  success: boolean
  message?: string
  token?: string
  user?: User
  deviceTrusted?: boolean
}

export interface User {
  _id: string
  fullName: string
  email: string
  emailVerified: boolean
  birthDate?: string
  phone?: string
  avatar?: string
  createdAt: string
  updatedAt: string
  admin?: boolean
  transferSecurityEnabled?: boolean
  taxID?: string
  balance?: number
}

/**
 * Solicitar código de verificação para cadastro
 */
export async function requestSignupCode(
  email: string,
  password?: string
): Promise<{ success: boolean; message: string }> {
  return apiPost('/v1/auth/signup/request-code', { email, password })
}

/**
 * Cadastrar novo usuário
 */
export async function signup(data: SignupData): Promise<AuthResponse> {
  const response = await apiPost<AuthResponse>('/v1/auth/signup/verify-code', data)
  if (response.success && response.token && typeof window !== 'undefined') {
    localStorage.setItem('token', response.token)
  }
  return response
}

/**
 * Solicitar código de verificação para login
 */
export async function requestLoginCode(data: LoginData): Promise<{
  success: boolean
  message: string
  trustedDevice?: boolean
  token?: string
  user?: User
  requiresCode?: boolean
}> {
  const response = await apiPost<any>('/v1/auth/login/request-code', data)
  if (response.trustedDevice && response.token && typeof window !== 'undefined') {
    localStorage.setItem('token', response.token)
  }
  return response
}

/**
 * Verificar código e fazer login
 */
export async function verifyCode(data: VerifyCodeData): Promise<AuthResponse> {
  const response = await apiPost<AuthResponse>('/v1/auth/login/verify-code', data)
  if (response.success && response.token && typeof window !== 'undefined') {
    localStorage.setItem('token', response.token)
  }
  return response
}

/**
 * Obter informações do usuário autenticado
 */
export async function getMe(): Promise<{ success: boolean; user: User }> {
  return apiGet('/v1/auth/me')
}

/**
 * Fazer logout
 */
export async function logout(): Promise<{ success: boolean; message: string }> {
  const response = await apiPost<{ success: boolean; message: string }>('/v1/auth/logout')
  if (typeof window !== 'undefined') {
    localStorage.removeItem('token')
  }
  return response
}

/**
 * Verificar se está autenticado
 */
export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false
  return !!localStorage.getItem('token')
}

/**
 * Obter token do localStorage
 */
export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('token')
}

/**
 * Solicitar código para alterar email
 * @deprecated O backend unificou alterações de perfil em PUT /v1/user/update
 */
export async function requestEmailChangeCode(
  newEmail: string
): Promise<{ success: boolean; message: string }> {
  return apiPost('/v1/profile/email/request-code', { newEmail })
}

/**
 * Alterar email do usuário via PUT /v1/user/update
 */
export async function changeEmail(
  newEmail: string,
  code?: string
): Promise<{ success: boolean; message: string; user: User }> {
  return apiPut('/v1/user/update', { email: newEmail, ...(code ? { code } : {}) })
}

/**
 * Alterar telefone do usuário via PUT /v1/user/update
 */
export async function changePhone(
  phone: string
): Promise<{ success: boolean; message: string; user: User }> {
  return apiPut('/v1/user/update', { phone })
}

/**
 * Alterar nome do usuário via PUT /v1/user/update
 */
export async function changeName(
  fullName: string
): Promise<{ success: boolean; message: string; user: User }> {
  return apiPut('/v1/user/update', { name: fullName })
}

/**
 * Alterar avatar do usuário
 * Usa o proxy interno do Next.js para não expor a URL do backend nem a chave secreta
 */
export async function changeAvatar(
  file: File
): Promise<{ success: boolean; message: string; user: User }> {
  const formData = new FormData()
  formData.append('avatar', file)

  // Usa o proxy em vez de apontar direto para o backend
  const url = `${API_BASE_URL}/v1/profile/avatar`

  const headers: Record<string, string> = {}

  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(url, {
    method: 'PUT',
    headers,
    body: formData,
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.error || data.message || 'Erro ao alterar avatar')
  }

  return data
}

/**
 * Solicitar código para alterar senha
 */
export async function requestPasswordChangeCode(
  oldPassword?: string,
  forgotPassword?: boolean
): Promise<{ success: boolean; message: string }> {
  return apiPost('/v1/profile/password/request-code', { oldPassword, forgotPassword })
}

/**
 * Alterar senha do usuário
 */
export async function changePassword(
  newPassword: string,
  code: string
): Promise<{ success: boolean; message: string; user: User }> {
  return apiPut('/v1/profile/password/verify-code', { newPassword, code })
}

/**
 * Solicitar código para recuperar senha
 */
export async function requestForgotPasswordCode(
  email: string
): Promise<{ success: boolean; message: string }> {
  return apiPost('/v1/auth/forgot-password/request-code', { email })
}

/**
 * Redefinir senha após esquecimento
 */
export async function resetPassword(
  email: string,
  code: string,
  newPassword: string
): Promise<AuthResponse> {
  const response = await apiPost<AuthResponse>('/v1/auth/forgot-password/verify-code', {
    email,
    code,
    newPassword,
  })
  if (response.success && response.token && typeof window !== 'undefined') {
    localStorage.setItem('token', response.token)
  }
  return response
}

/**
 * Interface para dispositivo confiável
 */
export interface TrustedDevice {
  id: string
  deviceName: string
  userAgent: string
  ip: string
  lastUsedAt: string
  createdAt: string
}

/**
 * Listar dispositivos confiáveis
 */
export async function getTrustedDevices(): Promise<{
  success: boolean
  data: TrustedDevice[]
}> {
  return apiGet('/v1/user/trusted-devices')
}

/**
 * Remover dispositivo confiável
 */
export async function removeTrustedDevice(
  deviceId: string
): Promise<{ success: boolean; message: string }> {
  return apiDelete(`/v1/user/trusted-devices/${deviceId}`)
}

/**
 * Remover todos os dispositivos confiáveis
 */
export async function removeAllTrustedDevices(): Promise<{
  success: boolean
  message: string
}> {
  return apiDelete('/v1/user/trusted-devices')
}

/**
 * Interface para sessão ativa
 */
export interface Session {
  id: string
  deviceName: string
  userAgent: string
  ip: string
  lastActivity: string
  createdAt: string
  expiresAt: string
  isCurrent: boolean
}

/**
 * Listar sessões ativas
 */
export async function getSessions(): Promise<{ success: boolean; data: Session[] }> {
  return apiGet('/v1/user/sessions')
}

/**
 * Revogar sessão específica
 */
export async function revokeSession(
  sessionId: string
): Promise<{ success: boolean; message: string }> {
  return apiDelete(`/v1/user/sessions/${sessionId}`)
}

/**
 * Revogar todas as sessões (exceto a atual)
 */
export async function revokeAllSessions(): Promise<{
  success: boolean
  message: string
  revokedCount?: number
}> {
  return apiDelete('/v1/user/sessions')
}
