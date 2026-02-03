'use client'

import ReactMarkdown from 'react-markdown'
import { FileText, Download, Copy, Check } from 'lucide-react'
import { useState } from 'react'

interface ReportPanelProps {
  markdown: string
}

export default function ReportPanel({ markdown }: ReportPanelProps) {
  const [copied, setCopied] = useState(false)
  
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(markdown)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }
  
  const handleDownload = () => {
    const blob = new Blob([markdown], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'investigation-report.md'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (!markdown) {
    return (
      <div className="h-full flex items-center justify-center text-text-muted text-sm">
        <div className="text-center">
          <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>Report will be generated at the end of investigation</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header with actions */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <FileText className="h-4 w-4 text-accent-purple" />
          Investigation Report
        </h3>
        <div className="flex gap-1">
          <button
            onClick={handleCopy}
            className="p-1.5 bg-bg-tertiary hover:bg-bg-elevated border border-border-default rounded text-text-secondary hover:text-text-primary transition-colors"
            title="Copy to clipboard"
          >
            {copied ? (
              <Check className="h-4 w-4 text-accent-green" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </button>
          <button
            onClick={handleDownload}
            className="p-1.5 bg-bg-tertiary hover:bg-bg-elevated border border-border-default rounded text-text-secondary hover:text-text-primary transition-colors"
            title="Download as Markdown"
          >
            <Download className="h-4 w-4" />
          </button>
        </div>
      </div>
      
      {/* Report content */}
      <div className="flex-1 overflow-y-auto bg-bg-tertiary border border-border-default rounded-lg p-4">
        <article className="prose prose-invert prose-sm max-w-none
          prose-headings:text-text-primary prose-headings:font-semibold
          prose-h1:text-xl prose-h1:border-b prose-h1:border-border-default prose-h1:pb-2
          prose-h2:text-lg prose-h2:mt-6 prose-h2:mb-3
          prose-h3:text-base prose-h3:mt-4
          prose-p:text-text-secondary prose-p:leading-relaxed
          prose-strong:text-text-primary
          prose-ul:text-text-secondary
          prose-li:marker:text-accent-cyan
          prose-table:text-sm
          prose-th:bg-bg-elevated prose-th:text-text-primary prose-th:font-medium prose-th:p-2
          prose-td:p-2 prose-td:border-border-default
          prose-hr:border-border-default
          prose-code:text-accent-cyan prose-code:bg-bg-primary prose-code:px-1 prose-code:rounded
          prose-pre:bg-bg-primary prose-pre:border prose-pre:border-border-default
        ">
          <ReactMarkdown>{markdown}</ReactMarkdown>
        </article>
      </div>
    </div>
  )
}
