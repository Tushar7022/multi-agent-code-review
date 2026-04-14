import { SeverityLevel } from '../types.ts'

const CONFIG: Record<SeverityLevel, { label: string; color: string; bg: string; border: string; glow: string }> = {
    critical: { label: 'Critical', color: '#dc2626', bg: '#fef2f2', border: '#fecaca', glow: 'rgba(220,38,38,0.15)' },
    high: { label: 'High', color: '#ea580c', bg: '#fff7ed', border: '#fed7aa', glow: 'rgba(234,88,12,0.15)' },
    medium: { label: 'Medium', color: '#ca8a04', bg: '#fefce8', border: '#fde68a', glow: 'rgba(202,138,4,0.15)' },
    low: { label: 'Low', color: '#4b6bfb', bg: '#eff3ff', border: '#c7d2fe', glow: 'rgba(75,107,251,0.15)' },
}

interface Props { severity: SeverityLevel }

export default function SeverityBadge({ severity }: Props) {
    const c = CONFIG[severity]
    return (
        <span
            className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full"
            style={{ color: c.color, background: c.bg, border: `1px solid ${c.border}`, boxShadow: `0 1px 6px ${c.glow}` }}
        >
            <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: c.color }} />
            {c.label}
        </span>
    )
}