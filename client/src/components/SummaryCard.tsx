import { useState } from 'react'

interface Props {
    summary: string
    originalCode: string
    fixedCode: string
    language: string
}

export default function SummaryCard({ summary, originalCode, fixedCode, language }: Props) {
    const [showDiff, setShowDiff] = useState(false)

    return (
        <div
            className="rounded-xl overflow-hidden"
            style={{
                background: '#ffffff',
                border: '1px solid rgba(203,213,255,0.7)',
                boxShadow: '0 2px 12px rgba(108,99,255,0.06)',
            }}
        >
            {/* ── Header ── */}
            <div
                className="px-5 py-4 flex items-center gap-3"
                style={{
                    background: 'linear-gradient(135deg, #f0eeff 0%, #e8eaff 50%, #eef3ff 100%)',
                    borderBottom: '1px solid rgba(203,213,255,0.5)',
                }}
            >
                <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-white flex-shrink-0"
                    style={{ background: 'linear-gradient(135deg, #6c63ff 0%, #4e46e5 100%)', boxShadow: '0 2px 8px rgba(108,99,255,0.3)' }}
                >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                    </svg>
                </div>
                <div>
                    <p className="text-[14px] font-semibold text-slate-800">Synthesis Summary</p>
                    <p className="text-[11px] text-indigo-400">Final report from all agents</p>
                </div>
            </div>

            {/* ── Summary text ── */}
            <div className="px-5 py-4">
                <p className="text-[14px] text-slate-600 leading-relaxed">{summary}</p>
            </div>

            {/* ── Code diff toggle ── */}
            {fixedCode && (
                <div style={{ borderTop: '1px solid rgba(203,213,255,0.5)' }}>
                    <button
                        onClick={() => setShowDiff(d => !d)}
                        className="w-full flex items-center justify-between px-5 py-3 text-[13px] font-medium text-indigo-600 hover:bg-indigo-50 transition-colors duration-150"
                    >
                        <div className="flex items-center gap-2">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="16 18 22 12 16 6" />
                                <polyline points="8 6 2 12 8 18" />
                            </svg>
                            {showDiff ? 'Hide' : 'Show'} Original vs Fixed Code
                        </div>
                        <svg
                            className="transition-transform duration-200"
                            style={{ transform: showDiff ? 'rotate(180deg)' : 'rotate(0deg)' }}
                            width="14" height="14" viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
                        >
                            <polyline points="6 9 12 15 18 9" />
                        </svg>
                    </button>

                    {/* ── Side by side diff ── */}
                    {showDiff && (
                        <div className="animate-fade-in-up" style={{ borderTop: '1px solid rgba(203,213,255,0.4)' }}>
                            {/* Column headers */}
                            <div className="grid grid-cols-2 divide-x divide-slate-200">
                                <div className="px-4 py-2 flex items-center gap-2"
                                    style={{ background: '#fff7f7' }}
                                >
                                    <span className="w-2 h-2 rounded-full bg-red-400" />
                                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Original</span>
                                    <span className="text-[11px] font-mono text-slate-400 ml-auto">{language}</span>
                                </div>
                                <div className="px-4 py-2 flex items-center gap-2"
                                    style={{ background: '#f0fdf4' }}
                                >
                                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Fixed</span>
                                    <span className="text-[11px] font-mono text-slate-400 ml-auto">{language}</span>
                                </div>
                            </div>

                            {/* Code panels */}
                            <div className="grid grid-cols-2 divide-x divide-slate-200">
                                <div className="relative">
                                    <pre
                                        className="text-[12px] font-mono leading-relaxed p-4 overflow-x-auto overflow-y-auto"
                                        style={{ maxHeight: '480px', background: '#fffafa', color: '#64748b' }}
                                    >
                                        {originalCode}
                                    </pre>
                                    {/* Red left bar */}
                                    <div className="absolute top-0 left-0 bottom-0 w-[3px]" style={{ background: 'linear-gradient(to bottom, #f87171, #fca5a5)' }} />
                                </div>
                                <div className="relative">
                                    <pre
                                        className="text-[12px] font-mono leading-relaxed p-4 overflow-x-auto overflow-y-auto"
                                        style={{ maxHeight: '480px', background: '#fafffe', color: '#64748b' }}
                                    >
                                        {fixedCode}
                                    </pre>
                                    {/* Green left bar */}
                                    <div className="absolute top-0 left-0 bottom-0 w-[3px]" style={{ background: 'linear-gradient(to bottom, #34d399, #6ee7b7)' }} />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}