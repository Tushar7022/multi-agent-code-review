import { useState, useRef, DragEvent } from 'react'
import { ReviewRequest, Language } from '../types.ts'

const LANGUAGES: { value: Language; label: string }[] = [
    { value: 'python', label: 'Python' },
    { value: 'javascript', label: 'JavaScript' },
]

const EXT_MAP: Record<string, Language> = {
    py: 'python', js: 'javascript', ts: 'javascript',
    jsx: 'javascript', tsx: 'javascript',
}

interface CodeInputProps {
    onSubmit: (req: ReviewRequest) => void
    isLoading?: boolean
}

export default function CodeInput({ onSubmit, isLoading = false }: CodeInputProps) {
    const [code, setCode] = useState('')
    const [lang, setLang] = useState<Language>('python')
    const [filename, setFilename] = useState<string | undefined>(undefined)
    const [isDragging, setIsDragging] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)

    function handleSubmit() {
        if (!code.trim() || isLoading) return
        onSubmit({ code, language: lang, filename })
    }

    function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') handleSubmit()
    }

    function readFile(file: File) {
        const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
        const detectedLang = EXT_MAP[ext]
        if (detectedLang) setLang(detectedLang)
        setFilename(file.name)

        const reader = new FileReader()
        reader.onload = e => setCode(e.target?.result as string ?? '')
        reader.readAsText(file)
    }

    function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0]
        if (file) readFile(file)
        e.target.value = ''
    }

    function handleDrop(e: DragEvent<HTMLDivElement>) {
        e.preventDefault()
        setIsDragging(false)
        const file = e.dataTransfer.files?.[0]
        if (file) readFile(file)
    }

    function handleDragOver(e: DragEvent<HTMLDivElement>) {
        e.preventDefault()
        setIsDragging(true)
    }

    function handleDragLeave() {
        setIsDragging(false)
    }

    function clearFile() {
        setCode('')
        setFilename(undefined)
    }

    const lineCount = code ? code.split('\n').length : 0
    const charCount = code.length

    return (
        <div
            className="w-full rounded-2xl overflow-hidden"
            style={{
                border: isDragging ? '1.5px solid #6c63ff' : '1.5px solid rgba(203,213,255,0.8)',
                boxShadow: isDragging
                    ? '0 0 0 4px rgba(108,99,255,0.12), 0 8px 40px rgba(108,99,255,0.15)'
                    : '0 4px 32px rgba(108,99,255,0.10), 0 1px 4px rgba(0,0,0,0.04)',
                background: '#ffffff',
                transition: 'box-shadow 0.2s ease, border-color 0.2s ease',
            }}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
        >

            {/* ── Card Header ── */}
            <div
                className="flex items-center justify-between px-6 py-4"
                style={{
                    background: 'linear-gradient(135deg, #f0eeff 0%, #e8eaff 50%, #eef3ff 100%)',
                    borderBottom: '1px solid rgba(203,213,255,0.6)',
                }}
            >
                {/* Title */}
                <div className="flex items-center gap-3">
                    <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center text-white flex-shrink-0"
                        style={{
                            background: 'linear-gradient(135deg, #6c63ff 0%, #4e46e5 100%)',
                            boxShadow: '0 4px 12px rgba(108,99,255,0.35)',
                        }}
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                            <polyline points="14 2 14 8 20 8" />
                            <line x1="10" y1="13" x2="14" y2="13" />
                            <line x1="8" y1="17" x2="16" y2="17" />
                        </svg>
                    </div>
                    <div>
                        <p className="text-[15px] font-semibold text-slate-800 leading-tight">AI Code Review</p>
                        <p className="text-[12px] text-indigo-400 mt-0.5">Powered by multi-agent analysis</p>
                    </div>
                </div>

                {/* Controls */}
                <div className="flex items-center gap-3">

                    {/* Upload button */}
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".py,.js,.ts,.jsx,.tsx"
                        className="hidden"
                        onChange={handleFileChange}
                    />
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isLoading}
                        className="flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-indigo-600 border transition-all duration-150 disabled:opacity-50"
                        style={{
                            background: 'linear-gradient(135deg, #ede9ff 0%, #e8eaff 100%)',
                            borderColor: 'rgba(139,92,246,0.25)',
                        }}
                        title="Upload a .py or .js/.ts file"
                    >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                            <polyline points="17 8 12 3 7 8" />
                            <line x1="12" y1="3" x2="12" y2="15" />
                        </svg>
                        Upload file
                    </button>

                    {/* Language selector */}
                    <div className="relative">
                        <select
                            value={lang}
                            onChange={e => setLang(e.target.value as Language)}
                            disabled={isLoading}
                            className="h-9 pl-3 pr-8 text-[13px] font-medium text-slate-700 border rounded-lg appearance-none outline-none cursor-pointer disabled:opacity-50 transition-all"
                            style={{
                                background: 'linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%)',
                                borderColor: 'rgba(139,92,246,0.25)',
                            }}
                        >
                            {LANGUAGES.map(l => (
                                <option key={l.value} value={l.value}>{l.label}</option>
                            ))}
                        </select>
                        <svg className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-indigo-400" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="6 9 12 15 18 9" />
                        </svg>
                    </div>
                </div>
            </div>

            {/* ── File loaded banner ── */}
            {filename && (
                <div
                    className="flex items-center justify-between px-6 py-2 text-[12px]"
                    style={{
                        background: 'linear-gradient(90deg, #ede9ff 0%, #eef3ff 100%)',
                        borderBottom: '1px solid rgba(203,213,255,0.5)',
                    }}
                >
                    <div className="flex items-center gap-2 text-indigo-600 font-medium">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                            <polyline points="14 2 14 8 20 8" />
                        </svg>
                        {filename}
                    </div>
                    <button
                        onClick={clearFile}
                        className="text-slate-400 hover:text-slate-600 transition-colors"
                    >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                    </button>
                </div>
            )}

            {/* ── Textarea ── */}
            <div className="relative">
                {/* Left gradient accent bar */}
                <div
                    className="absolute top-0 left-0 bottom-0 w-[3px] pointer-events-none"
                    style={{ background: 'linear-gradient(to bottom, #6c63ff, #818cf8, #a5b4fc)' }}
                />

                {isDragging && (
                    <div className="absolute inset-0 z-10 flex items-center justify-center rounded-none pointer-events-none"
                        style={{ background: 'rgba(237,233,255,0.85)', backdropFilter: 'blur(2px)' }}
                    >
                        <div className="flex flex-col items-center gap-2 text-indigo-500">
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                <polyline points="17 8 12 3 7 8" />
                                <line x1="12" y1="3" x2="12" y2="15" />
                            </svg>
                            <span className="text-[14px] font-semibold">Drop your file here</span>
                        </div>
                    </div>
                )}

                <textarea
                    value={code}
                    onChange={e => setCode(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isLoading}
                    spellCheck={false}
                    autoComplete="off"
                    placeholder="Paste your code here, or drag & drop a file..."
                    className="w-full min-h-[360px] px-6 py-5 pl-7 font-mono text-[13.5px] leading-relaxed text-slate-800 placeholder-slate-300 placeholder:font-sans placeholder:text-[14px] bg-white border-none outline-none resize-y disabled:opacity-60 disabled:cursor-not-allowed"
                />
            </div>

            {/* ── Footer ── */}
            <div
                className="flex items-center justify-between px-6 py-3"
                style={{
                    background: 'linear-gradient(to right, #f8f7ff, #f0f4ff)',
                    borderTop: '1px solid rgba(203,213,255,0.5)',
                }}
            >
                <span className="text-[12px] font-mono text-slate-400">
                    {code
                        ? `${lineCount} lines · ${charCount} chars`
                        : '⌘ + Enter to analyze · or drag & drop a file'
                    }
                </span>

                <button
                    onClick={handleSubmit}
                    disabled={!code.trim() || isLoading}
                    className="inline-flex items-center gap-2 px-5 h-10 rounded-xl text-[14px] font-semibold text-white transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 hover:-translate-y-px active:translate-y-0"
                    style={{
                        background: 'linear-gradient(135deg, #6c63ff 0%, #4e46e5 100%)',
                        boxShadow: '0 2px 12px rgba(108,99,255,0.4)',
                    }}
                >
                    {isLoading ? (
                        <>
                            <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                            </svg>
                            Analyzing…
                        </>
                    ) : (
                        <>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                            </svg>
                            Analyze Code
                        </>
                    )}
                </button>
            </div>
        </div>
    )
}