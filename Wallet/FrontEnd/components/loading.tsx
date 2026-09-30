'use client'

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faSpinner } from '@fortawesome/free-solid-svg-icons'

export function Loading() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <FontAwesomeIcon icon={faSpinner} className="w-8 h-8 text-primary animate-spin" />
    </div>
  )
}

