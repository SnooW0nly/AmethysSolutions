/**
 * Validador de senha forte
 */

/**
 * Valida se a senha atende aos requisitos de segurança
 * @param {string} password - Senha a ser validada
 * @returns {{ valid: boolean; errors: string[] }} - Resultado da validação
 */
export function validatePassword(password) {
  const errors = [];

  if (!password) {
    return { valid: false, errors: ['Senha é obrigatória'] };
  }

  // Mínimo de 8 caracteres
  if (password.length < 8) {
    errors.push('A senha deve ter no mínimo 8 caracteres');
  }

  // Pelo menos uma letra maiúscula
  if (!/[A-Z]/.test(password)) {
    errors.push('A senha deve conter pelo menos uma letra maiúscula');
  }

  // Pelo menos uma letra minúscula
  if (!/[a-z]/.test(password)) {
    errors.push('A senha deve conter pelo menos uma letra minúscula');
  }

  // Pelo menos um número
  if (!/[0-9]/.test(password)) {
    errors.push('A senha deve conter pelo menos um número');
  }

  // Pelo menos um caractere especial
  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
    errors.push('A senha deve conter pelo menos um caractere especial (!@#$%^&*()_+-=[]{};\':"|,.<>/? etc)');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

