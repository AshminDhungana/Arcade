/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { bindPinKeyboard } from '../../../src/renderer/components/pin-keyboard.js';

function fireKey(key: string, init: KeyboardEventInit = {}): boolean {
  return document.dispatchEvent(new KeyboardEvent('keydown', { key, cancelable: true, ...init }));
}

function makeCallbacks() {
  return {
    onDigit: vi.fn(),
    onBackspace: vi.fn(),
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
  };
}

describe('bindPinKeyboard', () => {
  let modal: HTMLElement;
  let cbs: ReturnType<typeof makeCallbacks>;

  beforeEach(() => {
    modal = document.createElement('div');
    modal.classList.add('visible');
    document.body.appendChild(modal);
    cbs = makeCallbacks();
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('routes digit keys 0-9 to onDigit', () => {
    bindPinKeyboard(modal, cbs);
    for (const d of '0123456789') fireKey(d);
    expect(cbs.onDigit).toHaveBeenCalledTimes(10);
    expect(cbs.onDigit).toHaveBeenNthCalledWith(1, '0');
    expect(cbs.onDigit).toHaveBeenNthCalledWith(10, '9');
  });

  it('routes Backspace to onBackspace', () => {
    bindPinKeyboard(modal, cbs);
    fireKey('Backspace');
    expect(cbs.onBackspace).toHaveBeenCalledTimes(1);
  });

  it('routes Enter and NumpadEnter to onSubmit and prevents default', () => {
    bindPinKeyboard(modal, cbs);
    expect(fireKey('Enter')).toBe(false);
    expect(fireKey('NumpadEnter')).toBe(false);
    expect(cbs.onSubmit).toHaveBeenCalledTimes(2);
  });

  it('routes Escape to onCancel', () => {
    bindPinKeyboard(modal, cbs);
    fireKey('Escape');
    expect(cbs.onCancel).toHaveBeenCalledTimes(1);
  });

  it('ignores keys with ctrl/alt/meta modifiers', () => {
    bindPinKeyboard(modal, cbs);
    fireKey('5', { ctrlKey: true });
    fireKey('5', { altKey: true });
    fireKey('5', { metaKey: true });
    expect(cbs.onDigit).not.toHaveBeenCalled();
  });

  it('ignores keys when the modal is not visible', () => {
    modal.classList.remove('visible');
    bindPinKeyboard(modal, cbs);
    fireKey('5');
    expect(cbs.onDigit).not.toHaveBeenCalled();
  });

  it('ignores non-PIN keys (letters, function keys)', () => {
    bindPinKeyboard(modal, cbs);
    fireKey('a');
    fireKey('F5');
    fireKey('ArrowUp');
    expect(cbs.onDigit).not.toHaveBeenCalled();
    expect(cbs.onBackspace).not.toHaveBeenCalled();
    expect(cbs.onSubmit).not.toHaveBeenCalled();
    expect(cbs.onCancel).not.toHaveBeenCalled();
  });

  it('cleanup removes the listener', () => {
    const cleanup = bindPinKeyboard(modal, cbs);
    cleanup();
    fireKey('5');
    expect(cbs.onDigit).not.toHaveBeenCalled();
  });
});
