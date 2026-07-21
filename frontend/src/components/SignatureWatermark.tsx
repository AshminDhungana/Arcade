// frontend/src/components/SignatureWatermark.tsx
import { motion, useReducedMotion } from 'framer-motion';
import { SignatureMark } from './SignatureMark';

interface SignatureWatermarkProps {
  className?: string;
  /**
   * Current app theme. Colors are resolved explicitly from this prop rather
   * than Tailwind's `dark:` variant, because this app toggles a `data-theme`
   * attribute (not the `dark` class Tailwind's dark-mode variant expects) —
   * relying on `dark:` here meant the mark never actually switched color.
   */
  theme?: 'light' | 'dark';
}

/**
 * @description Faint, theme-aware signature watermark that reveals itself once
 * on mount with a slow left-to-right "signing" animation. Respects
 * prefers-reduced-motion by showing the signature instantly.
 */
export function SignatureWatermark({ className, theme = 'dark' }: SignatureWatermarkProps) {
  const reduceMotion = useReducedMotion();
  const colorClass = theme === 'dark' ? 'text-white' : 'text-neutral-900';

  if (reduceMotion) {
    return (
      <div className={`${className ?? ''} opacity-30 transition-colors duration-700`}>
        <SignatureMark className={`w-64 h-auto ${colorClass}`} />
      </div>
    );
  }

  return (
    <motion.div
      className={`${className ?? ''} transition-colors duration-700`}
      initial={{ clipPath: 'inset(0 100% 0 0)', opacity: 0 }}
      animate={{ clipPath: 'inset(0 0% 0 0)', opacity: 0.3 }}
      transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1], delay: 0.3 }}
    >
      <SignatureMark className={`w-64 h-auto ${colorClass}`} />
    </motion.div>
  );
}
