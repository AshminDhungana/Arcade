import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { NavShell } from './NavShell';
import { useFeatureFlagStore } from '@/store/featureFlagStore';

describe('NavShell', () => {
  it('hides Members nav when enable_members is false', () => {
    useFeatureFlagStore.setState({
      flags: { ...useFeatureFlagStore.getState().flags, enable_members: false },
    });
    render(
      <MemoryRouter>
        <NavShell>
          <div>child</div>
        </NavShell>
      </MemoryRouter>
    );
    expect(screen.queryByText('Members')).not.toBeInTheDocument();
  });

  it('shows active Members nav when enable_members is true and on /members', () => {
    useFeatureFlagStore.setState({
      flags: { ...useFeatureFlagStore.getState().flags, enable_members: true },
    });
    render(
      <MemoryRouter initialEntries={['/members']}>
        <NavShell>
          <div>child</div>
        </NavShell>
      </MemoryRouter>
    );
    const link = screen.getByText('Members').closest('a')!;
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('aria-current', 'page');
  });
});
