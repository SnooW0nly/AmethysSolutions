'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faEnvelope, faLock, faEye, faEyeSlash, faKey, faCheckCircle, faArrowRight, faSpinner, faCheck, faArrowLeft } from '@fortawesome/free-solid-svg-icons'
import { RippleButton } from '@/components/ripple-button'
import { requestLoginCode, verifyCode, isAuthenticated, requestForgotPasswordCode, resetPassword } from '@/lib/auth'
import { validatePassword } from '@/lib/passwordValidator'

export default function LoginPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [step, setStep] = useState<'login' | 'code' | 'forgot-password' | 'reset-password'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [passwordValidation, setPasswordValidation] = useState<{ valid: boolean; errors: string[] }>({ valid: true, errors: [] })
  const [trustDevice, setTrustDevice] = useState(true) // Marcado por padrão

  // Redirecionar se já estiver logado (apenas se ainda estiver na página de login)
  useEffect(() => {
    const checkAuth = () => {
      if (isAuthenticated()) {
        // Verificar se ainda estamos na página de login antes de redirecionar
        // Isso evita redirecionamentos indesejados durante o processo de login
        if (window.location.pathname === '/login') {
          window.location.href = '/dashboard'
        }
      }
    }

    // Pequeno delay para evitar verificação muito cedo
    const timeoutId = setTimeout(checkAuth, 100)

    return () => clearTimeout(timeoutId)
  }, [router])

  const handleRequestCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const response = await requestLoginCode({ email, password })

      // Se o dispositivo já é confiável, fazer login direto
      if (response.trustedDevice && response.token && response.user) {
        // Salvar token no localStorage
        if (typeof window !== 'undefined' && response.token) {
          localStorage.setItem('token', response.token)

          // Salvar usuário temporariamente para uso imediato
          // Isso garante que o usuário esteja disponível mesmo antes do useAuth carregar
          sessionStorage.setItem('temp_user', JSON.stringify(response.user))

          // Disparar evento storage para forçar atualização do useAuth
          window.dispatchEvent(new Event('storage'))
          // Disparar evento customizado também
          window.dispatchEvent(new CustomEvent('auth-change', { detail: { user: response.user, token: response.token } }))
        }

        // Delay maior para garantir que o token seja salvo e processado
        await new Promise(resolve => setTimeout(resolve, 300))

        // Forçar atualização completa da página ao redirecionar para dashboard
        window.location.href = '/dashboard'
        return
      }

      setStep('code')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao solicitar código')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const response = await verifyCode({ email, code, trustDevice })

      if (response.success && response.token && response.user) {
        // O token JÁ foi salvo pela função verifyCode
        // Agora salvar usuário temporariamente para uso imediato
        if (typeof window !== 'undefined') {
          sessionStorage.setItem('temp_user', JSON.stringify(response.user))

          // Disparar eventos para atualizar o useAuth
          window.dispatchEvent(new Event('storage'))
          window.dispatchEvent(new CustomEvent('auth-change', { detail: { user: response.user, token: response.token } }))
        }

        // Delay para garantir que tudo foi processado
        await new Promise(resolve => setTimeout(resolve, 300))

        // Forçar atualização completa da página ao redirecionar para dashboard
        window.location.href = '/dashboard'
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Código inválido ou expirado')
    } finally {
      setLoading(false)
    }
  }

  const handleRequestForgotPasswordCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await requestForgotPasswordCode(email)
      setStep('reset-password')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao solicitar código')
    } finally {
      setLoading(false)
    }
  }

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const validation = validatePassword(newPassword)
    if (!validation.valid) {
      setError(validation.errors.join(', '))
      setLoading(false)
      return
    }

    try {
      const response = await resetPassword(email, code, newPassword)
      if (response.success && response.token) {
        // Pequeno delay para garantir que o token seja salvo no localStorage antes do redirecionamento
        await new Promise(resolve => setTimeout(resolve, 50))
        // Forçar atualização completa da página ao redirecionar para dashboard
        window.location.href = '/dashboard'
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao redefinir senha')
    } finally {
      setLoading(false)
    }
  }

  const handlePasswordChange = (value: string) => {
    setNewPassword(value)
    setPasswordValidation(validatePassword(value))
  }

  return (
    <div className="min-h-[calc(100vh-120px)] sm:min-h-[calc(100vh-200px)] flex items-center justify-center p-4 sm:p-6 -mt-4 sm:-mt-8">
      <div className="w-full max-w-md">
        {/* Card */}
        <div className="p-5 sm:p-8 rounded-2xl border border-foreground/10 bg-foreground/2 backdrop-blur-sm shadow-xl">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-foreground">Bem-vindo de volta</h1>
            <p className="text-foreground/60 text-sm mt-1">Entre na sua conta para continuar</p>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm animate-in slide-in-from-top-2 fade-in-0 duration-200">
              <div className="flex items-start gap-2">
                <span className="text-red-500 mt-0.5">⚠</span>
                <span>{error}</span>
              </div>
            </div>
          )}

          {step === 'login' ? (
            <>
              {/* Email/Password Form */}
              <form onSubmit={handleRequestCode} className="space-y-4 animate-in fade-in-0 duration-300">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    E-mail
                  </label>
                  <div className="relative">
                    <FontAwesomeIcon
                      icon={faEnvelope}
                      className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50"
                    />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="seu@email.com"
                      autoComplete="email"
                      className={`w-full pl-10 pr-4 py-3 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/30 transition-all ${loading ? 'opacity-60 cursor-not-allowed' : ''
                        }`}
                      required
                      disabled={loading}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Senha
                  </label>
                  <div className="relative">
                    <FontAwesomeIcon
                      icon={faLock}
                      className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50"
                    />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      className={`w-full pl-10 pr-12 py-3 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/30 transition-all ${loading ? 'opacity-60 cursor-not-allowed' : ''
                        }`}
                      required
                      disabled={loading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground/50 hover:text-foreground transition-colors"
                    >
                      <FontAwesomeIcon icon={showPassword ? faEyeSlash : faEye} className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <button
                    type="button"
                    onClick={() => {
                      setStep('forgot-password')
                      setPassword('')
                      setError(null)
                    }}
                    className="text-primary hover:text-primary/80 font-medium transition-colors"
                  >
                    Esqueceu a senha?
                  </button>
                </div>

                <RippleButton
                  type="submit"
                  className="w-full py-3.5 bg-primary text-primary-foreground rounded-xl font-bold hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300 mt-2 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
                  disabled={loading}
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <FontAwesomeIcon icon={faSpinner} className="w-4 h-4 animate-spin" />
                      <span>Enviando código...</span>
                    </span>
                  ) : (
                    <span className="flex items-center justify-center gap-2">
                      <span>Continuar</span>
                      <FontAwesomeIcon icon={faArrowRight} className="w-4 h-4" />
                    </span>
                  )}
                </RippleButton>
              </form>
            </>
          ) : step === 'forgot-password' ? (
            <>
              {/* Forgot Password Form */}
              <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-primary/10 via-primary/5 to-primary/10 border border-primary/20 shadow-sm animate-in slide-in-from-top-2 fade-in-0 duration-300">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center animate-in zoom-in-50 duration-300">
                      <FontAwesomeIcon icon={faLock} className="w-4 h-4 text-primary" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground mb-1">
                      Recuperar Senha
                    </p>
                    <p className="text-xs text-foreground/70">
                      Digite seu e-mail para receber um código de verificação e redefinir sua senha.
                    </p>
                  </div>
                </div>
              </div>

              <form onSubmit={handleRequestForgotPasswordCode} className="space-y-4 animate-in fade-in-0 duration-300">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    E-mail
                  </label>
                  <div className="relative">
                    <FontAwesomeIcon
                      icon={faEnvelope}
                      className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50"
                    />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="seu@email.com"
                      autoComplete="email"
                      className={`w-full pl-10 pr-4 py-3 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/30 transition-all ${loading ? 'opacity-60 cursor-not-allowed' : ''
                        }`}
                      required
                      disabled={loading}
                    />
                  </div>
                </div>

                <RippleButton
                  type="submit"
                  className="w-full py-3.5 bg-primary text-primary-foreground rounded-xl font-bold hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300 mt-2 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
                  disabled={loading}
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <FontAwesomeIcon icon={faSpinner} className="w-4 h-4 animate-spin" />
                      <span>Enviando código...</span>
                    </span>
                  ) : (
                    <span className="flex items-center justify-center gap-2">
                      <span>Enviar Código</span>
                      <FontAwesomeIcon icon={faArrowRight} className="w-4 h-4" />
                    </span>
                  )}
                </RippleButton>

                <button
                  type="button"
                  onClick={() => {
                    setStep('login')
                    setError(null)
                  }}
                  className="w-full text-sm text-foreground/60 hover:text-foreground transition-colors flex items-center justify-center gap-2"
                >
                  <FontAwesomeIcon icon={faArrowLeft} className="w-3 h-3" />
                  <span>Voltar para login</span>
                </button>
              </form>
            </>
          ) : step === 'reset-password' ? (
            <>
              {/* Reset Password Form */}
              <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-primary/10 via-primary/5 to-primary/10 border border-primary/20 shadow-sm animate-in slide-in-from-top-2 fade-in-0 duration-300">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center animate-in zoom-in-50 duration-300">
                      <FontAwesomeIcon icon={faCheckCircle} className="w-4 h-4 text-primary" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground mb-1">
                      Código enviado!
                    </p>
                    <p className="text-xs text-foreground/70">
                      Verifique o e-mail <span className="font-semibold text-foreground">{email}</span> e insira o código para redefinir sua senha.
                    </p>
                  </div>
                </div>
              </div>

              <form onSubmit={handleResetPassword} className="space-y-4 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Código de Verificação
                  </label>
                  <div className="relative">
                    {!code && (
                      <FontAwesomeIcon
                        icon={faKey}
                        className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50 pointer-events-none z-10"
                      />
                    )}
                    <input
                      type="text"
                      value={code}
                      onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      placeholder="000000"
                      autoComplete="off"
                      maxLength={6}
                      className={`w-full py-3 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20 transition-all text-center text-2xl tracking-widest font-mono focus:scale-[1.02] ${loading ? 'opacity-60 cursor-not-allowed' : ''
                        }`}
                      style={{
                        paddingLeft: code ? '1rem' : '1rem',
                        paddingRight: '1rem',
                        textAlign: 'center'
                      }}
                      required
                      disabled={loading}
                      autoFocus
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Nova Senha
                  </label>
                  <div className="relative">
                    <FontAwesomeIcon
                      icon={faLock}
                      className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50"
                    />
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => handlePasswordChange(e.target.value)}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      className={`w-full pl-10 pr-4 py-3 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/30 transition-all ${loading ? 'opacity-60 cursor-not-allowed' : ''
                        }`}
                      required
                      disabled={loading}
                    />
                  </div>
                  {!passwordValidation.valid && passwordValidation.errors.length > 0 && (
                    <div className="mt-2 text-xs text-red-500 space-y-1">
                      {passwordValidation.errors.map((err, idx) => (
                        <p key={idx}>• {err}</p>
                      ))}
                    </div>
                  )}
                </div>

                <RippleButton
                  type="submit"
                  className="w-full py-3.5 bg-primary text-primary-foreground rounded-xl font-bold hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300 mt-2 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
                  disabled={loading || code.length !== 6 || !passwordValidation.valid}
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <FontAwesomeIcon icon={faSpinner} className="w-4 h-4 animate-spin" />
                      <span>Redefinindo...</span>
                    </span>
                  ) : (
                    <span className="flex items-center justify-center gap-2">
                      <FontAwesomeIcon icon={faCheck} className="w-4 h-4" />
                      <span>Redefinir Senha</span>
                    </span>
                  )}
                </RippleButton>

                <button
                  type="button"
                  onClick={() => {
                    setStep('forgot-password')
                    setCode('')
                    setNewPassword('')
                    setError(null)
                  }}
                  className="w-full text-sm text-foreground/60 hover:text-foreground transition-colors flex items-center justify-center gap-2"
                >
                  <FontAwesomeIcon icon={faArrowLeft} className="w-3 h-3" />
                  <span>Voltar</span>
                </button>
              </form>
            </>
          ) : (
            <>
              {/* Code Verification Form */}
              <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-primary/10 via-primary/5 to-primary/10 border border-primary/20 shadow-sm animate-in slide-in-from-top-2 fade-in-0 duration-300">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center animate-in zoom-in-50 duration-300">
                      <FontAwesomeIcon icon={faCheckCircle} className="w-4 h-4 text-primary" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground mb-1">
                      Código enviado!
                    </p>
                    <p className="text-xs text-foreground/70">
                      Verifique o e-mail <span className="font-semibold text-foreground">{email}</span> e insira o código de 6 dígitos abaixo.
                    </p>
                  </div>
                </div>
              </div>

              <form onSubmit={handleVerifyCode} className="space-y-4 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Código de Verificação
                  </label>
                  <div className="relative">
                    {!code && (
                      <FontAwesomeIcon
                        icon={faKey}
                        className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50 pointer-events-none z-10"
                      />
                    )}
                    <input
                      type="text"
                      value={code}
                      onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      placeholder="000000"
                      autoComplete="off"
                      maxLength={6}
                      className={`w-full py-3 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20 transition-all text-center text-2xl tracking-widest font-mono focus:scale-[1.02] ${loading ? 'opacity-60 cursor-not-allowed' : ''
                        }`}
                      style={{
                        paddingLeft: code ? '1rem' : '1rem',
                        paddingRight: '1rem',
                        textAlign: 'center'
                      }}
                      required
                      disabled={loading}
                      autoFocus
                    />
                  </div>
                  <p className="text-xs text-foreground/60 mt-2 text-center">
                    Digite o código de 6 dígitos enviado por e-mail
                  </p>
                </div>

                {/* Checkbox para confiar no dispositivo */}
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="trustDevice"
                    checked={trustDevice}
                    onChange={(e) => setTrustDevice(e.target.checked)}
                    className="w-4 h-4 rounded border-foreground/20 text-primary focus:ring-primary/50 focus:ring-2"
                    disabled={loading}
                  />
                  <label htmlFor="trustDevice" className="text-sm text-foreground/80 cursor-pointer select-none">
                    Confiar neste dispositivo
                  </label>
                </div>
                <p className="text-xs text-foreground/50 -mt-2">
                  Não pedir código nas próximas vezes neste dispositivo
                </p>

                <RippleButton
                  type="submit"
                  className="w-full py-3.5 bg-primary text-primary-foreground rounded-xl font-bold hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300 mt-2 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
                  disabled={loading || code.length !== 6}
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <FontAwesomeIcon icon={faSpinner} className="w-4 h-4 animate-spin" />
                      <span>Verificando...</span>
                    </span>
                  ) : (
                    <span className="flex items-center justify-center gap-2">
                      <FontAwesomeIcon icon={faCheck} className="w-4 h-4" />
                      <span>Verificar Código</span>
                    </span>
                  )}
                </RippleButton>

                <button
                  type="button"
                  onClick={() => {
                    setStep('login')
                    setCode('')
                    setError(null)
                  }}
                  className="w-full text-sm text-foreground/60 hover:text-foreground transition-colors flex items-center justify-center gap-2"
                >
                  <FontAwesomeIcon icon={faArrowLeft} className="w-3 h-3" />
                  <span>Voltar</span>
                </button>
              </form>
            </>
          )}

          <p className="text-center text-sm text-foreground/60 mt-6">
            Não tem uma conta?{' '}
            <Link href="/signup" className="text-primary hover:text-primary/80 font-medium transition-colors">
              Criar conta
            </Link>
          </p>
        </div>

        {/* Back to Home */}
        <div className="text-center mt-6">
          <Link href="/" className="text-sm text-foreground/60 hover:text-foreground transition-colors inline-flex items-center gap-2">
            <FontAwesomeIcon icon={faArrowLeft} className="w-3 h-3" />
            <span>Voltar para o início</span>
          </Link>
        </div>
      </div>
    </div>
  )
}
