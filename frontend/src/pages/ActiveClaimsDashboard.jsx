import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { Loader2, AlertCircle, AlertTriangle, CheckCircle2, Clock, ArrowLeft } from 'lucide-react'
import { cn } from '../lib/utils'

/**
 * ActiveClaimsDashboard - Global MA view of all non-GREEN claims
 * Fetches from GET /tpa/claims/active (already sorted oldest-first per FR-11)
 * Clicking a patient routes to their chart with Insurance tab focused
 */
export default function ActiveClaimsDashboard() {
  const [claims, setClaims] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchActiveClaims()
  }, [])

  const fetchActiveClaims = async () => {
    try {
      setLoading(true)
      setError(null)
      const url = `${import.meta.env.VITE_API_URL}/tpa/claims/active`
      const response = await axios.get(url)
      setClaims(response.data || [])
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load active claims')
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status) => {
    const statusUpper = String(status || '').toUpperCase()
    if (statusUpper === 'RED') return <AlertCircle className="h-5 w-5 text-white" />
    if (statusUpper === 'YELLOW') return <AlertTriangle className="h-5 w-5 text-white" />
    if (statusUpper === 'PROCESSING') return <Loader2 className="h-5 w-5 text-white animate-spin" />
    return <CheckCircle2 className="h-5 w-5 text-white" />
  }

  const getStatusStyles = (status) => {
    const statusUpper = String(status || '').toUpperCase()
    if (statusUpper === 'RED') return 'bg-red-500 border-red-600'
    if (statusUpper === 'YELLOW') return 'bg-amber-500 border-amber-600'
    if (statusUpper === 'PROCESSING') return 'bg-slate-500 border-slate-600'
    return 'bg-emerald-500 border-emerald-600'
  }

  const getStatusLabel = (status) => {
    const statusUpper = String(status || '').toUpperCase()
    if (statusUpper === 'RED') return 'Critical Error'
    if (statusUpper === 'YELLOW') return 'Needs Action'
    if (statusUpper === 'PROCESSING') return 'Processing'
    return 'Ready'
  }

  const getTimeElapsed = (createdAt) => {
    if (!createdAt) return 'N/A'
    const now = new Date()
    const created = new Date(createdAt)
    const diffMs = now - created
    const diffMins = Math.floor(diffMs / 60000)
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`
    
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  }

  const handlePatientClick = (patientId) => {
    // Navigate to dashboard and pass state to focus Insurance tab
    navigate('/', { state: { patientId, focusInsuranceTab: true } })
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-gradient-to-br from-slate-100 via-blue-50 to-purple-50 dark:from-slate-950 dark:via-slate-900 dark:to-blue-950">
      {/* Header */}
      <div className="sticky top-0 z-40 w-full backdrop-blur-sm bg-white/85 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="flex items-center justify-between px-6 h-16">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-sm font-medium text-slate-700 dark:text-slate-300 transition-all"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Patient List
            </button>
            <div className="border-l border-slate-300 dark:border-slate-600 pl-4">
              <h1 className="text-2xl font-black bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 bg-clip-text text-transparent tracking-tight">
                TPA Claims Queue
              </h1>
              <p className="text-xs text-slate-600 dark:text-slate-400">Active claims requiring medical assistant review</p>
            </div>
          </div>
          <button
            onClick={fetchActiveClaims}
            disabled={loading}
            className={cn(
              'px-4 py-2 rounded-lg border text-sm font-medium transition-all',
              loading
                ? 'border-slate-200 text-slate-400 dark:border-slate-700 dark:text-slate-500 cursor-not-allowed'
                : 'border-slate-300 text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800'
            )}
          >
            {loading ? 'Refreshing...' : 'Refresh Queue'}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-7xl mx-auto">
          {loading && claims.length === 0 ? (
            <div className="flex items-center justify-center h-96">
              <div className="flex items-center gap-3 text-slate-600 dark:text-slate-300">
                <Loader2 className="h-6 w-6 animate-spin" />
                <span className="text-lg font-medium">Loading active claims...</span>
              </div>
            </div>
          ) : error ? (
            <div className="max-w-2xl mx-auto mt-12 p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-red-800 dark:text-red-300">Error Loading Claims</p>
                  <p className="text-xs text-red-700 dark:text-red-400 mt-1">{error}</p>
                </div>
              </div>
            </div>
          ) : claims.length === 0 ? (
            <div className="max-w-2xl mx-auto mt-12 text-center">
              <div className="inline-flex p-6 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-full shadow-2xl mb-6">
                <CheckCircle2 className="h-16 w-16 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-200 mb-2">All Clear!</h2>
              <p className="text-sm text-slate-600 dark:text-slate-400">No claims currently require attention. All systems are Clear2Go ✓</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Queue Stats */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
                  <p className="text-xs text-slate-600 dark:text-slate-400 font-semibold mb-1">Total Active Claims</p>
                  <p className="text-2xl font-bold text-slate-800 dark:text-slate-200">{claims.length}</p>
                </div>
                <div className="p-4 rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
                  <p className="text-xs text-red-700 dark:text-red-300 font-semibold mb-1">Critical Errors</p>
                  <p className="text-2xl font-bold text-red-800 dark:text-red-200">
                    {claims.filter(c => String(c.status).toUpperCase() === 'RED').length}
                  </p>
                </div>
                <div className="p-4 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
                  <p className="text-xs text-amber-700 dark:text-amber-300 font-semibold mb-1">Warnings</p>
                  <p className="text-2xl font-bold text-amber-800 dark:text-amber-200">
                    {claims.filter(c => String(c.status).toUpperCase() === 'YELLOW').length}
                  </p>
                </div>
              </div>

              {/* Claims Table */}
              <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden bg-white dark:bg-slate-800">
                <table className="w-full">
                  <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">Priority</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">Patient</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">Claim ID</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">Time Waiting</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">Demographics</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-700 dark:text-slate-300">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                    {claims.map((claim, idx) => {
                      const statusUpper = String(claim.status || '').toUpperCase()
                      const isUrgent = statusUpper === 'RED'
                      const isWarning = statusUpper === 'YELLOW'
                      
                      return (
                        <tr
                          key={claim.claim_id}
                          className={cn(
                            'hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer',
                            isUrgent && 'bg-red-50/50 dark:bg-red-900/10',
                            isWarning && 'bg-amber-50/50 dark:bg-amber-900/10'
                          )}
                          onClick={() => handlePatientClick(claim.patient_id)}
                        >
                          {/* Priority Indicator */}
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className={cn(
                                'h-8 w-8 rounded-full flex items-center justify-center border-2',
                                getStatusStyles(claim.status)
                              )}>
                                {getStatusIcon(claim.status)}
                              </div>
                              {isUrgent && (
                                <span className="px-2 py-0.5 rounded-md bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-xs font-bold">
                                  URGENT
                                </span>
                              )}
                            </div>
                          </td>

                          {/* Patient Name */}
                          <td className="px-4 py-3">
                            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                              {claim.patient_name || 'Unknown Patient'}
                            </p>
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                              ID: {claim.patient_id}
                            </p>
                          </td>

                          {/* Claim ID */}
                          <td className="px-4 py-3">
                            <code className="px-2 py-1 rounded bg-slate-100 dark:bg-slate-900 text-xs font-mono text-slate-700 dark:text-slate-300">
                              {claim.claim_id}
                            </code>
                          </td>

                          {/* Status */}
                          <td className="px-4 py-3">
                            <span className={cn(
                              'px-2.5 py-1 rounded-md text-xs font-semibold inline-block',
                              statusUpper === 'RED' && 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
                              statusUpper === 'YELLOW' && 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
                              statusUpper === 'PROCESSING' && 'bg-slate-100 dark:bg-slate-900/30 text-slate-700 dark:text-slate-300'
                            )}>
                              {getStatusLabel(claim.status)}
                            </span>
                          </td>

                          {/* Time Elapsed */}
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                              <Clock className="h-4 w-4 text-slate-400" />
                              <span className="font-medium">{getTimeElapsed(claim.created_at)}</span>
                            </div>
                          </td>

                          {/* Demographics */}
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              {claim.patient_age != null && (
                                <span className="px-2 py-0.5 rounded-md bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs">
                                  {claim.patient_age} yrs
                                </span>
                              )}
                              {claim.patient_sex && (
                                <span className={cn(
                                  'px-2 py-0.5 rounded-md text-xs',
                                  claim.patient_sex === 'M' 
                                    ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                                    : 'bg-pink-100 dark:bg-pink-900/30 text-pink-700 dark:text-pink-300'
                                )}>
                                  {claim.patient_sex === 'M' ? 'Male' : claim.patient_sex === 'F' ? 'Female' : claim.patient_sex}
                                </span>
                              )}
                            </div>
                          </td>

                          {/* Action */}
                          <td className="px-4 py-3">
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                handlePatientClick(claim.patient_id)
                              }}
                              className="px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors"
                            >
                              Review
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {/* Queue Info Footer */}
              <div className="mt-4 p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
                <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
                  <Clock className="h-4 w-4" />
                  <p>
                    Queue sorted by oldest first (per FR-11). 
                    <span className="font-semibold text-slate-700 dark:text-slate-300 ml-1">
                      Total claims awaiting review: {claims.length}
                    </span>
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
