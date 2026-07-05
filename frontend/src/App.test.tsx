import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import App from './App';

const createWrapper = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { staleTime: Infinity } },
  });
  return ({ children }: { children: ReactNode }) => (
    <BrowserRouter>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </BrowserRouter>
  );
};

describe('App', () => {
  it('renders login page at /login', () => {
    window.history.pushState({}, '', '/login');
    render(<App />, { wrapper: createWrapper() });
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });
});
