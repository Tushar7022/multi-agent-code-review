import { useEffect, useRef, useState } from 'react'
import { Issue, Language, ReviewRequest, StreamEvent } from '../types.ts'
import IssueCard from './IssueCard.tsx'
import SummaryCard from './SummaryCard.tsx'

interface Props {
    request: ReviewRequest
    onReset: () => void
    onDone: () => void
}

type StepStatus = 'waiting' | 'running' | 'done' | 'error'

interface Step {
    id: string
    label: string
    status: StepStatus
    detail?: string
}

const INITIAL_STEPS: Step[] = [
    { id: 'language', label: 'Detecting language', status: 'waiting' },
    { id: 'tools', label: 'Running static analysis', status: 'waiting' },
    { id: 'security', label: 'Security agent', status: 'waiting' },
    { id: 'performance', label: 'Performance agent', status: 'waiting' },
    { id: 'maintainability', label: 'Maintainability agent', status: 'waiting' },
    { id: 'synthesizer', label: 'Synthesizer merging results', status: 'waiting' },
]

function updateStep(steps: Step[], id: string, patch: Partial<Step>): Step[] {
    return steps.map(s => s.id === id ? { ...s, ...patch } : s)
}

export default function ProgressPanel({ request, onReset, onDone }: Props) {
    const [steps, setSteps] = useState<Step[]>(INITIAL_STEPS)
    const [securityIssues, setSecurityIssues] = useState<Issue[]>([])
    const [perfIssues, setPerfIssues] = useState<Issue[]>([])
    const [maintIssues, setMaintIssues] = useState<Issue[]>([])
    const [finalIssues, setFinalIssues] = useState<Issue[]>([])
    const [summary, setSummary] = useState('')
    const [fixedCode, setFixedCode] = useState('')
    const [language, setLanguage] = useState<Language>('python')
    const [phase, setPhase] = useState<'connecting' | 'streaming' | 'done' | 'error'>('connecting')
    const [errorMsg, setErrorMsg] = useState('')
    const esRef = useRef<EventSource | null>(null)

    useEffect(() => {
        // build query params — POST via SSE workaround using fetch + ReadableStream
        const ctrl = new AbortController()

        async function startStream() {
            try {
                const res = await fetch('/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(request),
                    signal: ctrl.signal,
                })

                if (!res.ok) throw new Error(`Server error ${res.status}`)
                if (!res.body) throw new Error('No response body')

                setPhase('streaming')

                // step 1 immediately running
                setSteps(s => updateStep(s, 'language', { status: 'running' }))

                const reader = res.body.getReader()
                const decoder = new TextDecoder()
                let buffer = ''

                while (true) {
                    const { done, value } = await reader.read()
                    if (done) break

                    buffer += decoder.decode(value, { stream: true })
                    const lines = buffer.split('\n')
                    buffer = lines.pop() ?? ''

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue
                        const raw = line.slice(6).trim()
                        if (!raw) continue

                        let evt: StreamEvent
                        try { evt = JSON.parse(raw) } catch { continue }

                        handleEvent(evt)
                    }
                }

            } catch (e: unknown) {
                if ((e as Error).name === 'AbortError') return
                setPhase('error')
                setErrorMsg((e as Error).message ?? 'Unknown error')
            }
        }

        startStream()
        return () => ctrl.abort()
    }, [])   // eslint-disable-line react-hooks/exhaustive-deps

    function handleEvent(evt: StreamEvent) {
        switch (evt.event) {
            case 'language':
                setLanguage(evt.language)
                setSteps(s => {
                    let next = updateStep(s, 'language', { status: 'done', detail: evt.language })
                    next = updateStep(next, 'tools', { status: 'running' })
                    return next
                })
                break

            case 'tools_done':
                setSteps(s => {
                    let next = updateStep(s, 'tools', { status: 'done' })
                    next = updateStep(next, 'security', { status: 'running' })
                    next = updateStep(next, 'performance', { status: 'running' })
                    next = updateStep(next, 'maintainability', { status: 'running' })
                    return next
                })
                break

            case 'security_done':
                setSecurityIssues(evt.issues)
                setSteps(s => updateStep(s, 'security', {
                    status: 'done',
                    detail: `${evt.issues.length} issue${evt.issues.length !== 1 ? 's' : ''} found`,
                }))
                break

            case 'performance_done':
                setPerfIssues(evt.issues)
                setSteps(s => updateStep(s, 'performance', {
                    status: 'done',
                    detail: `${evt.issues.length} issue${evt.issues.length !== 1 ? 's' : ''} found`,
                }))
                break

            case 'maintainability_done':
                setMaintIssues(evt.issues)
                setSteps(s => updateStep(s, 'maintainability', {
                    status: 'done',
                    detail: `${evt.issues.length} issue${evt.issues.length !== 1 ? 's' : ''} found`,
                }))
                // all 3 done — synthesizer starts
                setSteps(s => updateStep(s, 'synthesizer', { status: 'running' }))
                break

            case 'synthesis_done':
                setFinalIssues(evt.issues)
                setSummary(evt.summary)
                setFixedCode(evt.fixed_code ?? '')
                setSecurityIssues([])
                setPerfIssues([])
                setMaintIssues([])
                setSteps(s => updateStep(s, 'synthesizer', {
                    status: 'done',
                    detail: `${evt.issues.length} total issues`,
                }))
                break

            case 'done':
                // fetch fixed_code — not in SSE, pull from full response later
                // for now mark complete
                setPhase('done')
                onDone()
                break
        }
    }

    // issues to show during streaming — pre-synthesis per-agent results
    const streamingIssues = [...securityIssues, ...perfIssues, ...maintIssues]
    // after synthesis — use final merged list
    const displayIssues = finalIssues.length > 0 ? finalIssues : streamingIssues

    const criticalCount = displayIssues.filter(i => i.severity === 'critical').length
    const highCount = displayIssues.filter(i => i.severity === 'high').length

    return (
        <div className="flex flex-col gap-6">

            {/* ── Top bar ── */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <button
                        onClick={onReset}
                        className="flex items-center gap-1.5 text-[13px] text-slate-400 hover:text-slate-600 transition-colors"
                    >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="15 18 9 12 15 6" />
                        </svg>
                        Back
                    </button>
                    <span className="text-slate-300">·</span>
                    <span className="text-[13px] text-slate-400 font-mono">
                        {request.filename ?? 'submitted code'}
                    </span>
                </div>

                {phase === 'done' && (
                    <div className="flex items-center gap-2">
                        {criticalCount > 0 && (
                            <span className="text-[12px] font-semibold px-2.5 py-1 rounded-full bg-red-50 text-red-600 border border-red-200">
                                {criticalCount} critical
                            </span>
                        )}
                        {highCount > 0 && (
                            <span className="text-[12px] font-semibold px-2.5 py-1 rounded-full bg-orange-50 text-orange-600 border border-orange-200">
                                {highCount} high
                            </span>
                        )}
                        <span className="text-[12px] font-semibold px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-600 border border-indigo-200">
                            {displayIssues.length} total issues
                        </span>
                    </div>
                )}
            </div>

            {/* ── Step tracker ── */}
            <div
                className="rounded-2xl overflow-hidden"
                style={{
                    background: '#ffffff',
                    border: '1px solid rgba(203,213,255,0.7)',
                    boxShadow: '0 2px 12px rgba(108,99,255,0.06)',
                }}
            >
                {/* Header */}
                <div
                    className="px-5 py-3 flex items-center gap-2"
                    style={{
                        background: 'linear-gradient(135deg, #f0eeff 0%, #e8eaff 50%, #eef3ff 100%)',
                        borderBottom: '1px solid rgba(203,213,255,0.5)',
                    }}
                >
                    {phase === 'connecting' && (
                        <svg className="animate-spin text-indigo-400" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                        </svg>
                    )}
                    {phase === 'streaming' && (
                        <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse-dot-fast" />
                    )}
                    {phase === 'done' && (
                        <svg className="text-emerald-500" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                        </svg>
                    )}
                    {phase === 'error' && (
                        <svg className="text-red-400" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
                        </svg>
                    )}
                    <span className="text-[13px] font-semibold text-slate-700">
                        {phase === 'connecting' && 'Connecting to agents…'}
                        {phase === 'streaming' && 'Analysis in progress…'}
                        {phase === 'done' && 'Analysis complete'}
                        {phase === 'error' && 'Something went wrong'}
                    </span>
                </div>

                {/* Steps */}
                <div className="px-5 py-4 flex flex-col gap-3">
                    {phase === 'error' ? (
                        <div className="text-[13px] text-red-500 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                            {errorMsg || 'Failed to connect to backend. Make sure the server is running on port 8000.'}
                        </div>
                    ) : (
                        steps.map((step, i) => (
                            <div key={step.id} className="flex items-center gap-3">
                                {/* Step icon */}
                                <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
                                    {step.status === 'waiting' && (
                                        <span className="w-2 h-2 rounded-full bg-slate-200" />
                                    )}
                                    {step.status === 'running' && (
                                        <svg className="animate-spin text-indigo-400" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                                        </svg>
                                    )}
                                    {step.status === 'done' && (
                                        <div className="w-5 h-5 rounded-full flex items-center justify-center"
                                            style={{ background: 'linear-gradient(135deg, #34d399, #059669)' }}
                                        >
                                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                                <polyline points="20 6 9 17 4 12" />
                                            </svg>
                                        </div>
                                    )}
                                    {step.status === 'error' && (
                                        <span className="w-5 h-5 rounded-full bg-red-100 flex items-center justify-center text-red-500 text-[10px] font-bold">✕</span>
                                    )}
                                </div>

                                {/* Connector line */}
                                <div className="flex-1 flex items-center gap-3">
                                    <span
                                        className="text-[13px] font-medium"
                                        style={{
                                            color: step.status === 'waiting' ? '#94a3b8'
                                                : step.status === 'running' ? '#6c63ff'
                                                    : step.status === 'done' ? '#1e293b'
                                                        : '#ef4444'
                                        }}
                                    >
                                        {step.label}
                                    </span>
                                    {step.detail && (
                                        <span className="text-[12px] text-slate-400 font-mono">{step.detail}</span>
                                    )}
                                    {step.status === 'running' && (
                                        <span className="text-[11px] text-indigo-400 animate-pulse-dot-fast">running…</span>
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* ── Live issues (stream as they arrive) ── */}
            {displayIssues.length > 0 && (
                <div className="flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                        <h2 className="text-[15px] font-semibold text-slate-700">
                            {phase === 'done' ? 'Issues' : 'Issues (live)'}
                        </h2>
                        <span className="text-[12px] text-slate-400">{displayIssues.length} found</span>
                    </div>

                    {/* Group by severity */}
                    {(['critical', 'high', 'medium', 'low'] as const).map(severity => {
                        const group = displayIssues.filter(i => i.severity === severity)
                        if (!group.length) return null
                        return (
                            <div key={severity} className="flex flex-col gap-2">
                                {group.map((issue, idx) => (
                                    <div key={idx} className="animate-fade-in-up" style={{ animationDelay: `${idx * 40}ms` }}>
                                        <IssueCard issue={issue} index={idx} />
                                    </div>
                                ))}
                            </div>
                        )
                    })}
                </div>
            )}

            {/* ── Summary + code diff — only after done ── */}
            {phase === 'done' && summary && (
                <div className="animate-fade-in-up">
                    <SummaryCard
                        summary={summary}
                        originalCode={request.code}
                        fixedCode={fixedCode}
                        language={language}
                    />
                </div>
            )}

            {/* ── Review another button ── */}
            {phase === 'done' && (
                <div className="flex justify-center pb-8 animate-fade-in-up">
                    <button
                        onClick={onReset}
                        className="inline-flex items-center gap-2 px-6 h-11 rounded-xl text-[14px] font-semibold text-white transition-all duration-200 hover:opacity-90 hover:-translate-y-px"
                        style={{
                            background: 'linear-gradient(135deg, #6c63ff 0%, #4e46e5 100%)',
                            boxShadow: '0 2px 12px rgba(108,99,255,0.4)',
                        }}
                    >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="15 18 9 12 15 6" />
                        </svg>
                        Review Another File
                    </button>
                </div>
            )}
        </div>
    )
}