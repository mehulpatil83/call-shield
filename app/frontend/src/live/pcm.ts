/** Audio helpers: everything the server wants is mono 16 kHz signed 16-bit little-endian PCM. */

export function floatToPcm16(input: Float32Array): Int16Array {
  const out = new Int16Array(input.length)
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]))
    out[i] = s < 0 ? Math.round(s * 32768) : Math.round(s * 32767)
  }
  return out
}

export function resampleLinear(input: Float32Array, from: number, to: number): Float32Array {
  if (from === to || input.length === 0) return input
  const ratio = from / to
  const length = Math.max(1, Math.floor(input.length / ratio))
  const out = new Float32Array(length)
  for (let i = 0; i < length; i++) {
    const pos = i * ratio
    const i0 = Math.floor(pos)
    const i1 = Math.min(i0 + 1, input.length - 1)
    const frac = pos - i0
    out[i] = input[i0] * (1 - frac) + input[i1] * frac
  }
  return out
}

export function mixToMono(channels: Float32Array[]): Float32Array {
  if (channels.length === 1) return channels[0]
  const out = new Float32Array(channels[0].length)
  for (const ch of channels) for (let i = 0; i < out.length; i++) out[i] += ch[i] / channels.length
  return out
}

export function toBytes(pcm: Int16Array): ArrayBuffer {
  return pcm.buffer.slice(pcm.byteOffset, pcm.byteOffset + pcm.byteLength) as ArrayBuffer
}

/** Split into frames of `size` bytes (the last one may be shorter). */
export function frames(buffer: ArrayBuffer, size: number): ArrayBuffer[] {
  const out: ArrayBuffer[] = []
  for (let i = 0; i < buffer.byteLength; i += size) out.push(buffer.slice(i, Math.min(i + size, buffer.byteLength)))
  return out
}
