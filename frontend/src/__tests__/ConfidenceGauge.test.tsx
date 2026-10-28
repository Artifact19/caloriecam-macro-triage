import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ConfidenceGauge, confidenceBand } from '../components/ConfidenceGauge';

describe('ConfidenceGauge', () => {
  it('exposes the rounded percentage as an accessible meter', () => {
    render(<ConfidenceGauge confidence={0.9123} />);
    const meter = screen.getByRole('meter', { name: /prediction confidence/i });
    expect(meter).toHaveAttribute('aria-valuenow', '91');
    expect(screen.getByTestId('confidence-value')).toHaveTextContent('91%');
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('labels medium and low confidence with text, not only colour', () => {
    const { rerender } = render(<ConfidenceGauge confidence={0.55} />);
    expect(screen.getByText('Medium')).toBeInTheDocument();
    rerender(<ConfidenceGauge confidence={0.2} />);
    expect(screen.getByText('Low')).toBeInTheDocument();
  });

  it('clamps out-of-range values', () => {
    render(<ConfidenceGauge confidence={1.7} />);
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '100');
  });

  it('uses the triage thresholds 0.4 / 0.7 for bands', () => {
    expect(confidenceBand(0.7)).toBe('high');
    expect(confidenceBand(0.69999)).toBe('medium');
    expect(confidenceBand(0.4)).toBe('medium');
    expect(confidenceBand(0.39999)).toBe('low');
  });
});
