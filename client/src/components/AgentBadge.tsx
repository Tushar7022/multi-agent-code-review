import { AgentType } from '../types.ts'

const CONFIG: Record<AgentType, { label: string; color: string; bg: string; border: string }> = {
    security: { label: 'Security', color: '#7c3aed', bg: '#f3eeff', border: '#ddd6fe' },
    performance: { label: 'Performance', color: '#0891b2', bg: '#ecfeff', border: '#a5f3fc' },
    maintainability: { label: 'Maintainability', color: '#059669', bg: '#ecfdf5', border: '#a7f3d0' },
    synthesizer: { label: 'Synthesizer', color: '#6c63ff', bg: '#ede9ff', border: '#c4b5fd' },
}

interface Props { agent: AgentType }

export default function AgentBadge({ agent }: Props) {
    const c = CONFIG[agent]
    return (
        <span
            className="inline-flex items-center text-[11px] font-medium px-2.5 py-0.5 rounded-full"
            style={{ color: c.color, background: c.bg, border: `1px solid ${c.border}` }}
        >
            {c.label}
        </span>
    )
}