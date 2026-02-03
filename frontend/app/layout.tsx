import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Agentic Fraud Investigation',
  description: 'LangGraph-powered fraud ring detection with adaptive graph expansion',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg-primary text-text-primary antialiased">
        {children}
      </body>
    </html>
  )
}
