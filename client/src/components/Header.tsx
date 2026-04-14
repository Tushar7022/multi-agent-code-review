type Status = 'ready' | 'running' | 'done'

interface HeaderProps {
    status?: Status
}

export default function Header({ status = 'ready' }: HeaderProps) {
    return (
        <header className="sticky top-0 z-50 flex items-center justify-between px-8 h-14 border-b border-slate-200/80"
            style={{
                background: 'linear-gradient(to right, rgba(245,244,255,0.92) 0%, rgba(240,244,255,0.92) 100%)',
                backdropFilter: 'blur(16px)'
            }}
        >
            {/* Logo */}
            <div className="flex items-center gap-3">
                <div
                    className="w-9 h-9 rounded-xl flex items-center justify-center text-white"
                    style={{
                        background: 'linear-gradient(135deg, #6c63ff 0%, #4e46e5 100%)',
                        boxShadow: '0 2px 12px rgba(108,99,255,0.4)',
                    }}
                >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="16 18 22 12 16 6" />
                        <polyline points="8 6 2 12 8 18" />
                    </svg>
                </div>
                <span className="text-[15px] font-semibold tracking-tight"
                    style={{ background: 'linear-gradient(135deg, #3730a3, #6c63ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}
                >
                    Multiagent Code Review
                </span>
            </div>

            {/* Right side — status indicator, no pill */}
            {(status === 'running' || status === 'done') && (
                <div className="flex items-center gap-2 text-[13px] font-medium"
                    style={{ color: status === 'done' ? '#16a34a' : '#6c63ff' }}
                >
                    <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse-dot" />
                    {status === 'running' ? 'Analyzing…' : 'Complete'}
                </div>
            )}
        </header>
    )
}