import markUrl from '@/assets/stilliu-mark.png'

/**
 * BrandMark — the Stilliu logo.
 *
 * A fingerprint whose ridges resolve into an S, sitting above four waves. The
 * figure is the product argument in one image: a fingerprint is what makes one
 * person's hand unmistakable from every other, and the waves are the signal it
 * is measured against — which is exactly what the tool does to your prose.
 *
 * This is the supplied artwork rather than a traced copy of it, so the mark in
 * the app is the mark you designed. The source export carried ~160px of empty
 * margin on every side, which is trimmed in the committed asset: at topbar size
 * the padding alone would have shrunk the visible mark to a few pixels inside
 * its own box.
 *
 * The PNG keeps its own dark ink instead of inheriting `currentColor`. An <img>
 * cannot be recoloured by CSS, which is the one trade for using the real asset;
 * the ink is near-black and the topbar is paper-white, so it reads correctly on
 * the only surface it currently sits on.
 */

interface Props {
  /** Rendered height in px. Width follows the artwork's own 0.76 aspect ratio. */
  size?: number
  className?: string
}

export default function BrandMark({ size = 26, className }: Props) {
  return (
    <img
      className={className}
      src={markUrl}
      // Height-driven: the artwork is taller than it is wide, so constraining
      // height is what makes the mark align with adjacent text.
      height={size}
      width={Math.round(size * 0.762)}
      alt=""
      // Decorative here — the wordmark beside it already says "Stilliu", so
      // announcing the logo too would just repeat the name to a screen reader.
      aria-hidden="true"
      draggable={false}
      style={{ display: 'block', objectFit: 'contain' }}
    />
  )
}
