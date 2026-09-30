import crypto from 'crypto';

/**
 * Gera uma API Key única para o usuário
 */
export function generateApiKey() {
  return 'vp_' + crypto.randomBytes(32).toString('hex');
}

/**
 * Gera um ID único
 */
export function generateUniqueId() {
  return crypto.randomBytes(16).toString('hex');
}

/**
 * Hash de senha
 */
export function hashPassword(password) {
  return crypto.createHash('sha256').update(password).digest('hex');
}

/**
 * Valida CPF usando algoritmo oficial brasileiro de dígitos verificadores
 * (Não usa Luhn - CPF tem algoritmo próprio)
 */
export function validateCPF(cpf) {
  const cleaned = cpf.replace(/[.\-/]/g, '');
  
  // Verificar se tem 11 dígitos
  if (cleaned.length !== 11) {
    return false;
  }
  
  // Verificar se todos os dígitos são iguais (CPF inválido)
  if (/^(\d)\1{10}$/.test(cleaned)) {
    return false;
  }
  
  // Calcular primeiro dígito verificador
  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(cleaned.charAt(i)) * (10 - i);
  }
  let remainder = sum % 11;
  let firstDigit = remainder < 2 ? 0 : 11 - remainder;
  
  if (firstDigit !== parseInt(cleaned.charAt(9))) {
    return false;
  }
  
  // Calcular segundo dígito verificador
  sum = 0;
  for (let i = 0; i < 10; i++) {
    sum += parseInt(cleaned.charAt(i)) * (11 - i);
  }
  remainder = sum % 11;
  let secondDigit = remainder < 2 ? 0 : 11 - remainder;
  
  if (secondDigit !== parseInt(cleaned.charAt(10))) {
    return false;
  }
  
  return true;
}

/**
 * Valida CNPJ usando algoritmo oficial brasileiro de dígitos verificadores
 * (Não usa Luhn - CNPJ tem algoritmo próprio)
 */
export function validateCNPJ(cnpj) {
  const cleaned = cnpj.replace(/[.\-/]/g, '');
  
  // Verificar se tem 14 dígitos
  if (cleaned.length !== 14) {
    return false;
  }
  
  // Verificar se todos os dígitos são iguais (CNPJ inválido)
  if (/^(\d)\1{13}$/.test(cleaned)) {
    return false;
  }
  
  // Pesos para cálculo dos dígitos verificadores
  const weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  
  // Calcular primeiro dígito verificador
  let sum = 0;
  for (let i = 0; i < 12; i++) {
    sum += parseInt(cleaned.charAt(i)) * weights1[i];
  }
  let remainder = sum % 11;
  let firstDigit = remainder < 2 ? 0 : 11 - remainder;
  
  if (firstDigit !== parseInt(cleaned.charAt(12))) {
    return false;
  }
  
  // Calcular segundo dígito verificador
  sum = 0;
  for (let i = 0; i < 13; i++) {
    sum += parseInt(cleaned.charAt(i)) * weights2[i];
  }
  remainder = sum % 11;
  let secondDigit = remainder < 2 ? 0 : 11 - remainder;
  
  if (secondDigit !== parseInt(cleaned.charAt(13))) {
    return false;
  }
  
  return true;
}

/**
 * Valida número usando algoritmo de Luhn
 * Útil para validar cartões de crédito, números de identificação, etc.
 */
export function validateLuhn(number) {
  const cleaned = number.replace(/\D/g, '');
  
  if (cleaned.length < 2) {
    return false;
  }
  
  let sum = 0;
  let isEven = false;
  
  // Percorrer da direita para a esquerda
  for (let i = cleaned.length - 1; i >= 0; i--) {
    let digit = parseInt(cleaned.charAt(i));
    
    if (isEven) {
      digit *= 2;
      if (digit > 9) {
        digit -= 9;
      }
    }
    
    sum += digit;
    isEven = !isEven;
  }
  
  return sum % 10 === 0;
}

/**
 * Valida CPF/CNPJ (valida ambos usando algoritmos de dígitos verificadores)
 */
export function validateTaxID(taxID) {
  if (!taxID) {
    return false;
  }
  
  const cleaned = taxID.replace(/[.\-/]/g, '');
  
  // CPF tem 11 dígitos
  if (cleaned.length === 11) {
    return validateCPF(cleaned);
  }
  
  // CNPJ tem 14 dígitos
  if (cleaned.length === 14) {
    return validateCNPJ(cleaned);
  }
  
  return false;
}

/**
 * Valida email
 */
export function validateEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

