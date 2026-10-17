import { floatToPcm16, frames, mixToMono, resampleLinear, toBytes } from './pcm'

describe('pcm helpers', () => {
  it('converts floats to 16-bit with clamping', () => {
    const out = floatToPcm16(new Float32Array([0, 1, -1, 2, -2, 0.5]))
    expect(Array.from(out)).toEqual([0, 32767, -32768, 32767, -32768, 16384])
  })
  it('resamples by the right ratio and keeps the shape of a ramp', () => {
    const input = Float32Array.from({ length: 480 }, (_, i) => i / 480)
    const out = resampleLinear(input, 48000, 16000)
    expect(out.length).toBe(160)
    expect(out[0]).toBeCloseTo(0, 5)
    expect(out[80]).toBeCloseTo(0.5, 2)
    expect(resampleLinear(input, 16000, 16000)).toBe(input)
  })
  it('mixes channels to mono', () => {
    const mono = mixToMono([new Float32Array([1, 0]), new Float32Array([0, 1])])
    expect(Array.from(mono)).toEqual([0.5, 0.5])
  })
  it('turns samples into little-endian bytes and splits into frames', () => {
    const bytes = toBytes(new Int16Array([1, 2, 3]))
    expect(bytes.byteLength).toBe(6)
    expect(new Uint8Array(bytes)[0]).toBe(1)
    const parts = frames(new ArrayBuffer(2500), 1024)
    expect(parts.map((p) => p.byteLength)).toEqual([1024, 1024, 452])
  })
})
