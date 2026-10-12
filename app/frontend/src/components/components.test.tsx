import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import ReportView from './ReportView'
import UploadCard from './UploadCard'
import HistoryList from './HistoryList'
import { STRINGS } from '../i18n'
import type { AnalysisDetail } from '../types'

const text = 'please share the otp right now'
const detail: AnalysisDetail = {
  id: 'abcdef012345', filename: 'en_call.wav', created: '2026-10-10T10:00:00', language: 'en', status: 'done',
  step: null, error: null, level: 'high', auth_label: null, est_rupees: 0.2,
  report: {
    meta: { file: 'en_call.wav', language: 'en', created: '2026-10-10T10:00:00', audio_seconds: 22, est_cost_rupees: 0.2, stt_models: [] },
    plain_summary: '', advice: [],
    transcripts: [{
      code: 'en-IN', mode: 'rest', text,
      rules: { hits: [{ category: 'otp_request', kind: 'request', quote: 'share the otp', start: 7, end: 20, explanation: 'x', source: '' },
                      { category: 'urgency', kind: 'pressure', quote: 'right now', start: 21, end: 30, explanation: 'y', source: '' }] },
    }],
    conversation: {
      level: 'high', label: 'High risk', score: 7, summary: '', digit_note: '',
      hits: [{ category: 'otp_request', kind: 'request', quote: 'share the otp', start: 7, end: 20, explanation: 'x', source: '' }],
      digit_runs: [{ digits: '4721', start: 0, end: 4, quote: 'four seven two one' }],
    },
    authenticity: {
      status: 'ok', label: 'Consistent with natural speech (provisional)', code: 'natural', reason: '', median: -3.0, q25: -3.5, q75: -2.5,
      n_windows: 3, window_scores: [-3.1, -3.0, -2.9], real_at_least: -4.8, synth_at_most: -6.8, note: '', plain_note: '', model: 'AASIST-L',
    },
    limitations: [],
  },
}

describe('UploadCard', () => {
  it('stays disabled until a file is chosen and consent is given', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<UploadCard t={STRINGS.en} maxMb={25} keyPresent busy={false} onSubmit={onSubmit} />)
    const button = screen.getByRole('button', { name: STRINGS.en.analyse })
    expect(button).toBeDisabled()
    await user.upload(document.getElementById('audio-file') as HTMLInputElement, new File(['x'], 'en_call.wav', { type: 'audio/wav' }))
    expect(button).toBeDisabled()                       // still no consent
    await user.click(screen.getByRole('checkbox', { name: new RegExp(STRINGS.en.consent.slice(0, 20)) }))
    expect(button).toBeEnabled()
    await user.click(button)
    expect(onSubmit).toHaveBeenCalledWith(expect.any(File), 'en', true, false)
  })
  it('warns when the Gnani key is missing and when the file is too large', async () => {
    const user = userEvent.setup()
    render(<UploadCard t={STRINGS.en} maxMb={1} keyPresent={false} busy={false} onSubmit={() => {}} />)
    expect(screen.getByText(STRINGS.en.keyMissing)).toBeInTheDocument()
    const big = new File([new Uint8Array(2 * 1024 * 1024)], 'big.wav', { type: 'audio/wav' })
    await user.upload(document.getElementById('audio-file') as HTMLInputElement, big)
    expect(screen.getByText(STRINGS.en.tooBig(1))).toBeInTheDocument()
  })
})

describe('ReportView', () => {
  it('renders in Marathi with advice, evidence and the audio label', () => {
    render(<ReportView detail={detail} t={STRINGS.mr} onDelete={() => {}} onBack={() => {}} />)
    expect(screen.getByTestId('level-badge')).toHaveTextContent(STRINGS.mr.levels.high)
    expect(screen.getByTestId('plain-summary')).toHaveTextContent(STRINGS.mr.plain.high)
    expect(screen.getByText(STRINGS.mr.advice.high[0])).toBeInTheDocument()
    expect(screen.getByText(STRINGS.mr.auth.natural)).toBeInTheDocument()
    expect(screen.getByText(STRINGS.mr.categories.otp_request.label)).toBeInTheDocument()
  })
  it('shows the reason when a highlighted phrase is tapped (works without hover)', async () => {
    const user = userEvent.setup()
    render(<ReportView detail={detail} t={STRINGS.en} onDelete={() => {}} onBack={() => {}} />)
    expect(screen.queryByTestId('hit-reason')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'right now' }))
    expect(screen.getByTestId('hit-reason')).toHaveTextContent(STRINGS.en.categories.urgency.explain)
  })
  it('links to the downloadable report and calls delete', async () => {
    const onDelete = vi.fn()
    const user = userEvent.setup()
    render(<ReportView detail={detail} t={STRINGS.en} onDelete={onDelete} onBack={() => {}} />)
    expect(screen.getByRole('link', { name: STRINGS.en.download })).toHaveAttribute('href', '/api/analyses/abcdef012345/report.html?download=true')
    await user.click(screen.getByRole('button', { name: STRINGS.en.delete }))
    expect(onDelete).toHaveBeenCalled()
  })
})

describe('low-risk report', () => {
  it('calls a lone weak signal a minor signal, not evidence', () => {
    const low: AnalysisDetail = {
      ...detail, level: 'low',
      report: { ...detail.report!, conversation: { ...detail.report!.conversation, level: 'low' } },
    }
    render(<ReportView detail={low} t={STRINGS.en} onDelete={() => {}} onBack={() => {}} />)
    expect(screen.getByRole('heading', { name: STRINGS.en.minor })).toBeInTheDocument()
    expect(screen.getByText(STRINGS.en.minorNote)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: STRINGS.en.evidence })).not.toBeInTheDocument()
  })
})

describe('HistoryList', () => {
  it('shows level badges, in-progress steps and errors', () => {
    const base = { created: '2026-10-10T10:00:00', language: 'en', est_rupees: null, auth_label: null, error: null }
    render(<HistoryList t={STRINGS.hi} onOpen={() => {}} onDelete={() => {}} onDeleteAll={() => {}} items={[
      { ...base, id: 'a', filename: 'one.wav', status: 'done', step: null, level: 'low' },
      { ...base, id: 'b', filename: 'two.wav', status: 'running', step: 'transcribing', level: null },
      { ...base, id: 'c', filename: 'three.wav', status: 'error', step: null, level: null },
    ]} />)
    expect(screen.getByText(STRINGS.hi.levels.low)).toBeInTheDocument()
    expect(screen.getByText(STRINGS.hi.steps.transcribing)).toBeInTheDocument()
    expect(screen.getByText(STRINGS.hi.failedTitle)).toBeInTheDocument()
  })
})
