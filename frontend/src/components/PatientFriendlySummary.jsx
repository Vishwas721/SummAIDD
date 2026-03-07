import { useState, useEffect } from 'react'
import axios from 'axios'
import { Sparkles, Loader2, AlertTriangle, Printer } from 'lucide-react'
import { cn } from '../lib/utils'
import { logExportedPdf } from '../utils/auditLogger'

/**
 * PatientFriendlySummary - Isolated component for patient-friendly summary view
 * Epic 4.3: Renders simple, legible summary + empty state + print functionality
 * 
 * Props:
 * - patientId: string - patient identifier
 * - isVisible: boolean - whether to show this component
 */
export function PatientFriendlySummary({ patientId, isVisible }) {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Epic 4.3: Auto-fetch when component becomes visible
  useEffect(() => {
    if (isVisible && patientId) {
      fetchSummary()
    }
  }, [isVisible, patientId])

  const fetchSummary = async () => {
    if (!patientId) return
    setLoading(true)
    setError(null)
    try {
      const url = `${import.meta.env.VITE_API_URL}/summary/patient-friendly/${encodeURIComponent(patientId)}`
      const response = await axios.get(url)
      setSummary(response.data || null)
    } catch (e) {
      if (e.response?.status === 404) {
        // Summary doesn't exist yet - this is expected, not an error
        setSummary(null)
      } else {
        console.error('Fetch patient-friendly summary error', e)
        setError(e.response?.data?.detail || e.message || 'Failed to load patient summary')
        setSummary(null)
      }
    } finally {
      setLoading(false)
    }
  }

  const generateSummary = async () => {
    if (!patientId) return
    setLoading(true)
    setError(null)
    try {
      const url = `${import.meta.env.VITE_API_URL}/summary/patient-friendly/${encodeURIComponent(patientId)}`
      const response = await axios.post(url, { language: 'English' })
      setSummary(response.data || null)
    } catch (e) {
      console.error('Generate patient-friendly summary error', e)
      setError(e.response?.data?.detail || e.message || 'Failed to generate patient summary')
      setSummary(null)
    } finally {
      setLoading(false)
    }
  }

  const handlePrint = () => {
    if (!summary) return
    const { condition_explanation, current_status, next_steps } = summary
    
    // Epic 4.1: Log exported PDF for WORM compliance
    logExportedPdf(patientId, {
      type: 'patient_friendly_summary',
      sections: ['condition_explanation', 'current_status', 'next_steps'],
      export_method: 'print'
    })
    
    const content = `
      <!DOCTYPE html>
      <html lang="en">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>Patient Summary</title>
          <style>
            @media print {
              * {
                margin: 0;
                padding: 0;
              }
              body {
                margin: 0;
                padding: 0.5in;
              }
            }
            body {
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
              max-width: 8.5in;
              padding: 0.5in;
              margin: 0 auto;
              color: #1f2937;
              line-height: 1.6;
              background: white;
            }
            h1 {
              font-size: 24px;
              font-weight: 700;
              color: #1e40af;
              margin-bottom: 20px;
              text-align: center;
              page-break-after: avoid;
            }
            h2 {
              font-size: 18px;
              font-weight: 600;
              color: #1e40af;
              margin-top: 24px;
              margin-bottom: 12px;
              border-bottom: 2px solid #93c5fd;
              padding-bottom: 8px;
              page-break-after: avoid;
            }
            p, ul, div {
              font-size: 14px;
              margin-bottom: 12px;
              page-break-inside: avoid;
            }
            ul {
              margin-left: 20px;
            }
            li {
              margin-bottom: 8px;
            }
            .footer {
              margin-top: 32px;
              padding-top: 16px;
              border-top: 1px solid #e5e7eb;
              font-size: 12px;
              color: #6b7280;
              text-align: center;
              page-break-before: avoid;
            }
            @media print {
              body {
                background: white;
              }
              @page {
                margin: 0.5in;
              }
            }
          </style>
        </head>
        <body>
          <h1>Your Health Summary</h1>
          <h2>What is happening</h2>
          <p>${condition_explanation || 'Not available'}</p>
          <h2>How your treatment is going</h2>
          <p>${current_status || 'Not available'}</p>
          <h2>What you need to do next</h2>
          <div>${next_steps ? next_steps.replace(/\n/g, '<br />') : 'Not available'}</div>
          <div class="footer">
            <p>This summary was prepared for you by your healthcare team.</p>
            <p>Print date: ${new Date().toLocaleDateString()}</p>
          </div>
        </body>
      </html>
    `
    
    const win = window.open('', 'PRINT', 'height=800,width=800')
    win.document.write(content)
    win.document.close()
    
    // Give the document time to render before printing
    setTimeout(() => {
      try {
        win.print()
      } catch (e) {
        console.warn('Auto-print failed, user can print manually', e)
      }
      // Close window after a delay to allow printing to complete
      setTimeout(() => win.close(), 500)
    }, 250)
  }

  if (!isVisible) {
    return null
  }

  return (
    <div className="flex-1 overflow-auto p-4 min-h-0">
      {/* Error State */}
      {error && (
        <div className="mb-4 text-sm text-red-700 dark:text-red-300 border border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-900/20 rounded-md p-3 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <div className="text-xs">{error}</div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center gap-3 text-sm text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 p-4 rounded-md border border-blue-200 dark:border-blue-800">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Generating patient-friendly summary...</span>
        </div>
      )}

      {/* Content State - Summary exists and loaded */}
      {!loading && summary ? (
        <div className="space-y-6">
          {/* Header */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-blue-600 dark:text-blue-400 mb-2">Your Health Summary</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">This summary was prepared for you by your healthcare team.</p>
          </div>

          {/* Section 1: What is happening */}
          <div className="bg-slate-50 dark:bg-slate-900/30 rounded-lg p-6 border border-slate-200 dark:border-slate-700">
            <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">What is happening</h3>
            <p className="text-base leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
              {summary.condition_explanation || 'Not available'}
            </p>
          </div>

          {/* Section 2: How your treatment is going */}
          <div className="bg-slate-50 dark:bg-slate-900/30 rounded-lg p-6 border border-slate-200 dark:border-slate-700">
            <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">How your treatment is going</h3>
            <p className="text-base leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
              {summary.current_status || 'Not available'}
            </p>
          </div>

          {/* Section 3: What you need to do next */}
          <div className="bg-slate-50 dark:bg-slate-900/30 rounded-lg p-6 border border-slate-200 dark:border-slate-700">
            <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-3">What you need to do next</h3>
            <div className="text-base leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
              {summary.next_steps || 'Not available'}
            </div>
          </div>

          {/* Print Button */}
          <div className="flex justify-center pt-4">
            <button
              onClick={handlePrint}
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-all shadow-md hover:shadow-lg"
            >
              <Printer className="h-4 w-4" />
              Print for Patient
            </button>
          </div>
        </div>
      ) : (
        // Empty State - No summary yet
        !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12 space-y-4">
            <div className="bg-slate-100 dark:bg-slate-700/50 rounded-full p-4 mb-4">
              <Sparkles className="h-12 w-12 text-slate-400 dark:text-slate-500" />
            </div>
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-300 font-medium mb-2">No patient summary yet</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">Create a simple, easy-to-understand version of this patient's medical summary</p>
            </div>
            <button
              onClick={generateSummary}
              disabled={loading}
              className={cn(
                "px-6 py-3 rounded-lg font-semibold flex items-center gap-2 transition-all",
                loading
                  ? "bg-slate-300 dark:bg-slate-600 text-slate-500 cursor-not-allowed"
                  : "bg-blue-600 text-white hover:bg-blue-700 shadow-md hover:shadow-lg"
              )}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Generate Patient Explanation
                </>
              )}
            </button>
          </div>
        )
      )}
    </div>
  )
}
