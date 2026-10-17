import { initialLive, liveReducer, type ServerMessage } from './state'

const analysis = (level: 'low' | 'elevated' | 'high', score: number): ServerMessage =>
  ({ type: 'analysis', level, score, summary: '', seconds: 5, tracks: [], hits: [] })

describe('liveReducer', () => {
  it('goes live on ready and updates on analysis', () => {
    let s = liveReducer(initialLive, { type: 'ready' })
    expect(s.status).toBe('live')
    s = liveReducer(s, analysis('elevated', 4.5))
    expect(s.level).toBe('elevated')
    expect(s.score).toBe(4.5)
  })
  it('never lowers an alert that was already raised', () => {
    let s = liveReducer(initialLive, { type: 'alert', level: 'high' })
    s = liveReducer(s, { type: 'alert', level: 'elevated' })
    expect(s.alert).toBe('high')
    expect(liveReducer(initialLive, { type: 'alert', level: 'elevated' }).alert).toBe('elevated')
  })
  it('records the end of the call, errors and limits', () => {
    expect(liveReducer(initialLive, { type: 'ended', id: 'abc' })).toMatchObject({ status: 'ended', id: 'abc' })
    expect(liveReducer(initialLive, { type: 'ended', id: null, message: 'short' }).message).toBe('short')
    expect(liveReducer(initialLive, { type: 'error', message: 'boom' })).toMatchObject({ status: 'error', message: 'boom' })
    expect(liveReducer(initialLive, { type: 'limit', seconds: 600 }).warning).toBe('limit:600')
  })
})
