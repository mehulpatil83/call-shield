import { resampleLinear } from './pcm'

export interface PcmPlayer { push: (pcm16: ArrayBuffer) => void; close: () => void }

/** Plays mono 16 kHz PCM16 chunks as they arrive (the Receiver's optional "listen" switch). Create it inside a click. */
export function createPcmPlayer(rate = 16000): PcmPlayer {
  let ctx: AudioContext
  try { ctx = new AudioContext({ sampleRate: rate }) } catch { ctx = new AudioContext() }
  void ctx.resume()
  let next = 0
  return {
    push(buf) {
      const ints = new Int16Array(buf.slice(0, buf.byteLength - (buf.byteLength % 2)))
      if (ints.length === 0) return
      const floats = new Float32Array(ints.length)
      for (let i = 0; i < ints.length; i++) floats[i] = ints[i] / 32768
      const data = resampleLinear(floats, rate, ctx.sampleRate)
      const b = ctx.createBuffer(1, data.length, ctx.sampleRate)
      b.copyToChannel(new Float32Array(data), 0)
      const src = ctx.createBufferSource()
      src.buffer = b
      src.connect(ctx.destination)
      const at = Math.max(ctx.currentTime + 0.15, next)         // small cushion against network jitter
      src.start(at)
      next = at + b.duration
    },
    close() { void ctx.close() },
  }
}
