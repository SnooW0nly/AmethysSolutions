'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'

interface DataPoint {
  month: string
  value1: number
  value2: number
}

export function PerformanceChart() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  const data: DataPoint[] = [
    { month: 'Jan', value1: 45, value2: 38 },
    { month: 'Fev', value1: 52, value2: 45 },
    { month: 'Mar', value1: 58, value2: 51 },
    { month: 'Abr', value1: 65, value2: 58 },
    { month: 'Mai', value1: 72, value2: 65 },
    { month: 'Jun', value1: 78, value2: 71 },
    { month: 'Jul', value1: 85, value2: 78 },
  ]

  const maxValue = 100
  const chartHeight = 300
  const chartWidth = 1000
  const padding = { top: 30, bottom: 40, left: 40, right: 40 }
  const innerWidth = chartWidth - padding.left - padding.right
  const innerHeight = chartHeight - padding.top - padding.bottom

  // Create smooth curve path
  const createSmoothPath = (values: number[]) => {
    let path = ''
    const points = values.map((value, idx) => {
      const x = padding.left + (idx / (values.length - 1)) * innerWidth
      const y = padding.top + innerHeight - (value / maxValue) * innerHeight
      return { x, y }
    })

    points.forEach((point, idx) => {
      if (idx === 0) {
        path += `M ${point.x} ${point.y}`
      } else {
        const prevPoint = points[idx - 1]
        const cp1x = prevPoint.x + (point.x - prevPoint.x) / 2
        const cp1y = prevPoint.y
        const cp2x = prevPoint.x + (point.x - prevPoint.x) / 2
        const cp2y = point.y
        path += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${point.x} ${point.y}`
      }
    })

    return path
  }

  // Create area path
  const createAreaPath = (values: number[]) => {
    let path = createSmoothPath(values)
    const lastPoint = values[values.length - 1]
    const firstPoint = values[0]
    const lastX = padding.left + ((values.length - 1) / (values.length - 1)) * innerWidth
    const firstX = padding.left
    const bottomY = padding.top + innerHeight
    
    path += ` L ${lastX} ${bottomY} L ${firstX} ${bottomY} Z`
    return path
  }

  const getPointPosition = (index: number) => {
    const value = data[index].value1
    const x = padding.left + (index / (data.length - 1)) * innerWidth
    const y = padding.top + innerHeight - (value / maxValue) * innerHeight
    return { x, y }
  }

  return (
    <div className="relative w-full">
      <div className="relative w-full bg-foreground/2 border border-foreground/10 rounded-xl p-6 md:p-8">
        {/* Chart Container */}
        <div className="relative w-full" style={{ height: `${chartHeight}px` }}>
          <svg 
            className="w-full h-full" 
            viewBox={`0 0 ${chartWidth} ${chartHeight}`}
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id="areaGradient1" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#ff6400" stopOpacity="0.4" />
                <stop offset="50%" stopColor="#ff6400" stopOpacity="0.2" />
                <stop offset="100%" stopColor="#ff6400" stopOpacity="0" />
              </linearGradient>
              <linearGradient id="areaGradient2" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#ff6400" stopOpacity="0.3" />
                <stop offset="50%" stopColor="#ff6400" stopOpacity="0.15" />
                <stop offset="100%" stopColor="#ff6400" stopOpacity="0" />
              </linearGradient>
              <filter id="glow">
                <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>

            {/* Grid lines */}
            {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
              const y = padding.top + innerHeight * ratio
              return (
                <line
                  key={`grid-${i}`}
                  x1={padding.left}
                  y1={y}
                  x2={padding.left + innerWidth}
                  y2={y}
                  stroke="rgba(255, 255, 255, 0.05)"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
              )
            })}

            {/* Y-axis labels */}
            {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
              const y = padding.top + innerHeight * ratio
              const value = Math.round(maxValue * (1 - ratio))
              return (
                <text
                  key={`y-label-${i}`}
                  x={padding.left - 10}
                  y={y + 4}
                  textAnchor="end"
                  fill="rgba(255, 255, 255, 0.4)"
                  fontSize="12"
                  fontFamily="monospace"
                >
                  {value}%
                </text>
              )
            })}

            {/* Area fills */}
            <path
              d={createAreaPath(data.map(d => d.value1))}
              fill="url(#areaGradient1)"
              className="transition-opacity duration-300"
              style={{ opacity: hoveredIndex !== null ? 0.6 : 0.4 }}
            />
            <path
              d={createAreaPath(data.map(d => d.value2))}
              fill="url(#areaGradient2)"
              className="transition-opacity duration-300"
              style={{ opacity: hoveredIndex !== null ? 0.5 : 0.3 }}
            />

            {/* Smooth lines */}
            <path
              d={createSmoothPath(data.map(d => d.value1))}
              fill="none"
              stroke="#ff6400"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              filter="url(#glow)"
            />
            <path
              d={createSmoothPath(data.map(d => d.value2))}
              fill="none"
              stroke="#ff6400"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeOpacity="0.7"
            />

            {/* Data points and hover areas */}
            {data.map((point, idx) => {
              const { x, y } = getPointPosition(idx)
              const hoverRadius = 20
              
              return (
                <g key={`point-${idx}`}>
                  {/* Hover area */}
                  <circle
                    cx={x}
                    cy={y}
                    r={hoverRadius}
                    fill="transparent"
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHoveredIndex(idx)}
                    onMouseLeave={() => setHoveredIndex(null)}
                  />
                  
                  {/* Point circle */}
                  {hoveredIndex === idx && (
                    <>
                      <circle
                        cx={x}
                        cy={y}
                        r="8"
                        fill="#ff6400"
                        filter="url(#glow)"
                      />
                      <circle
                        cx={x}
                        cy={y}
                        r="12"
                        fill="#ff6400"
                        opacity="0.3"
                      />
                      <circle
                        cx={x}
                        cy={y}
                        r="16"
                        fill="#ff6400"
                        opacity="0.1"
                      />
                    </>
                  )}
                </g>
              )
            })}
          </svg>

          {/* X-axis labels */}
          <div className="absolute flex justify-between w-full" style={{ top: `${chartHeight - padding.bottom + 10}px`, left: `${padding.left}px`, width: `${innerWidth}px` }}>
            {data.map((point, idx) => (
              <div
                key={idx}
                className="text-xs text-muted-foreground font-medium transition-all duration-200 text-center"
                style={{ 
                  opacity: hoveredIndex === idx ? 1 : 0.6,
                  transform: hoveredIndex === idx ? 'scale(1.1)' : 'scale(1)',
                  fontWeight: hoveredIndex === idx ? 600 : 500
                }}
              >
                {point.month}
              </div>
            ))}
          </div>

          {/* Tooltip */}
          {hoveredIndex !== null && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute px-4 py-2 bg-background border border-primary/30 text-foreground rounded-lg text-sm font-medium whitespace-nowrap shadow-2xl z-20 pointer-events-none backdrop-blur-lg"
              style={{
                left: `${(getPointPosition(hoveredIndex).x / chartWidth) * 100}%`,
                top: `${((getPointPosition(hoveredIndex).y - 40) / chartHeight) * 100}%`,
                transform: 'translateX(-50%) translateY(-100%)',
                boxShadow: '0 10px 40px rgba(255, 107, 53, 0.3)'
              }}
            >
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full bg-primary" style={{ boxShadow: '0 0 8px rgba(255, 107, 53, 0.5)' }} />
                <div className="font-bold text-foreground">{data[hoveredIndex].month}</div>
              </div>
              <div className="text-muted-foreground text-xs mb-0.5">Linha Principal</div>
              <div className="font-semibold text-foreground">Valor: {data[hoveredIndex].value1}%</div>
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-full w-0 h-0 border-l-[6px] border-r-[6px] border-t-[6px] border-transparent" style={{ borderTopColor: 'rgb(8, 9, 10)' }} />
            </motion.div>
          )}
        </div>

        {/* Legend */}
        <div className="flex items-center justify-center gap-6 mt-6">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-primary" style={{ boxShadow: '0 0 8px rgba(255, 107, 53, 0.5)' }} />
            <span className="text-sm text-muted-foreground">Linha Principal</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-primary opacity-70" />
            <span className="text-sm text-muted-foreground">Linha Secundária</span>
          </div>
        </div>

        <p className="text-center text-sm text-muted-foreground mt-4">
          Crescimento médio de <span className="text-green-500 font-bold">+15%</span> ao mês
        </p>
      </div>
    </div>
  )
}
