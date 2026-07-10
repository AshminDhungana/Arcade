import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Tabs } from './Tabs';

describe('Tabs', () => {
  it('renders tabs and calls onChange on click', () => {
    const onChange = vi.fn();
    render(
      <Tabs
        tabs={[{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }]}
        active="a"
        onChange={onChange}
      />
    );

    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(2);
    expect(tabs[0]).toHaveTextContent('A');
    expect(tabs[1]).toHaveTextContent('B');

    expect(tabs[0]).toHaveAttribute('aria-selected', 'true');
    expect(tabs[1]).toHaveAttribute('aria-selected', 'false');

    fireEvent.click(tabs[1]);
    expect(onChange).toHaveBeenCalledWith('b');
  });
});
