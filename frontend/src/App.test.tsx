import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

const createWrapper = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { staleTime: Infinity } },
  });
  // eslint-disable-next-line react/display-name
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
};

describe('App', () => {
  it('shows connection status indicator', () => {
    render(<App />, { wrapper: createWrapper() });
    expect(screen.getByLabelText(/connection status/i)).toBeInTheDocument();
  });

  it('shows the dashboard title', () => {
    render(<App />, { wrapper: createWrapper() });
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Arcade Dashboard',
    );
  });
});
