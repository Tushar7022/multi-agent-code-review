import { useState } from 'react'
import { Issue } from '../types.ts'
import SeverityBadge from './SeverityBadge.tsx'
import AgentBadge from './AgentBadge.tsx'

interface Props {
    issue: Issue
    index: number
}

export default function IssueCard({ issue, index }: Props) {
    const [expanded, setExpanded] = useState(false)

    return (
        <div
            className="rounded-xl overflow-hidden transition-all duration-200"
            style={{
                background: '#ffffff',
                border: '1px solid rgba(203,213,255,0.7)',
                boxShadow: '0 2px 12px rgba(108,99,255,0.06)',
                animationDelay: `${index * 60}ms`,
            }}
        >
            {/* ── Header row ── */}
            <button
                className="w-full text-left px-5 py-4 flex items-start justify-between gap-4"
                onClick={() => setExpanded(e => !e)}
            >
                <div className="flex flex-col gap-2 flex-1 min-w-0">
                    {/* Badges */}
                    <div className="flex items-center gap-2 flex-wrap">
                        <SeverityBadge severity={issue.severity} />
                        <AgentBadge agent={issue.agent} />
                        {issue.agent_agreement.length > 1 && (
                            <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200">
                                {issue.agent_agreement.length} agents agree
                            </span>
                        )}
                    </div>

                    {/* Issue type + location */}
                    <div className="flex items-center gap-2 min-w-0">
                        <span className="text-[14px] font-semibold text-slate-800 truncate">
                            {issue.issue_type}
                        </span>
                        <span className="text-[12px] font-mono text-slate-400 flex-shrink-0">
                            {issue.file}:{issue.line}
                        </span>
                    </div>
                </div>

                {/* Chevron */}
                <svg
                    className="flex-shrink-0 text-slate-400 transition-transform duration-200 mt-1"
                    style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
                    width="16" height="16" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
                >
                    <polyline points="6 9 12 15 18 9" />
                </svg>
            </button>

            {/* ── Expanded content ── */}
            {expanded && (
                <div
                    className="px-5 pb-5 flex flex-col gap-4 animate-fade-in-up"
                    style={{ borderTop: '1px solid rgba(203,213,255,0.5)' }}
                >
                    {/* Evidence */}
                    {issue.evidence && (
                        <div>
                            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                                Evidence
                            </p>
                            <pre
                                className="text-[12px] leading-relaxed p-3 rounded-lg overflow-x-auto"
                                style={{ background: '#f8f7ff', border: '1px solid rgba(203,213,255,0.5)', color: '#4338ca' }}
                            >
                                {issue.evidence}
                            </pre>
                        </div>
                    )}

                    {/* Reasoning */}
                    {issue.llm_reasoning && (
                        <div>
                            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                                Analysis
                            </p>
                            <p className="text-[13px] text-slate-600 leading-relaxed">
                                {issue.llm_reasoning}
                            </p>
                        </div>
                    )}

                    {/* Suggested fix */}
                    {issue.suggested_fix && (
                        <div>
                            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                                Suggested Fix
                            </p>
                            <pre
                                className="text-[12px] leading-relaxed p-3 rounded-lg overflow-x-auto"
                                style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534' }}
                            >
                                {issue.suggested_fix}
                            </pre>
                        </div>
                    )}

                    {/* Cross domain notes */}
                    {issue.cross_domain_notes && (
                        <div
                            className="flex items-start gap-2 p-3 rounded-lg text-[12px] text-indigo-600"
                            style={{ background: '#ede9ff', border: '1px solid #c4b5fd' }}
                        >
                            <svg className="flex-shrink-0 mt-0.5" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                            </svg>
                            <span>{issue.cross_domain_notes}</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}