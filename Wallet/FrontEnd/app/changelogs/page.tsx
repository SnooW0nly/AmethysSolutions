'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faWandSparkles, faArrowRight, faCheck } from '@fortawesome/free-solid-svg-icons'
import { changelogs, getTypeIcon, getTypeColor, getTypeLabel, formatDate } from '@/lib/changelogs'

export default function ChangelogsPage() {
  return (
    <main className="min-h-screen py-20 px-4 md:px-6 relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-primary/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="max-w-4xl mx-auto relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-16 space-y-4"
        >
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-foreground">
            Changelogs
          </h1>
          <p className="text-lg text-foreground/60 max-w-2xl mx-auto">
            Acompanhe a evolução do Amethys Wallet. Todas as atualizações, melhorias e novidades em um só lugar.
          </p>
        </motion.div>

        {/* Changelog List */}
        <div className="space-y-12">
          {changelogs.map((changelog, index) => (
            <motion.div
              key={changelog.version}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="relative"
            >
              <Link href={`/changelogs/${changelog.version}`} className="block group cursor-pointer">
                <div className="flex flex-col md:flex-row gap-8 items-start p-4 -mx-4 rounded-2xl transition-colors hover:bg-foreground/5">

                  {/* Date Column */}
                  <div className="md:w-32 flex-shrink-0 pt-2">
                    <span className="text-sm font-medium text-foreground/40 font-mono group-hover:text-foreground/60 transition-colors">
                      {formatDate(changelog.date)}
                    </span>
                  </div>

                  {/* Content */}
                  <div className="flex-1 space-y-4">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-2">
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="text-sm font-bold text-primary">
                            v{changelog.version}
                          </span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${getTypeColor(changelog.type)}`}>
                            {getTypeLabel(changelog.type)}
                          </span>
                        </div>
                        <h3 className="text-2xl font-bold text-foreground group-hover:text-primary transition-colors flex items-center gap-2">
                          {changelog.title}
                          <FontAwesomeIcon icon={faArrowRight} className="w-4 h-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                        </h3>
                      </div>
                    </div>

                    <p className="text-foreground/70 text-base leading-relaxed max-w-2xl">
                      {changelog.description}
                    </p>

                    {/* Changes List */}
                    {changelog.changes && changelog.changes.length > 0 && (
                      <div className="pt-2">
                        <ul className="space-y-3">
                          {changelog.changes.slice(0, 3).map((change, i) => (
                            <li key={i} className="flex items-start gap-3 text-sm text-foreground/60">
                              <FontAwesomeIcon icon={faCheck} className="w-3.5 h-3.5 mt-1 text-primary/60" />
                              <span className="line-clamp-1">{change}</span>
                            </li>
                          ))}
                          {changelog.changes.length > 3 && (
                            <li className="text-xs text-primary font-medium pt-1">
                              Ver mais {changelog.changes.length - 3} alterações...
                            </li>
                          )}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </Link>

              {/* Separator */}
              {index < changelogs.length - 1 && (
                <div className="mt-12 border-b border-foreground/5" />
              )}
            </motion.div>
          ))}
        </div>

        {/* Footer Note */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: changelogs.length * 0.1 }}
          className="mt-20 text-center"
        >
        </motion.div>
      </div>
    </main>
  )
}
