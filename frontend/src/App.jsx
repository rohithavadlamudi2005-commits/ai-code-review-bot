import React, { useState, useEffect } from 'react'

export default function App() {
  const [status, setStatus] = useState('checking') // 'connected' | 'disconnected' | 'checking'
  const [response, setResponse] = useState(null)
  const [error, setError] = useState(null)
  const [lastChecked, setLastChecked] = useState(null)
  const [loading, setLoading] = useState(false)

  // Stage 2: GitHub PR Fetcher state
  const [owner, setOwner] = useState('microsoft')
  const [repo, setRepo] = useState('vscode')
  const [pullNumber, setPullNumber] = useState('123')
  const [prData, setPrData] = useState(null)
  const [filesData, setFilesData] = useState([])
  const [prLoading, setPrLoading] = useState(false)
  const [prError, setPrError] = useState(null)
  const [expandedFiles, setExpandedFiles] = useState({})

  // Stage 3: Static Analysis Engine state
  const [analyzeOwner, setAnalyzeOwner] = useState('facebook')
  const [analyzeRepo, setAnalyzeRepo] = useState('react')
  const [analyzePrNumber, setAnalyzePrNumber] = useState('28000')
  const [analysisData, setAnalysisData] = useState(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisError, setAnalysisError] = useState(null)

  // Stage 4: LLM Code Review Engine state
  const [reviewOwner, setReviewOwner] = useState('facebook')
  const [reviewRepo, setReviewRepo] = useState('react')
  const [reviewPrNumber, setReviewPrNumber] = useState('28000')
  const [reviewData, setReviewData] = useState(null)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [reviewError, setReviewError] = useState(null)
  const [activeTab, setActiveTab] = useState('combined')

  // Stage 5: Automated Review & Webhook state
  const [autoOwner, setAutoOwner] = useState('facebook')
  const [autoRepo, setAutoRepo] = useState('react')
  const [autoPrNumber, setAutoPrNumber] = useState('28000')
  const [autoRunData, setAutoRunData] = useState(null)
  const [autoLoading, setAutoLoading] = useState(false)
  const [autoError, setAutoError] = useState(null)

  // Create Test PR state
  const [testPrOwner, setTestPrOwner] = useState('rohithavadlamudi2005-commits')
  const [testPrRepo, setTestPrRepo] = useState('AI-Health-Assistant')
  const [testPrBaseBranch, setTestPrBaseBranch] = useState('main')
  const [testPrData, setTestPrData] = useState(null)
  const [testPrLoading, setTestPrLoading] = useState(false)
  const [testPrError, setTestPrError] = useState(null)

  const handleCreateTestPR = async (e) => {
    if (e) e.preventDefault()
    if (!testPrOwner.trim() || !testPrRepo.trim()) {
      setTestPrError('Please fill in repository owner and repository name.')
      return
    }

    setTestPrLoading(true)
    setTestPrError(null)
    setTestPrData(null)

    try {
      const res = await fetch(`/api/github/repos/${testPrOwner.trim()}/${testPrRepo.trim()}/test-pr`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_branch: testPrBaseBranch.trim() || 'main',
        }),
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || `Failed to create test PR: HTTP ${res.status}`)
      }

      setTestPrData(data)
    } catch (err) {
      console.error('Failed to create test PR:', err)
      setTestPrError(err.message || 'An unexpected error occurred while creating test PR.')
    } finally {
      setTestPrLoading(false)
    }
  }

  const fetchHealthStatus = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/health')
      if (!res.ok) {
        throw new Error(`HTTP error! Status: ${res.status}`)
      }
      const data = await res.json()
      setResponse(data)
      setStatus('connected')
    } catch (err) {
      console.error('Failed to fetch backend health status:', err)
      setError(err.message || 'Connection failed')
      setStatus('disconnected')
      setResponse(null)
    } finally {
      setLoading(false)
      setLastChecked(new Date().toLocaleTimeString())
    }
  }

  const handleFetchPullRequest = async (e) => {
    if (e) e.preventDefault()
    if (!owner.trim() || !repo.trim() || !pullNumber.toString().trim()) {
      setPrError('Please fill in repository owner, name, and PR number.')
      return
    }

    setPrLoading(true)
    setPrError(null)
    setPrData(null)
    setFilesData([])
    setExpandedFiles({})

    try {
      const prRes = await fetch(`/api/github/repos/${owner.trim()}/${repo.trim()}/pulls/${pullNumber.toString().trim()}`)
      const prJson = await prRes.json()

      if (!prRes.ok) {
        throw new Error(prJson.detail || `GitHub API error: HTTP ${prRes.status}`)
      }

      setPrData(prJson)

      const filesRes = await fetch(`/api/github/repos/${owner.trim()}/${repo.trim()}/pulls/${pullNumber.toString().trim()}/files`)
      const filesJson = await filesRes.json()

      if (!filesRes.ok) {
        throw new Error(filesJson.detail || `Failed to fetch PR files: HTTP ${filesRes.status}`)
      }

      setFilesData(filesJson)
    } catch (err) {
      console.error('Failed to fetch GitHub PR data:', err)
      setPrError(err.message || 'An unexpected error occurred while fetching PR data.')
    } finally {
      setPrLoading(false)
    }
  }

  const handleRunStaticAnalysis = async (e) => {
    if (e) e.preventDefault()
    if (!analyzeOwner.trim() || !analyzeRepo.trim() || !analyzePrNumber.toString().trim()) {
      setAnalysisError('Please enter owner, repository, and PR number for static analysis.')
      return
    }

    setAnalysisLoading(true)
    setAnalysisError(null)
    setAnalysisData(null)

    try {
      const res = await fetch('/api/analyze/pr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          owner: analyzeOwner.trim(),
          repo: analyzeRepo.trim(),
          pull_number: parseInt(analyzePrNumber.toString().trim(), 10),
        }),
      })

      const json = await res.json()
      if (!res.ok) {
        throw new Error(json.detail || `Static analysis failed: HTTP ${res.status}`)
      }

      setAnalysisData(json)
    } catch (err) {
      console.error('Static analysis request error:', err)
      setAnalysisError(err.message || 'Failed to run static code analysis.')
    } finally {
      setAnalysisLoading(false)
    }
  }

  const handleRunAiCodeReview = async (e) => {
    if (e) e.preventDefault()
    if (!reviewOwner.trim() || !reviewRepo.trim() || !reviewPrNumber.toString().trim()) {
      setReviewError('Please enter owner, repository, and PR number for AI review.')
      return
    }

    setReviewLoading(true)
    setReviewError(null)
    setReviewData(null)

    try {
      const res = await fetch('/api/review/pr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          owner: reviewOwner.trim(),
          repo: reviewRepo.trim(),
          pull_number: parseInt(reviewPrNumber.toString().trim(), 10),
        }),
      })

      const json = await res.json()
      if (!res.ok) {
        throw new Error(json.detail || `AI Code Review failed: HTTP ${res.status}`)
      }

      setReviewData(json)
    } catch (err) {
      console.error('AI review request error:', err)
      setReviewError(err.message || 'Failed to execute AI Code Review.')
    } finally {
      setReviewLoading(false)
    }
  }

  const handleRunAutomatedReviewManually = async (e) => {
    if (e) e.preventDefault()
    if (!autoOwner.trim() || !autoRepo.trim() || !autoPrNumber.toString().trim()) {
      setAutoError('Please enter owner, repository, and PR number for automated review execution.')
      return
    }

    setAutoLoading(true)
    setAutoError(null)
    setAutoRunData(null)

    try {
      const res = await fetch(`/api/review/pr/${autoOwner.trim()}/${autoRepo.trim()}/${autoPrNumber.toString().trim()}/run`, {
        method: 'POST',
      })

      const json = await res.json()
      if (!res.ok) {
        throw new Error(json.detail || `Automated review failed: HTTP ${res.status}`)
      }

      setAutoRunData(json)
    } catch (err) {
      console.error('Automated review trigger error:', err)
      setAutoError(err.message || 'Failed to execute automated PR review pipeline.')
    } finally {
      setAutoLoading(false)
    }
  }

  const toggleFilePatch = (filename) => {
    setExpandedFiles((prev) => ({
      ...prev,
      [filename]: !prev[filename],
    }))
  }

  useEffect(() => {
    fetchHealthStatus()
  }, [])

  return (
    <div className="dashboard-container">
      {/* Header Bar */}
      <header className="header">
        <div className="brand">
          <div className="brand-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6"></polyline>
              <polyline points="8 6 2 12 8 18"></polyline>
              <circle cx="12" cy="12" r="2"></circle>
            </svg>
          </div>
          <div className="brand-text">
            <h1>AI Code Review Bot</h1>
            <p>Stage 5 — Automated GitHub PR Commenting & Webhook Integration</p>
          </div>
        </div>

        {/* Status Indicator */}
        <div className={`status-badge ${status}`}>
          <span className="pulse-dot"></span>
          <span>
            Backend Status: {status === 'connected' ? 'Connected' : status === 'disconnected' ? 'Disconnected' : 'Checking...'}
          </span>
        </div>
      </header>

      {/* STAGE 5: Automated Review & Webhook Integration Section */}
      <section className="card">
        <div className="card-header">
          <h2 className="card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
              <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
            </svg>
            Automated PR Review & GitHub Webhooks
          </h2>
        </div>

        <form className="github-form" onSubmit={handleRunAutomatedReviewManually}>
          <div className="form-group">
            <label htmlFor="auto-owner-input">Owner</label>
            <input
              id="auto-owner-input"
              type="text"
              className="form-input"
              placeholder="e.g. facebook"
              value={autoOwner}
              onChange={(e) => setAutoOwner(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="auto-repo-input">Repository</label>
            <input
              id="auto-repo-input"
              type="text"
              className="form-input"
              placeholder="e.g. react"
              value={autoRepo}
              onChange={(e) => setAutoRepo(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="auto-pr-input">PR Number</label>
            <input
              id="auto-pr-input"
              type="number"
              className="form-input"
              placeholder="e.g. 28000"
              value={autoPrNumber}
              onChange={(e) => setAutoPrNumber(e.target.value)}
              required
              min="1"
            />
          </div>

          <button type="submit" className="btn-primary" disabled={autoLoading}>
            {autoLoading ? (
              <>
                <svg className="spinning" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M23 4v6h-6"></path>
                  <path d="M1 20v-6h6"></path>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                </svg>
                Executing Review...
              </>
            ) : (
              'Run Review Manually'
            )}
          </button>
        </form>

        {autoError && (
          <div className="code-block" style={{ color: 'var(--status-disconnected-text)', borderColor: 'var(--status-disconnected-border)' }}>
            Automated Review Error: {autoError}
          </div>
        )}

        {/* Webhook Endpoint Info */}
        <div className="info-list" style={{ background: 'var(--bg-secondary)', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
          <div className="info-item">
            <span className="info-label">Webhook Listener URL</span>
            <span className="info-value" style={{ color: '#38bdf8' }}>POST /api/webhooks/github</span>
          </div>
          <div className="info-item">
            <span className="info-label">Signature Verification</span>
            <span className="info-value">HMAC SHA-256 (X-Hub-Signature-256)</span>
          </div>
          <div className="info-item">
            <span className="info-label">Supported Events</span>
            <span className="info-value">pull_request (opened, synchronize, reopened)</span>
          </div>
        </div>

        {/* Automated Run Result Display */}
        {autoRunData && (
          <div className="pr-overview">
            <div className="pr-header">
              <div>
                <h3 className="pr-title-text">
                  Review Run: {autoRunData.repo_full_name} PR #{autoRunData.pull_number}
                </h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  Commit SHA: <strong style={{ color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>{autoRunData.commit_sha}</strong>
                </p>
              </div>
              <span className={`status-pill-lg ${(autoRunData.status || 'not_run').toLowerCase()}`}>
                {autoRunData.status}
              </span>
            </div>

            <div className="pr-meta-grid">
              <div className="meta-pill">
                <span className="meta-label">Findings Posted</span>
                <span className="meta-value">{autoRunData.findings_count} finding(s)</span>
              </div>
              <div className="meta-pill">
                <span className="meta-label">GitHub Review ID</span>
                <span className="meta-value">{autoRunData.github_review_id || 'N/A (Dry run / Local)'}</span>
              </div>
              <div className="meta-pill">
                <span className="meta-label">Completed Timestamp</span>
                <span className="meta-value branch">{autoRunData.completed_at || 'In progress'}</span>
              </div>
            </div>

            {autoRunData.error_message && (
              <div className="code-block" style={{ color: 'var(--status-disconnected-text)', borderColor: 'var(--status-disconnected-border)' }}>
                Run Failure Details: {autoRunData.error_message}
              </div>
            )}
          </div>
        )}
      </section>

      {/* STAGE 4: AI Code Review Engine Section */}
      <section className="card">
        <div className="card-header">
          <h2 className="card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a10 10 0 1 0 10 10H12V2z"></path>
              <path d="M12 2A10 10 0 0 1 22 12h-10V2z"></path>
              <path d="M12 12L2.1 12a10 10 0 0 1 9.9-10v10z"></path>
            </svg>
            AI Code Review Engine (LLM + Static Analysis)
          </h2>
        </div>

        <form className="github-form" onSubmit={handleRunAiCodeReview}>
          <div className="form-group">
            <label htmlFor="ai-owner-input">Owner</label>
            <input
              id="ai-owner-input"
              type="text"
              className="form-input"
              placeholder="e.g. facebook"
              value={reviewOwner}
              onChange={(e) => setReviewOwner(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="ai-repo-input">Repository</label>
            <input
              id="ai-repo-input"
              type="text"
              className="form-input"
              placeholder="e.g. react"
              value={reviewRepo}
              onChange={(e) => setReviewRepo(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="ai-pr-input">PR Number</label>
            <input
              id="ai-pr-input"
              type="number"
              className="form-input"
              placeholder="e.g. 28000"
              value={reviewPrNumber}
              onChange={(e) => setReviewPrNumber(e.target.value)}
              required
              min="1"
            />
          </div>

          <button type="submit" className="btn-primary" disabled={reviewLoading}>
            {reviewLoading ? (
              <>
                <svg className="spinning" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M23 4v6h-6"></path>
                  <path d="M1 20v-6h6"></path>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                </svg>
                Analyzing PR...
              </>
            ) : (
              'Run AI Code Review'
            )}
          </button>
        </form>

        {reviewError && (
          <div className="code-block" style={{ color: 'var(--status-disconnected-text)', borderColor: 'var(--status-disconnected-border)' }}>
            AI Code Review Error: {reviewError}
          </div>
        )}

        {reviewData && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div className="review-stats-bar">
              <div className="metric-card">
                <div className="metric-icon-box combined">★</div>
                <div className="metric-details">
                  <span className="metric-num">{reviewData.combined_findings_count}</span>
                  <span className="metric-title">Combined Findings</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon-box static">⚙</div>
                <div className="metric-details">
                  <span className="metric-num">{reviewData.static_findings_count}</span>
                  <span className="metric-title">Static Analysis</span>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon-box ai">✦</div>
                <div className="metric-details">
                  <span className="metric-num">{reviewData.llm_findings_count}</span>
                  <span className="metric-title">AI LLM Review</span>
                </div>
              </div>
            </div>

            <div className="tab-nav">
              <button
                type="button"
                className={`tab-btn ${activeTab === 'combined' ? 'active' : ''}`}
                onClick={() => setActiveTab('combined')}
              >
                Combined Review ({reviewData.combined_findings.length})
              </button>
              <button
                type="button"
                className={`tab-btn ${activeTab === 'static' ? 'active' : ''}`}
                onClick={() => setActiveTab('static')}
              >
                Static Findings ({reviewData.static_findings.length})
              </button>
              <button
                type="button"
                className={`tab-btn ${activeTab === 'llm' ? 'active' : ''}`}
                onClick={() => setActiveTab('llm')}
              >
                AI Findings ({reviewData.llm_findings.length})
              </button>
            </div>

            {activeTab === 'combined' && (
              <div className="finding-card-list">
                {reviewData.combined_findings.length > 0 ? (
                  reviewData.combined_findings.map((f, idx) => (
                    <div key={idx} className={`finding-card ${f.severity.toLowerCase()}`}>
                      <div className="finding-top-bar">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <span className={`badge-state ${f.severity.toLowerCase()}`}>{f.severity}</span>
                          <span className={`source-pill ${f.source}`}>{f.source}</span>
                          {f.static_rule_id && <span className="rule-tag">{f.static_rule_id}</span>}
                          <span className="confidence-tag">Confidence: {Math.round(f.confidence * 100)}%</span>
                        </div>
                        <span className="finding-location">
                          File: <strong>{f.file}</strong> {f.line ? `: Line ${f.line}` : ''}
                        </span>
                      </div>

                      <div className="finding-message">{f.message}</div>

                      {f.evidence && (
                        <div className="finding-section">
                          <span className="finding-section-label">Code Evidence</span>
                          <pre className="evidence-block">{f.evidence}</pre>
                        </div>
                      )}

                      <div className="finding-section">
                        <span className="finding-section-label">Explanation</span>
                        <p className="finding-section-body">{f.explanation}</p>
                      </div>

                      <div className="finding-section">
                        <span className="finding-section-label">Suggested Fix</span>
                        <div className="finding-section-body suggestion">{f.suggestion}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="code-block" style={{ color: '#4ade80', borderColor: '#22c55e' }}>
                    ✓ No combined findings detected on changed PR lines!
                  </div>
                )}
              </div>
            )}

            {activeTab === 'static' && (
              <div className="finding-card-list">
                {reviewData.static_findings.length > 0 ? (
                  reviewData.static_findings.map((f, idx) => (
                    <div key={idx} className={`finding-card ${f.severity.toLowerCase()}`}>
                      <div className="finding-top-bar">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className={`badge-state ${f.severity.toLowerCase()}`}>{f.severity}</span>
                          <span className="rule-tag">{f.rule_id}</span>
                        </div>
                        <span className="finding-location">File: <strong>{f.file}</strong> : Line {f.line}</span>
                      </div>
                      <div className="finding-message">{f.message}</div>
                      <div className="finding-section">
                        <span className="finding-section-label">Explanation</span>
                        <p className="finding-section-body">{f.explanation}</p>
                      </div>
                      <div className="finding-section">
                        <span className="finding-section-label">Suggestion</span>
                        <div className="finding-section-body suggestion">{f.suggestion}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="code-block" style={{ color: '#4ade80', borderColor: '#22c55e' }}>
                    ✓ No static findings detected!
                  </div>
                )}
              </div>
            )}

            {activeTab === 'llm' && (
              <div className="finding-card-list">
                {reviewData.llm_findings.length > 0 ? (
                  reviewData.llm_findings.map((f, idx) => (
                    <div key={idx} className={`finding-card ${f.severity.toLowerCase()}`}>
                      <div className="finding-top-bar">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className={`badge-state ${f.severity.toLowerCase()}`}>{f.severity}</span>
                          <span className="source-pill llm">AI LLM</span>
                          <span className="confidence-tag">Confidence: {Math.round(f.confidence * 100)}%</span>
                        </div>
                        <span className="finding-location">File: <strong>{f.file}</strong> {f.line ? `: Line ${f.line}` : ''}</span>
                      </div>
                      <div className="finding-message">{f.message}</div>
                      {f.evidence && (
                        <div className="finding-section">
                          <span className="finding-section-label">Code Evidence</span>
                          <pre className="evidence-block">{f.evidence}</pre>
                        </div>
                      )}
                      <div className="finding-section">
                        <span className="finding-section-label">Explanation</span>
                        <p className="finding-section-body">{f.explanation}</p>
                      </div>
                      <div className="finding-section">
                        <span className="finding-section-label">Suggestion</span>
                        <div className="finding-section-body suggestion">{f.suggestion}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="code-block" style={{ color: '#4ade80', borderColor: '#22c55e' }}>
                    ✓ No AI findings returned!
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </section>

      {/* STAGE 3: Static Analysis Engine Section */}
      <section className="card">
        <div className="card-header">
          <h2 className="card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
            </svg>
            Static Code Analysis Engine (AST & Security Rules)
          </h2>
        </div>

        <form className="github-form" onSubmit={handleRunStaticAnalysis}>
          <div className="form-group">
            <label htmlFor="ast-owner-input">Owner</label>
            <input
              id="ast-owner-input"
              type="text"
              className="form-input"
              placeholder="e.g. facebook"
              value={analyzeOwner}
              onChange={(e) => setAnalyzeOwner(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="ast-repo-input">Repository</label>
            <input
              id="ast-repo-input"
              type="text"
              className="form-input"
              placeholder="e.g. react"
              value={analyzeRepo}
              onChange={(e) => setAnalyzeRepo(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="ast-pr-input">PR Number</label>
            <input
              id="ast-pr-input"
              type="number"
              className="form-input"
              placeholder="e.g. 28000"
              value={analyzePrNumber}
              onChange={(e) => setAnalyzePrNumber(e.target.value)}
              required
              min="1"
            />
          </div>

          <button type="submit" className="btn-primary" disabled={analysisLoading}>
            {analysisLoading ? (
              <>
                <svg className="spinning" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M23 4v6h-6"></path>
                  <path d="M1 20v-6h6"></path>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                </svg>
                Analyzing...
              </>
            ) : (
              'Analyze Pull Request'
            )}
          </button>
        </form>

        {analysisError && (
          <div className="code-block" style={{ color: 'var(--status-disconnected-text)', borderColor: 'var(--status-disconnected-border)' }}>
            Error during static analysis: {analysisError}
          </div>
        )}

        {analysisData && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div className="pr-overview">
              <div className="pr-header">
                <div>
                  <h3 className="pr-title-text">
                    Analysis Report: {analysisData.owner}/{analysisData.repo} PR #{analysisData.pull_number}
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    Diff-aware analysis completed across {analysisData.analyzed_files_count} supported file(s) ({analysisData.skipped_files_count} skipped).
                  </p>
                </div>
                <span className="badge-state open" style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}>
                  {analysisData.total_findings} Finding(s)
                </span>
              </div>

              <div className="severity-summary-grid">
                <div className="sev-badge-card critical">
                  <span className="sev-count">{analysisData.severity_counts.CRITICAL || 0}</span>
                  <span className="sev-name">Critical</span>
                </div>
                <div className="sev-badge-card high">
                  <span className="sev-count">{analysisData.severity_counts.HIGH || 0}</span>
                  <span className="sev-name">High</span>
                </div>
                <div className="sev-badge-card medium">
                  <span className="sev-count">{analysisData.severity_counts.MEDIUM || 0}</span>
                  <span className="sev-name">Medium</span>
                </div>
                <div className="sev-badge-card low">
                  <span className="sev-count">{analysisData.severity_counts.LOW || 0}</span>
                  <span className="sev-name">Low</span>
                </div>
                <div className="sev-badge-card info">
                  <span className="sev-count">{analysisData.severity_counts.INFO || 0}</span>
                  <span className="sev-name">Info</span>
                </div>
              </div>
            </div>

            {analysisData.findings.length > 0 ? (
              <div className="finding-card-list">
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Detected Code Findings ({analysisData.findings.length})
                </h3>
                {analysisData.findings.map((finding, idx) => (
                  <div key={idx} className={`finding-card ${finding.severity.toLowerCase()}`}>
                    <div className="finding-top-bar">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className={`badge-state ${finding.severity.toLowerCase()}`}>{finding.severity}</span>
                        <span className="rule-tag">{finding.rule_id}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                          &bull; {finding.category}
                        </span>
                      </div>
                      <span className="finding-location">
                        File: <strong>{finding.file}</strong> : Line <strong>{finding.line}</strong>
                      </span>
                    </div>

                    <div className="finding-message">{finding.message}</div>

                    <div className="finding-section">
                      <span className="finding-section-label">Explanation</span>
                      <p className="finding-section-body">{finding.explanation}</p>
                    </div>

                    <div className="finding-section">
                      <span className="finding-section-label">Recommendation / Fix</span>
                      <div className="finding-section-body suggestion">{finding.suggestion}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="code-block" style={{ color: '#4ade80', borderColor: '#22c55e' }}>
                ✓ No static analysis security or quality issues detected on changed PR lines!
              </div>
            )}
          </div>
        )}
      </section>

      {/* Create Test Pull Request Section */}
      <section className="card">
        <div className="card-header">
          <h2 className="card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            Create Test Pull Request
          </h2>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
          Automatically create a Git branch with sample vulnerable code (<code style={{ color: 'var(--accent-pink)' }}>ai_review_test.py</code>) and open a test Pull Request on GitHub.
        </p>

        <form className="github-form" onSubmit={handleCreateTestPR}>
          <div className="form-group">
            <label htmlFor="test-owner-input">Owner</label>
            <input
              id="test-owner-input"
              type="text"
              className="form-input"
              placeholder="e.g. rohithavadlamudi2005-commits"
              value={testPrOwner}
              onChange={(e) => setTestPrOwner(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="test-repo-input">Repository</label>
            <input
              id="test-repo-input"
              type="text"
              className="form-input"
              placeholder="e.g. AI-Health-Assistant"
              value={testPrRepo}
              onChange={(e) => setTestPrRepo(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="test-base-branch-input">Base Branch</label>
            <input
              id="test-base-branch-input"
              type="text"
              className="form-input"
              placeholder="e.g. main"
              value={testPrBaseBranch}
              onChange={(e) => setTestPrBaseBranch(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn-primary" disabled={testPrLoading}>
            {testPrLoading ? (
              <>
                <svg className="spinning" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M23 4v6h-6"></path>
                  <path d="M1 20v-6h6"></path>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                </svg>
                Creating Test PR...
              </>
            ) : (
              'Create Test PR'
            )}
          </button>
        </form>

        {testPrError && (
          <div className="code-block" style={{ color: 'var(--status-disconnected-text)', borderColor: 'var(--status-disconnected-border)', marginTop: '1rem' }}>
            Error creating test PR: {testPrError}
          </div>
        )}

        {testPrData && (
          <div className="pr-overview" style={{ marginTop: '1.25rem' }}>
            <div className="pr-header">
              <div>
                <h3 className="pr-title-text" style={{ color: '#4ade80' }}>✓ Test Pull Request Created Successfully!</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  {testPrData.title}
                </p>
              </div>
              <span className="badge-state open">PR #{testPrData.pull_number}</span>
            </div>

            <div className="pr-meta-grid">
              <div className="meta-pill">
                <span className="meta-label">Branch Name</span>
                <span className="meta-value branch">{testPrData.branch_name}</span>
              </div>
              <div className="meta-pill">
                <span className="meta-label">Pull Request #</span>
                <span className="meta-value">#{testPrData.pull_number}</span>
              </div>
              <div className="meta-pill" style={{ gridColumn: 'span 2' }}>
                <span className="meta-label">Pull Request URL</span>
                <a
                  href={testPrData.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="meta-value"
                  style={{ color: '#60a5fa', textDecoration: 'underline', wordBreak: 'break-all' }}
                >
                  {testPrData.html_url}
                </a>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* STAGE 2: GitHub PR Inspector Section */}
      <section className="card">
        <div className="card-header">
          <h2 className="card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 22v-4a48.4 48.4 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"></path>
              <path d="M9 18c-4.51 2-5-2-7-2"></path>
            </svg>
            GitHub Pull Request Inspector
          </h2>
        </div>

        <form className="github-form" onSubmit={handleFetchPullRequest}>
          <div className="form-group">
            <label htmlFor="owner-input">Owner</label>
            <input
              id="owner-input"
              type="text"
              className="form-input"
              placeholder="e.g. microsoft"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="repo-input">Repository</label>
            <input
              id="repo-input"
              type="text"
              className="form-input"
              placeholder="e.g. vscode"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="pr-input">PR Number</label>
            <input
              id="pr-input"
              type="number"
              className="form-input"
              placeholder="e.g. 123"
              value={pullNumber}
              onChange={(e) => setPullNumber(e.target.value)}
              required
              min="1"
            />
          </div>

          <button type="submit" className="btn-primary" disabled={prLoading}>
            {prLoading ? (
              <>
                <svg className="spinning" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M23 4v6h-6"></path>
                  <path d="M1 20v-6h6"></path>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                </svg>
                Fetching...
              </>
            ) : (
              'Fetch Pull Request'
            )}
          </button>
        </form>

        {prError && (
          <div className="code-block" style={{ color: 'var(--status-disconnected-text)', borderColor: 'var(--status-disconnected-border)' }}>
            Error fetching PR: {prError}
          </div>
        )}

        {prData && (
          <div className="pr-overview">
            <div className="pr-header">
              <div>
                <h3 className="pr-title-text">{prData.title}</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  Pull Request #{prData.pull_number} in <strong style={{ color: 'var(--text-secondary)' }}>{prData.repository}</strong>
                </p>
              </div>
              <span className={`badge-state ${prData.state}`}>{prData.state}</span>
            </div>

            <div className="pr-meta-grid">
              <div className="meta-pill">
                <span className="meta-label">Author</span>
                <span className="meta-value">@{prData.author}</span>
              </div>
              <div className="meta-pill">
                <span className="meta-label">Branches</span>
                <span className="meta-value branch">{prData.head_branch} &rarr; {prData.base_branch}</span>
              </div>
              <div className="meta-pill">
                <span className="meta-label">Changed Files</span>
                <span className="meta-value">{prData.changed_files_count} files</span>
              </div>
              <div className="meta-pill">
                <span className="meta-label">Lines Changed</span>
                <span className="meta-value">
                  <span className="additions">+{prData.additions}</span>{' '}
                  <span className="deletions">-{prData.deletions}</span>
                </span>
              </div>
            </div>
          </div>
        )}

        {filesData.length > 0 && (
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
              Changed Files ({filesData.length})
            </h3>
            <div className="file-list">
              {filesData.map((file, idx) => {
                const isExpanded = !!expandedFiles[file.filename]
                return (
                  <div key={idx} className="file-item">
                    <div className="file-header" onClick={() => toggleFilePatch(file.filename)}>
                      <div className="file-title">
                        <span className={`file-status ${file.status}`}>{file.status}</span>
                        <span>{file.filename}</span>
                      </div>
                      <div className="file-stats">
                        <span className="additions">+{file.additions}</span>
                        <span className="deletions">-{file.deletions}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {isExpanded ? '▲ Hide Diff' : '▼ View Diff'}
                        </span>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="patch-container">
                        {file.patch ? (
                          file.patch.split('\n').map((line, lineIdx) => {
                            let typeClass = ''
                            if (line.startsWith('+') && !line.startsWith('+++')) typeClass = 'add'
                            else if (line.startsWith('-') && !line.startsWith('---')) typeClass = 'delete'
                            else if (line.startsWith('@@')) typeClass = 'header'

                            return (
                              <div key={lineIdx} className={`patch-line ${typeClass}`}>
                                {line}
                              </div>
                            )
                          })
                        ) : (
                          <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            No patch string available (file may be binary or exceed GitHub patch size limits).
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </section>

      {/* Backend Diagnostics Section */}
      <main className="grid">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                <line x1="8" y1="21" x2="16" y2="21"></line>
                <line x1="12" y1="17" x2="12" y2="21"></line>
              </svg>
              GET /api/health Response
            </h2>
            <button 
              className={`btn-refresh ${loading ? 'spinning' : ''}`} 
              onClick={fetchHealthStatus}
              disabled={loading}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M23 4v6h-6"></path>
                <path d="M1 20v-6h6"></path>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
              </svg>
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          <div className="card-body">
            {status === 'checking' && (
              <p style={{ color: 'var(--text-muted)' }}>Connecting to backend service...</p>
            )}

            {status === 'connected' && response && (
              <pre className="code-block">
                {JSON.stringify(response, null, 2)}
              </pre>
            )}

            {status === 'disconnected' && (
              <div className="code-block" style={{ color: 'var(--status-disconnected-text)', borderColor: 'var(--status-disconnected-border)' }}>
                {`Error: Unable to connect to backend at /api/health.\nDetails: ${error}`}
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <h2 className="card-title">System Metrics</h2>
          <div className="info-list">
            <div className="info-item">
              <span className="info-label">Target Endpoint</span>
              <span className="info-value">/api/health</span>
            </div>
            <div className="info-item">
              <span className="info-label">Expected Status</span>
              <span className="info-value">200 OK</span>
            </div>
            <div className="info-item">
              <span className="info-label">Service ID</span>
              <span className="info-value">{response?.service || 'ai-code-review-bot'}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Last Checked</span>
              <span className="info-value">{lastChecked || 'N/A'}</span>
            </div>
          </div>
        </div>
      </main>

      {/* Stage Roadmap Notice */}
      <section className="card roadmap-card">
        <span className="stage-tag">Current Milestone: Stage 5</span>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem' }}>Upcoming Roadmap</h3>
        <ul className="roadmap-list">
          <li>✓ Stage 1: Initial Backend & Frontend Architecture</li>
          <li>✓ Stage 2: GitHub API Integration & PR Fetching</li>
          <li>✓ Stage 3: AST Static Analysis & Security Scanning Engine</li>
          <li>✓ Stage 4: LLM Code Review Engine & Combined Findings Pipeline</li>
          <li>✓ Stage 5: Automated GitHub PR Commenting & Webhooks</li>
        </ul>
      </section>

      <footer>
        AI Code Review Bot &bull; Stage 5 Automated PR Commenting & Webhooks
      </footer>
    </div>
  )
}
