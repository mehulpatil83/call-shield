/** The phone's body, drawn once as an image with a transparent window for the screen. The live call shows through the window and the
 *  holographic foil is laid over the metal. Returns '' where canvas drawing is not available (tests, very old browsers). */
export const PHONE_W = 992
export const PHONE_H = 1600
export const PHONE_RATIO = PHONE_W / PHONE_H

const BODY = 16, BEZEL = 30, BODY_R = 130, SCREEN_R = 100
/** The window, as percentages of the card, for the content layer. */
export const SCREEN = {
  left: `${((BODY + BEZEL) / PHONE_W) * 100}%`, top: `${((BODY + BEZEL) / PHONE_H) * 100}%`,
  width: `${((PHONE_W - 2 * (BODY + BEZEL)) / PHONE_W) * 100}%`, height: `${((PHONE_H - 2 * (BODY + BEZEL)) / PHONE_H) * 100}%`,
  borderRadius: `${(SCREEN_R / (PHONE_W - 2 * (BODY + BEZEL))) * 100}% / ${(SCREEN_R / (PHONE_H - 2 * (BODY + BEZEL))) * 100}%`,
}
/** Width of the sparkling edge, as a percent of the card width: the bezel plus the margin of the body. */
export const SCREEN_FRAME = ((BODY + BEZEL) / PHONE_W) * 100

let cached: string | null = null

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

export function phoneBezel(): string {
  if (cached !== null) return cached
  cached = ''
  if (typeof document === 'undefined') return cached
  const canvas = document.createElement('canvas')
  canvas.width = PHONE_W
  canvas.height = PHONE_H
  const ctx = canvas.getContext('2d')
  if (!ctx) return cached
  // side buttons
  ctx.fillStyle = '#1b1e27'
  roundRect(ctx, 2, 300, 16, 150, 6); ctx.fill()
  roundRect(ctx, 2, 480, 16, 150, 6); ctx.fill()
  roundRect(ctx, PHONE_W - 18, 380, 16, 210, 6); ctx.fill()
  // body: dark brushed metal
  const metal = ctx.createLinearGradient(0, 0, PHONE_W, PHONE_H)
  metal.addColorStop(0, '#3a3f4e'); metal.addColorStop(0.45, '#14161d'); metal.addColorStop(1, '#2b2f3b')
  ctx.fillStyle = metal
  roundRect(ctx, BODY, BODY, PHONE_W - 2 * BODY, PHONE_H - 2 * BODY, BODY_R); ctx.fill()
  ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(255,255,255,0.16)'
  roundRect(ctx, BODY + 1.5, BODY + 1.5, PHONE_W - 2 * BODY - 3, PHONE_H - 2 * BODY - 3, BODY_R - 1.5); ctx.stroke()
  // the window for the screen
  ctx.globalCompositeOperation = 'destination-out'
  roundRect(ctx, BODY + BEZEL, BODY + BEZEL, PHONE_W - 2 * (BODY + BEZEL), PHONE_H - 2 * (BODY + BEZEL), SCREEN_R); ctx.fill()
  ctx.globalCompositeOperation = 'source-over'
  // inner lip of the window, and the camera island
  ctx.lineWidth = 4; ctx.strokeStyle = 'rgba(0,0,0,0.55)'
  roundRect(ctx, BODY + BEZEL, BODY + BEZEL, PHONE_W - 2 * (BODY + BEZEL), PHONE_H - 2 * (BODY + BEZEL), SCREEN_R); ctx.stroke()
  ctx.fillStyle = '#05060a'
  roundRect(ctx, PHONE_W / 2 - 100, BODY + BEZEL + 22, 200, 56, 28); ctx.fill()
  try { cached = canvas.toDataURL('image/png') } catch { cached = '' }
  return cached
}
