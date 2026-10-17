import QRCode from 'qrcode'
import { useEffect, useState } from 'react'

/** QR code drawn as an inline SVG image (no canvas, no network). */
export default function QrCode({ value, label }: { value: string; label: string }) {
  const [src, setSrc] = useState<string | null>(null)
  useEffect(() => {
    let stop = false
    QRCode.toString(value, { type: 'svg', margin: 2, errorCorrectionLevel: 'M' })
      .then((svg) => { if (!stop) setSrc(`data:image/svg+xml;utf8,${encodeURIComponent(svg)}`) })
      .catch(() => { if (!stop) setSrc(null) })
    return () => { stop = true }
  }, [value])
  return src ? <img className="qr" src={src} alt={label} width={240} height={240} /> : null
}
