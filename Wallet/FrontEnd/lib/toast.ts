/**
 * Funções helper para facilitar o uso de toasts
 */

import { toast as toastFn } from '@/components/ui/use-toast'

/**
 * Exibe um toast de sucesso
 */
export function toastSuccess(description: string, title?: string) {
  return toastFn({
    title: title || 'Sucesso',
    description,
    variant: 'success',
  })
}

/**
 * Exibe um toast de erro
 */
export function toastError(description: string, title?: string) {
  return toastFn({
    title: title || 'Erro',
    description,
    variant: 'destructive',
  })
}

/**
 * Exibe um toast informativo
 */
export function toastInfo(description: string, title?: string) {
  return toastFn({
    title: title || 'Informação',
    description,
    variant: 'default',
  })
}

