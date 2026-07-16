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
    expect(tableWrapper).toHaveClass('border-slate-700/50');
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
    expect(th).toHaveClass('px-3');
    expect(th).toHaveClass('py-2');
    expect(th).toHaveClass('text-left');
    expect(th).toHaveClass('text-xs');
    expect(th).toHaveClass('font-semibold');
    expect(th).toHaveClass('uppercase');
    expect(th).toHaveClass('tracking-wider');
    expect(th).toHaveClass('text-slate-400');
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
    expect(td).toHaveClass('px-3');
    expect(td).toHaveClass('py-2');
    expect(td).toHaveClass('text-sm');
    expect(td).toHaveClass('text-slate-200');
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
