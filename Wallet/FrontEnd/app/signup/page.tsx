'use client'

import { useState, useEffect, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faEnvelope, faLock, faUser, faCalendar, faPhone, faEye, faEyeSlash, faKey, faCheckCircle, faArrowRight, faSpinner, faUserPlus, faArrowLeft, faIdCard, faMapPin } from '@fortawesome/free-solid-svg-icons'
import { RippleButton } from '@/components/ripple-button'
import { requestSignupCode, signup, isAuthenticated } from '@/lib/auth'
import { trackAffiliateClick } from '@/lib/wallet'
import { validatePassword } from '@/lib/passwordValidator'

function SignupContent() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [passwordErrors, setPasswordErrors] = useState<string[]>([])
  const [cpfError, setCpfError] = useState<string | null>(null)
  const [fullNameError, setFullNameError] = useState<string | null>(null)
  const [step, setStep] = useState<'form' | 'code'>('form')
  const [code, setCode] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [zipCodeError, setZipCodeError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    fullName: '',
    birthDate: '',
    cpf: '',
    zipCode: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
  })

  // Limites de caracteres
  const MAX_NAME_LENGTH = 100
  const MAX_PHONE_LENGTH = 15

  const searchParams = useSearchParams()
  const refCode = searchParams.get('ref')

  // Salvar código de afiliado no cookie se existir na URL
  useEffect(() => {
    if (refCode) {
      document.cookie = `affiliate_code=${refCode}; path=/; max-age=604800` // 7 dias
      trackAffiliateClick(refCode).catch(console.error)
    }
  }, [refCode])

  // Redirecionar se já estiver logado
  useEffect(() => {
    if (isAuthenticated()) {
      router.push('/')
    }
  }, [router])

  // Validar nome completo (pelo menos primeiro e último nome)
  const validateFullName = (name: string): { valid: boolean; error: string | null } => {
    const trimmed = name.trim()
    if (!trimmed) {
      return { valid: false, error: 'Nome é obrigatório' }
    }
    const nameParts = trimmed.split(/\s+/).filter(part => part.length > 0)
    if (nameParts.length < 2) {
      return { valid: false, error: 'Informe nome e sobrenome' }
    }
    if (nameParts.some(part => part.length < 2)) {
      return { valid: false, error: 'Cada parte do nome deve ter pelo menos 2 caracteres' }
    }
    return { valid: true, error: null }
  }

  // Função para formatar CPF
  const formatCPF = (value: string) => {
    const numbers = value.replace(/\D/g, '')
    if (numbers.length <= 11) {
      return numbers
        .replace(/(\d{3})(\d)/, '$1.$2')
        .replace(/(\d{3})(\d)/, '$1.$2')
        .replace(/(\d{3})(\d{1,2})$/, '$1-$2')
    }
    return value
  }

  // Função para formatar CEP
  const formatZipCode = (value: string) => {
    const numbers = value.replace(/\D/g, '')
    if (numbers.length <= 8) {
      return numbers.replace(/(\d{5})(\d)/, '$1-$2')
    }
    return value
  }

  // Função para formatar telefone
  const formatPhone = (value: string) => {
    const numbers = value.replace(/\D/g, '')
    if (numbers.length <= 11) {
      if (numbers.length <= 2) return numbers
      if (numbers.length <= 7) return `(${numbers.slice(0, 2)}) ${numbers.slice(2)}`
      return `(${numbers.slice(0, 2)}) ${numbers.slice(2, 7)}-${numbers.slice(7)}`
    }
    return value
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value
    const name = e.target.name

    // Validar e limitar nome
    if (name === 'fullName') {
      if (value.length > MAX_NAME_LENGTH) return
      const validation = validateFullName(value)
      setFullNameError(value.length > 0 ? validation.error : null)
    }

    // Formatar CPF automaticamente
    if (name === 'cpf') {
      value = formatCPF(value)
      // Validar CPF em tempo real
      const cleaned = value.replace(/[.\-/]/g, '')
      if (cleaned.length === 11) {
        const cpfValidation = validateCPF(value)
        if (cpfValidation.valid) {
          setCpfError(null)
        } else {
          setCpfError(cpfValidation.error || null)
        }
      } else if (cleaned.length > 0) {
        setCpfError('CPF deve conter 11 dígitos')
      } else {
        setCpfError(null)
      }
    }

    // Formatar CEP automaticamente
    if (name === 'zipCode') {
      value = formatZipCode(value)
      const cleaned = value.replace(/\D/g, '')
      if (cleaned.length === 8) {
        setZipCodeError(null)
      } else if (cleaned.length > 0) {
        setZipCodeError('CEP deve conter 8 dígitos')
      } else {
        setZipCodeError(null)
      }
      if (value.length > 9) return
    }

    // Formatar e limitar telefone
    if (name === 'phone') {
      value = formatPhone(value)
      if (value.length > MAX_PHONE_LENGTH) return
    }

    setFormData({
      ...formData,
      [name]: value,
    })
    setError(null)

    // Validar senha em tempo real
    if (name === 'password') {
      const validation = validatePassword(e.target.value)
      setPasswordErrors(validation.errors)
    } else if (name === 'confirmPassword') {
      setPasswordErrors([])
    }
  }

  // Validar CPF usando algoritmo oficial brasileiro de dígitos verificadores
  const validateCPF = (cpf: string): { valid: boolean; error?: string } => {
    const cleaned = cpf.replace(/[.\-/]/g, '')

    // Verificar se tem 11 dígitos
    if (cleaned.length !== 11) {
      return { valid: false, error: 'CPF deve conter 11 dígitos' }
    }

    // Verificar se todos os dígitos são iguais (CPF inválido)
    if (/^(\d)\1{10}$/.test(cleaned)) {
      return { valid: false, error: 'CPF inválido. Todos os dígitos são iguais' }
    }

    // Calcular primeiro dígito verificador
    let sum = 0
    for (let i = 0; i < 9; i++) {
      sum += parseInt(cleaned.charAt(i)) * (10 - i)
    }
    let remainder = sum % 11
    let firstDigit = remainder < 2 ? 0 : 11 - remainder

    if (firstDigit !== parseInt(cleaned.charAt(9))) {
      return { valid: false, error: 'CPF inválido. Verifique os dígitos verificadores' }
    }

    // Calcular segundo dígito verificador
    sum = 0
    for (let i = 0; i < 10; i++) {
      sum += parseInt(cleaned.charAt(i)) * (11 - i)
    }
    remainder = sum % 11
    let secondDigit = remainder < 2 ? 0 : 11 - remainder

    if (secondDigit !== parseInt(cleaned.charAt(10))) {
      return { valid: false, error: 'CPF inválido. Verifique os dígitos verificadores' }
    }

    return { valid: true }
  }

  const handleRequestCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validar nome completo
    const nameValidation = validateFullName(formData.fullName)
    if (!nameValidation.valid) {
      setError(nameValidation.error || 'Nome completo é obrigatório')
      setFullNameError(nameValidation.error)
      return
    }

    // Validar CPF (obrigatório)
    if (!formData.cpf) {
      setError('CPF é obrigatório')
      setCpfError('CPF é obrigatório')
      return
    }
    const cpfValidation = validateCPF(formData.cpf)
    if (!cpfValidation.valid) {
      setError(cpfValidation.error || 'CPF inválido')
      setCpfError(cpfValidation.error || 'CPF inválido')
      return
    }

    // Validar CEP (obrigatório)
    const cleanedZip = formData.zipCode.replace(/\D/g, '')
    if (!cleanedZip || cleanedZip.length !== 8) {
      setError('CEP é obrigatório e deve conter 8 dígitos')
      setZipCodeError('CEP deve conter 8 dígitos')
      return
    }

    if (formData.password !== formData.confirmPassword) {
      setError('As senhas não coincidem')
      return
    }

    // Validar senha forte
    const passwordValidation = validatePassword(formData.password)
    if (!passwordValidation.valid) {
      setError(passwordValidation.errors.join(', '))
      setPasswordErrors(passwordValidation.errors)
      return
    }

    setLoading(true)

    try {
      await requestSignupCode(formData.email, formData.password)
      setStep('code')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao solicitar código')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {

      // Obter código de afiliado do cookie se existir
      let affiliateCode = undefined;
      if (typeof document !== 'undefined') {
        const cookies = document.cookie.split(';');
        const affiliateCookie = cookies.find(c => c.trim().startsWith('affiliate_code='));
        if (affiliateCookie) {
          affiliateCode = affiliateCookie.split('=')[1];
        }
      }

      const response = await signup({
        fullName: formData.fullName,
        email: formData.email,
        password: formData.password,
        code,
        birthDate: formData.birthDate,
        taxID: formData.cpf.replace(/\D/g, ''),
        zipCode: formData.zipCode.replace(/\D/g, ''),
        phone: formData.phone || undefined,
        affiliateCode,
      })

      if (response.success && response.token) {
        // Se o cadastro retornou token, fazer login automático e ir para dashboard
        if (typeof window !== 'undefined' && response.token) {
          localStorage.setItem('token', response.token)

          // Salvar usuário temporariamente se disponível
          if (response.user) {
            sessionStorage.setItem('temp_user', JSON.stringify(response.user))
            window.dispatchEvent(new Event('storage'))
            window.dispatchEvent(new CustomEvent('auth-change', { detail: { user: response.user, token: response.token } }))
          }

          // Delay para garantir que o token seja salvo
          await new Promise(resolve => setTimeout(resolve, 300))

          // Forçar atualização completa da página ao redirecionar para dashboard
          window.location.href = '/dashboard'
        } else {
          // Se não houver token, redirecionar para login
          router.push('/login?registered=true')
        }
      } else if (response.success) {
        // Redirecionar para login após cadastro bem-sucedido (sem token)
        router.push('/login?registered=true')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Código inválido ou expirado')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[calc(100vh-120px)] sm:min-h-[calc(100vh-200px)] flex items-center justify-center p-4 sm:p-6 -mt-4 sm:-mt-8">
      <div className="w-full max-w-md">
        {/* Card */}
        <div className="p-5 sm:p-8 rounded-2xl border border-foreground/10 bg-foreground/2 backdrop-blur-sm shadow-xl">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-foreground">Criar conta</h1>
            <p className="text-foreground/60 text-sm mt-1">Preencha seus dados para começar</p>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm animate-in slide-in-from-top-2 fade-in-0 duration-200">
              <div className="flex items-start gap-2">
                <span className="text-red-500 mt-0.5">⚠</span>
                <span>{error}</span>
              </div>
            </div>
          )}

          {step === 'form' ? (
            <>
              {/* Signup Form */}
              <form onSubmit={handleRequestCode} className="space-y-4 animate-in fade-in-0 duration-300" autoComplete="off">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Nome Completo
                  </label>
                  <div className="relative">
                    <FontAwesomeIcon
                      icon={faUser}
                      className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50"
                    />
                    <input
                      type="text"
                      name="fullName"
                      value={formData.fullName}
                      onChange={handleChange}
                      placeholder="Seu nome completo"
                      autoComplete="off"
                      maxLength={MAX_NAME_LENGTH}
                      className={`w-full pl-10 pr-4 py-3 rounded-lg bg-foreground/5 border ${fullNameError && formData.fullName ? 'border-red-500/50' : !fullNameError && formData.fullName && validateFullName(formData.fullName).valid ? 'border-green-500/50' : 'border-foreground/10'} text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/30 transition-all ${loading ? 'opacity-60 cursor-not-allowed' : ''}`}
                      required
                      disabled={loading}
                    />
                  </div>
                  <div className="flex justify-between mt-1">
                    {fullNameError && formData.fullName ? (
                      <p className="text-xs text-red-500">{fullNameError}</p>
                    ) : !fullNameError && formData.fullName && validateFullName(formData.fullName).valid ? (
                      <p className="text-xs text-green-500">✓ Nome válido</p>
                    ) : (
                      <p className="text-xs text-foreground/60">Informe nome e sobrenome</p>
                    )}
                    <p className="text-xs text-foreground/40">{formData.fullName.length}/{MAX_NAME_LENGTH}</p>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Data de Nascimento
                  </label>
                  <div className="relative">
                    <FontAwesomeIcon
                      icon={faCalendar}
                      className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50"
                    />
                    <input
                      type="date"
                      name="birthDate"
                      value={formData.birthDate}
                      onChange={handleChange}
                      autoComplete="off"
                      className={`w-full pl-10 pr-4 py-3 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/30 transition-all ${loading ? 'opacity-60 cursor-not-allowed' : ''
                        }`}
                      required
                      disabled={loading}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    CPF
                  </label>
                  <div className="relative">
                    <FontAwesomeIcon
                      icon={faIdCard}
                      className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50"
                    />
                    <input
                      type="text"
                      name="cpf"
                      value={formData.cpf}
                      onChange={handleChange}
                      placeholder="000.000.000-00"
                      autoComplete="off"
                      maxLength={14}
                      className={`w-full pl-10 pr-4 py-3 rounded-lg bg-foreground/5 border ${cpfError
                        ? 'border-red-500/50 focus:border-red-500/50 focus:ring-red-500/50'
                        : formData.cpf && !cpfError && formData.cpf.replace(/[.\-/]/g, '').length === 11
                          ? 'border-green-500/50 focus:border-green-500/50 focus:ring-green-500/50'
                          : 'border-foreground/10 focus:border-primary/30 focus:ring-primary/50'
                        } text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 transition-all ${loading ? 'opacity-60 cursor-not-allowed' : ''
                        }`}
                      required
                      disabled={loading}
                    />
                  </div>
                  {cpfError ? (
                    <p className="text-xs text-red-500 mt-1">{cpfError}</p>
                  ) : formData.cpf && formData.cpf.replace(/[.\-/]/g, '').length === 11 ? (
                    <p className="text-xs text-green-500 mt-1">✓ CPF válido</p>
                  ) : (
                    <p className="text-xs text-foreground/60 mt-1">
                      Informe apenas números (será formatado automaticamente)
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    CEP
                  </label>
                  <div className="relative">
                    <FontAwesomeIcon
                      icon={faMapPin}
                      className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50"
                    />
                    <input
                      type="text"
                      name="zipCode"
                      value={formData.zipCode}
                      onChange={handleChange}
                      placeholder="00000-000"
                      autoComplete="off"
                      maxLength={9}
                      className={`w-full pl-10 pr-4 py-3 rounded-lg bg-foreground/5 border ${zipCodeError
                        ? 'border-red-500/50 focus:border-red-500/50 focus:ring-red-500/50'
                        : formData.zipCode && !zipCodeError && formData.zipCode.replace(/\D/g, '').length === 8
                          ? 'border-green-500/50 focus:border-green-500/50 focus:ring-green-500/50'
                          : 'border-foreground/10 focus:border-primary/30 focus:ring-primary/50'
                        } text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 transition-all ${loading ? 'opacity-60 cursor-not-allowed' : ''
                        }`}
                      required
                      disabled={loading}
                    />
                  </div>
                  {zipCodeError ? (
                    <p className="text-xs text-red-500 mt-1">{zipCodeError}</p>
                  ) : formData.zipCode && formData.zipCode.replace(/\D/g, '').length === 8 ? (
                    <p className="text-xs text-green-500 mt-1">✓ CEP válido</p>
                  ) : (
                    <p className="text-xs text-foreground/60 mt-1">
                      Informe apenas números (será formatado automaticamente)
                    </p>
                  )}
                </div>

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
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="seu@email.com"
                      autoComplete="off"
                      className={`w-full pl-10 pr-4 py-3 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/30 transition-all ${loading ? 'opacity-60 cursor-not-allowed' : ''
                        }`}
                      required
                      disabled={loading}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Telefone
                  </label>
                  <div className="relative">
                    <FontAwesomeIcon
                      icon={faPhone}
                      className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50"
                    />
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      placeholder="(00) 00000-0000"
                      autoComplete="off"
                      maxLength={MAX_PHONE_LENGTH}
                      className={`w-full pl-10 pr-4 py-3 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/30 transition-all ${loading ? 'opacity-60 cursor-not-allowed' : ''}`}
                      required
                      disabled={loading}
                    />
                  </div>
                  <div className="flex justify-end mt-1">
                    <p className="text-xs text-foreground/40">{formData.phone.length}/{MAX_PHONE_LENGTH}</p>
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
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      className={`w-full pl-10 pr-12 py-3 rounded-lg bg-foreground/5 border ${passwordErrors.length > 0 && formData.password
                        ? 'border-red-500/50'
                        : 'border-foreground/10'
                        } text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/30 transition-all`}
                      required
                      disabled={loading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground/50 hover:text-foreground transition-colors"
                      disabled={loading}
                    >
                      <FontAwesomeIcon icon={showPassword ? faEyeSlash : faEye} className="w-4 h-4" />
                    </button>
                  </div>
                  {passwordErrors.length > 0 && formData.password && (
                    <div className="mt-2 space-y-1">
                      {passwordErrors.map((err, idx) => (
                        <p key={idx} className="text-xs text-red-500">
                          • {err}
                        </p>
                      ))}
                    </div>
                  )}
                  {formData.password && passwordErrors.length === 0 && (
                    <p className="text-xs text-green-500 mt-2">✓ Senha válida</p>
                  )}
                  {!formData.password && (
                    <p className="text-xs text-foreground/60 mt-2">
                      A senha deve conter: mínimo 8 caracteres, 1 maiúscula, 1 minúscula, 1 número e 1 caractere especial
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Confirmar Senha
                  </label>
                  <div className="relative">
                    <FontAwesomeIcon
                      icon={faLock}
                      className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50"
                    />
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      name="confirmPassword"
                      value={formData.confirmPassword}
                      onChange={handleChange}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      className={`w-full pl-10 pr-12 py-3 rounded-lg bg-foreground/5 border border-foreground/10 text-foreground placeholder-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/30 transition-all ${loading ? 'opacity-60 cursor-not-allowed' : ''
                        }`}
                      required
                      disabled={loading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground/50 hover:text-foreground transition-colors"
                      disabled={loading}
                    >
                      <FontAwesomeIcon icon={showConfirmPassword ? faEyeSlash : faEye} className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <RippleButton
                  type="submit"
                  className="w-full py-3.5 bg-primary text-primary-foreground rounded-xl font-bold hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300 mt-2 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
                  disabled={loading || !!cpfError || !!fullNameError || !!zipCodeError || !formData.fullName || formData.cpf.replace(/[.\-/]/g, '').length !== 11 || formData.zipCode.replace(/\D/g, '').length !== 8}
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
                      Verifique o e-mail <span className="font-semibold text-foreground">{formData.email}</span> e insira o código de 6 dígitos abaixo para completar seu cadastro.
                    </p>
                  </div>
                </div>
              </div>

              <form onSubmit={handleVerifyCode} className="space-y-4 animate-in fade-in-0 slide-in-from-bottom-2 duration-300" autoComplete="off">
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

                <RippleButton
                  type="submit"
                  className="w-full py-3.5 bg-primary text-primary-foreground rounded-xl font-bold hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300 mt-2 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
                  disabled={loading || code.length !== 6}
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <FontAwesomeIcon icon={faSpinner} className="w-4 h-4 animate-spin" />
                      <span>Criando conta...</span>
                    </span>
                  ) : (
                    <span className="flex items-center justify-center gap-2">
                      <FontAwesomeIcon icon={faUserPlus} className="w-4 h-4" />
                      <span>Criar conta</span>
                    </span>
                  )}
                </RippleButton>

                <button
                  type="button"
                  onClick={() => {
                    setStep('form')
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
            Já tem uma conta?{' '}
            <Link href="/login" className="text-primary hover:text-primary/80 font-medium transition-colors">
              Fazer login
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

// Wrapper com Suspense para useSearchParams
export default function SignupPage() {
  return (
    <Suspense fallback={
      <div className="min-h-[calc(100vh-120px)] flex items-center justify-center">
        <FontAwesomeIcon icon={faSpinner} className="w-6 h-6 animate-spin text-primary" />
      </div>
    }>
      <SignupContent />
    </Suspense>
  )
}
