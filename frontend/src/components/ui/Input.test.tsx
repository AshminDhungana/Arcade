import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Input } from './Input';

describe('Input', () => {
  it('renders label and error with role="alert" and aria-invalid="true"', () => {
    render(<Input label="Email" error="Required" name="email" />);

    // Label renders
    expect(screen.getByLabelText('Email')).toBeInTheDocument();

    // Error renders with role="alert" and contains the error text
    const error = screen.getByRole('alert');
    expect(error).toBeInTheDocument();
    expect(error).toHaveTextContent('Required');

    // Input has aria-invalid="true"
    const input = screen.getByLabelText('Email');
    expect(input).toHaveAttribute('aria-invalid', 'true');
  });

  it('renders without error and aria-invalid is absent/false', () => {
    render(<Input label="Email" name="email" />);

    // Label renders
    expect(screen.getByLabelText('Email')).toBeInTheDocument();

    // No error message
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();

    // Input does not have aria-invalid="true"
    const input = screen.getByLabelText('Email');
    expect(input).not.toHaveAttribute('aria-invalid', 'true');
  });
});
