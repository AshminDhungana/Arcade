import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Table, Th, Td } from './Table';

describe('Table', () => {
  it('renders table wrapper with correct classes', () => {
    render(
      <Table>
        <thead>
          <tr>
            <Th>Header</Th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <Td>Cell</Td>
          </tr>
        </tbody>
      </Table>
    );

    const tableWrapper = screen.getByRole('table').parentElement;
    expect(tableWrapper).toHaveClass('overflow-x-auto');
    expect(tableWrapper).toHaveClass('rounded-lg');
    expect(tableWrapper).toHaveClass('border-border');
  });

  it('renders Th with correct classes', () => {
    render(
      <Table>
        <thead>
          <tr>
            <Th>Header</Th>
          </tr>
        </thead>
      </Table>
    );

    const th = screen.getByRole('columnheader');
    expect(th).toHaveClass('px-4');
    expect(th).toHaveClass('py-3');
    expect(th).toHaveClass('bg-secondary/60');
    expect(th).toHaveClass('text-muted-foreground');
    expect(th).toHaveClass('font-medium');
  });

  it('renders Td with correct classes', () => {
    render(
      <Table>
        <tbody>
          <tr>
            <Td>Cell</Td>
          </tr>
        </tbody>
      </Table>
    );

    const td = screen.getByRole('cell');
    expect(td).toHaveClass('px-4');
    expect(td).toHaveClass('py-3');
    expect(td).toHaveClass('text-foreground');
  });

  it('forwards additional className to Table, Th, and Td', () => {
    render(
      <Table className="custom-table">
        <thead>
          <tr>
            <Th className="custom-th">Header</Th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <Td className="custom-td">Cell</Td>
          </tr>
        </tbody>
      </Table>
    );

    expect(screen.getByRole('table').parentElement).toHaveClass('custom-table');
    expect(screen.getByRole('columnheader')).toHaveClass('custom-th');
    expect(screen.getByRole('cell')).toHaveClass('custom-td');
  });
});
