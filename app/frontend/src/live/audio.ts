import { floatToPcm16, frames, mixToMono, resampleLinear, toBytes } from './pcm'

export const TARGET_RATE = 16000
export const FRAME_BYTES = 1024

/** Open the microphone and call onChunk with 16 kHz PCM16 bytes. Returns a function that stops everything. */
export async function startMicrophone(onChunk: (pcm: ArrayBuffer) => void): Promise<() => void> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  })
  let ctx: AudioContext
  let source: MediaStreamAudioSourceNode
  try {
    ctx = new AudioContext({ sampleRate: TARGET_RATE })
    source = ctx.createMediaStreamSource(stream)
  } catch {
    ctx = new AudioContext()          // some browsers cannot run at 16 kHz: resample ourselves
    source = ctx.createMediaStreamSource(stream)
  }
  await ctx.audioWorklet.addModule('/pcm-worklet.js')
  const node = new AudioWorkletNode(ctx, 'pcm-capture')
  const mute = ctx.createGain()
  mute.gain.value = 0                 // keep the graph running without playing the microphone back
  source.connect(node)
  node.connect(mute)
  mute.connect(ctx.destination)
  let pending: Float32Array[] = []
  let pendingLen = 0
  node.port.onmessage = (e: MessageEvent<Float32Array>) => {
    pending.push(e.data)
    pendingLen += e.data.length
    if (pendingLen < 1024) return     // batch about 20-60 ms before resampling and sending
    const joined = new Float32Array(pendingLen)
    let off = 0
    for (const p of pending) { joined.set(p, off); off += p.length }
    pending = []
    pendingLen = 0
    onChunk(toBytes(floatToPcm16(resampleLinear(joined, ctx.sampleRate, TARGET_RATE))))
  }
  return () => {
    node.port.onmessage = null
    node.disconnect()
    source.disconnect()
    stream.getTracks().forEach((t) => t.stop())
    void ctx.close()
  }
}

/** Decode a recording and play it into the pipeline at real-time speed, as if it were a live call. */
export async function startReplay(file: File, onChunk: (pcm: ArrayBuffer) => void, onDone: () => void): Promise<() => void> {
  const ctx = new AudioContext()
  const decoded = await ctx.decodeAudioData(await file.arrayBuffer())
  void ctx.close()
  const channels = Array.from({ length: decoded.numberOfChannels }, (_, i) => decoded.getChannelData(i))
  const mono = resampleLinear(mixToMono(channels), decoded.sampleRate, TARGET_RATE)
  const all = frames(toBytes(floatToPcm16(mono)), FRAME_BYTES)
  const start = performance.now()
  let sent = 0
  const timer = window.setInterval(() => {
    const due = Math.floor(((performance.now() - start) / 1000) * (TARGET_RATE / (FRAME_BYTES / 2)))
    while (sent < all.length && sent <= due) onChunk(all[sent++])
    if (sent >= all.length) {
      window.clearInterval(timer)
      onDone()
    }
  }, 30)
  return () => window.clearInterval(timer)
}
