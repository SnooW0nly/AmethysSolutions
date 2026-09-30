'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowLeft, faCheck, faCalendar, faTag } from '@fortawesome/free-solid-svg-icons'
import { getChangelogById, getTypeIcon, getTypeColor, getTypeLabel, formatDate } from '@/lib/changelogs'

export default function ChangelogDetailPage() {
    const params = useParams()
    const id = params?.id as string
    const changelog = getChangelogById(id)

    if (!changelog) {
        return (
            <div className="min-h-screen flex items-center justify-center text-foreground/60">
                Changelog não encontrado.
            </div>
        )
    }

    return (
        <main className="min-h-screen py-20 px-4 md:px-6 relative overflow-hidden">
            {/* Background Glow */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-primary/5 blur-[120px] rounded-full pointer-events-none" />

            <div className="max-w-3xl mx-auto relative z-10">
                {/* Back Button */}
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="mb-8"
                >
                    <Link
                        href="/changelogs"
                        className="inline-flex items-center gap-2 text-sm text-foreground/60 hover:text-primary transition-colors group"
                    >
                        <FontAwesomeIcon icon={faArrowLeft} className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                        Voltar para lista
                    </Link>
                </motion.div>

                {/* Content */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="space-y-8"
                >
                    {/* Header */}
                    <div className="space-y-4">
                        <div className="flex items-center gap-3 flex-wrap">
                            <span className="text-sm font-bold text-primary bg-primary/10 px-3 py-1 rounded-full border border-primary/20">
                                v{changelog.version}
                            </span>
                            <span className={`text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider ${getTypeColor(changelog.type)}`}>
                                {getTypeLabel(changelog.type)}
                            </span>
                        </div>

                        <h1 className="text-4xl md:text-5xl font-bold text-foreground">
                            {changelog.title}
                        </h1>

                        <div className="flex items-center gap-4 text-sm text-foreground/60">
                            <div className="flex items-center gap-2">
                                <FontAwesomeIcon icon={faCalendar} className="w-4 h-4" />
                                <span>{formatDate(changelog.date)}</span>
                            </div>
                        </div>
                    </div>

                    <div className="h-px w-full bg-foreground/10" />

                    {/* Description */}
                    <div className="prose prose-invert max-w-none">
                        <p className="text-lg text-foreground/80 leading-relaxed">
                            {changelog.description}
                        </p>
                    </div>

                    {/* Changes */}
                    <div className="space-y-4">
                        <h3 className="text-xl font-semibold text-foreground flex items-center gap-2">
                            <FontAwesomeIcon icon={faTag} className="w-4 h-4 text-primary" />
                            Alterações Realizadas
                        </h3>
                        <div className="bg-card/50 backdrop-blur-sm border border-foreground/5 rounded-2xl p-6">
                            <ul className="space-y-4">
                                {changelog.changes.map((change, i) => (
                                    <li key={i} className="flex items-start gap-3 text-foreground/70">
                                        <div className="mt-1.5 w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                                            <FontAwesomeIcon icon={faCheck} className="w-3 h-3 text-primary" />
                                        </div>
                                        <span className="leading-relaxed">{change}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </motion.div>
            </div>
        </main>
    )
}
