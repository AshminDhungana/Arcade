/**
 * Physical-keyboard PIN entry helper — pure DOM helper.
 *
 * Listens for document-level keydown events while `modal` is visible and maps
 * digits/Backspace/Enter/Escape to PIN entry callbacks. Returns a cleanup
 * function that removes the listener.
 */

export interface PinKeyboardCallbacks {
  onDigit: (digit: string) => void;
  onBackspace: () => void;
  onSubmit: () => void;
  onCancel: () => void;
}

/** Bind keyboard PIN entry to a modal. Returns a cleanup function. */
export function bindPinKeyboard(
  modal: HTMLElement,
  callbacks: PinKeyboardCallbacks
): () => void {
  const handleKeyDown = (e: KeyboardEvent): void => {
    if (e.ctrlKey || e.altKey || e.metaKey) return;
    if (!modal.classList.contains('visible')) return;

    if (e.key >= '0' && e.key <= '9') {
      callbacks.onDigit(e.key);
    } else if (e.key === 'Backspace') {
      callbacks.onBackspace();
    } else if (e.key === 'Enter' || e.key === 'NumpadEnter') {
      e.preventDefault();
      callbacks.onSubmit();
    } else if (e.key === 'Escape') {
      callbacks.onCancel();
    }
  };

  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}
