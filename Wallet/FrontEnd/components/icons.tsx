'use client'

import * as React from 'react'

interface IconSvgProps {
  size?: number
  width?: number
  height?: number
  className?: string
}

export const Logo: React.FC<IconSvgProps> = ({
  size = 38,
  width,
  height,
  className,
  ...props
}) => {
  const logoWidth = width || size
  const logoHeight = height || size

  return (
    <img
      src="/icon.svg"
      alt="Amethys Wallet Logo"
      width={logoWidth}
      height={logoHeight}
      className={className}
      {...props}
    />
  )
}

