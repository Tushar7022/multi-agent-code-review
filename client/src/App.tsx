import { useState } from 'react'
import Header from './components/Header.tsx'
import CodeInput from './components/CodeInput.tsx'
import ProgressPanel from './components/ProgressPanel.tsx'
import { ReviewRequest } from './types.ts'

type AppState = 'idle' | 'streaming' | 'done'

const AGENTS = [
    { label: 'Security', color: 'text-violet-600', bg: 'bg-violet-50', border: 'border-violet-200', glow: 'rgba(124,58,237,0.15)' },
    { label: 'Performance', color: 'text-cyan-600', bg: 'bg-cyan-50', border: 'border-cyan-200', glow: 'rgba(8,145,178,0.15)' },
    { label: 'Maintainability', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', glow: 'rgba(5,150,105,0.15)' },
    { label: 'Synthesizer', color: 'text-indigo-600', bg: 'bg-indigo-50', border: 'border-indigo-200', glow: 'rgba(108,99,255,0.15)' },
]

export default function App() {
    const [appState, setAppState] = useState<AppState>('idle')
    const [request, setRequest] = useState<ReviewRequest | null>(null)

    function handleSubmit(req: ReviewRequest) {
        setRequest(req)
        setAppState('streaming')
    }

    function handleReset() {
        setRequest(null)
        setAppState('idle')
    }

    const headerStatus = appState === 'idle' ? 'ready' : appState === 'streaming' ? 'running' : 'done'

    return (
        <div className="min-h-screen flex flex-col" style={{ background: 'var(--bg-mesh)' }}>
            <Header status={headerStatus} />

            <main className="flex-1 flex flex-col items-center px-4 py-12">

                {/* ── Page 1: Landing ── */}
                {appState === 'idle' && (
                    <div className="w-full max-w-3xl animate-fade-in-up">
                        <div className="text-center mb-8">
                            <h1
                                className="text-[32px] font-semibold tracking-tight mb-3"
                                style={{
                                    background: 'linear-gradient(135deg, #312e81 0%, #6c63ff 50%, #818cf8 100%)',
                                    WebkitBackgroundClip: 'text',
                                    WebkitTextFillColor: 'transparent',
                                }}
                            >
                                AI-Powered Code Review
                            </h1>
                            <p className="text-slate-500 text-[15px] leading-relaxed">
                                Three specialized agents analyze your code in parallel — security, performance, and maintainability.
                            </p>
                        </div>

                        {/* Card with glow border */}
                        <div
                            className="rounded-2xl"
                            style={{
                                padding: '1.5px',
                                background: 'linear-gradient(135deg, rgba(108,99,255,0.35) 0%, rgba(129,140,248,0.2) 50%, rgba(165,180,252,0.35) 100%)',
                                boxShadow: '0 8px 40px rgba(108,99,255,0.12), 0 2px 8px rgba(0,0,0,0.04)',
                            }}
                        >
                            <div className="rounded-[14px] overflow-hidden">
                                <CodeInput onSubmit={handleSubmit} isLoading={false} />
                            </div>
                        </div>

                        {/* Agent pills */}
                        <div className="flex items-center justify-center gap-3 mt-6">
                            {AGENTS.map(({ label, color, bg, border, glow }) => (
                                <span
                                    key={label}
                                    className={`text-[12px] font-medium px-3 py-1 rounded-full border ${color} ${bg} ${border}`}
                                    style={{ boxShadow: `0 2px 8px ${glow}` }}
                                >
                                    {label}
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* ── Page 2: Results ── */}
                {(appState === 'streaming' || appState === 'done') && request && (
                    <div className="w-full max-w-4xl animate-fade-in-up">
                        <ProgressPanel
                            request={request}
                            onReset={handleReset}
                            onDone={() => setAppState('done')}
                        />
                    </div>
                )}

            </main>
        </div>
    )
}