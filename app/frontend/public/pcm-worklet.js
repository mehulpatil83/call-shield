// Runs in the audio thread: hands each block of microphone samples to the page.
class PCMCapture extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0]
    if (channel && channel.length) this.port.postMessage(channel.slice(0))
    return true
  }
}
registerProcessor('pcm-capture', PCMCapture)
