import { describe, it, expect } from 'vitest';
import {
  getContrastRatio,
  checkContrast,
  auditColorCombinations,
  generateContrastReport,
  type ContrastResult
} from '../contrastChecker';

describe('contrastChecker', () => {
  describe('getContrastRatio', () => {
    it('should calculate correct contrast ratio for black and white', () => {
      const ratio = getContrastRatio('#000000', '#FFFFFF');
      expect(ratio).toBe(21); // Maximum contrast
    });

    it('should calculate correct contrast ratio for same colors', () => {
      const ratio = getContrastRatio('#FFFFFF', '#FFFFFF');
      expect(ratio).toBe(1); // Minimum contrast
    });

    it('should handle 3-digit hex colors', () => {
      const ratio = getContrastRatio('#000', '#FFF');
      expect(ratio).toBe(21);
    });

    it('should handle colors without # prefix', () => {
      const ratio = getContrastRatio('000000', 'FFFFFF');
      expect(ratio).toBe(21);
    });

    it('should calculate dark mode primary text contrast', () => {
      // #F8FAFC on #020617
      const ratio = getContrastRatio('#F8FAFC', '#020617');
      expect(ratio).toBeGreaterThan(15); // Should exceed AAA (7:1)
    });

    it('should calculate light mode primary text contrast', () => {
      // #0F172A on #FFFFFF
      const ratio = getContrastRatio('#0F172A', '#FFFFFF');
      expect(ratio).toBeGreaterThan(15); // Should exceed AAA (7:1)
    });
  });

  describe('checkContrast', () => {
    it('should pass for high contrast combinations', () => {
      const result = checkContrast('#000000', '#FFFFFF', 'Test: Black on white');
      expect(result.passes).toBe(true);
      expect(result.level).toBe('AAA');
      expect(result.ratio).toBe(21);
    });

    it('should fail for low contrast combinations', () => {
      const result = checkContrast('#888888', '#999999', 'Test: Low contrast');
      expect(result.passes).toBe(false);
      expect(result.level).toBe('FAIL');
      expect(result.recommendation).toBeDefined();
    });

    it('should classify AA level correctly', () => {
      // A combination that passes AA (4.5:1) but not AAA (7:1)
      const result = checkContrast('#767676', '#FFFFFF', 'Test: AA level');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
      expect(result.ratio).toBeLessThan(7);
      expect(result.level).toBe('AA');
    });

    it('should include element information when provided', () => {
      const result = checkContrast('#000000', '#FFFFFF', 'Test', 'button');
      expect(result.pair.element).toBe('button');
    });
  });

  describe('auditColorCombinations', () => {
    it('should audit all color combinations', () => {
      const results = auditColorCombinations();
      expect(results.length).toBeGreaterThan(0);
    });

    it('should include both dark and light mode audits', () => {
      const results = auditColorCombinations();
      const darkModeResults = results.filter(r => r.pair.usage.includes('Dark Mode'));
      const lightModeResults = results.filter(r => r.pair.usage.includes('Light Mode'));
      
      expect(darkModeResults.length).toBeGreaterThan(0);
      expect(lightModeResults.length).toBeGreaterThan(0);
    });

    it('should test primary text combinations', () => {
      const results = auditColorCombinations();
      const primaryTextTests = results.filter(r => r.pair.usage.includes('Primary text'));
      
      expect(primaryTextTests.length).toBeGreaterThan(0);
    });

    it('should test positive/negative value combinations', () => {
      const results = auditColorCombinations();
      const positiveTests = results.filter(r => r.pair.usage.includes('Positive'));
      const negativeTests = results.filter(r => r.pair.usage.includes('Negative'));
      
      expect(positiveTests.length).toBeGreaterThan(0);
      expect(negativeTests.length).toBeGreaterThan(0);
    });

    it('should have all combinations pass WCAG AA', () => {
      const results = auditColorCombinations();
      const failed = results.filter(r => !r.passes);
      
      if (failed.length > 0) {
        console.error('Failed combinations:', failed);
      }
      
      expect(failed.length).toBe(0);
    });
  });

  describe('WCAG 2.1 AA Compliance - Dark Mode', () => {
    it('should pass for primary text on main background', () => {
      const result = checkContrast('#F8FAFC', '#020617', 'Dark Mode: Primary text');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('should pass for primary text on secondary background', () => {
      const result = checkContrast('#F8FAFC', '#0F172A', 'Dark Mode: Primary text on cards');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('should pass for secondary text on main background', () => {
      const result = checkContrast('#CBD5E1', '#020617', 'Dark Mode: Secondary text');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('should pass for muted text on main background', () => {
      const result = checkContrast('#94A3B8', '#020617', 'Dark Mode: Muted text');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('should pass for positive values on main background', () => {
      const result = checkContrast('#22C55E', '#020617', 'Dark Mode: Positive values');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('should pass for negative values on main background', () => {
      const result = checkContrast('#EF4444', '#020617', 'Dark Mode: Negative values');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
    });
  });

  describe('WCAG 2.1 AA Compliance - Light Mode', () => {
    it('should pass for primary text on main background', () => {
      const result = checkContrast('#0F172A', '#FFFFFF', 'Light Mode: Primary text');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('should pass for primary text on secondary background', () => {
      const result = checkContrast('#0F172A', '#F8FAFC', 'Light Mode: Primary text on cards');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('should pass for secondary text on main background', () => {
      const result = checkContrast('#475569', '#FFFFFF', 'Light Mode: Secondary text');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('should pass for muted text on main background', () => {
      const result = checkContrast('#475569', '#FFFFFF', 'Light Mode: Muted text');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('should pass for positive values on main background', () => {
      const result = checkContrast('#15803D', '#FFFFFF', 'Light Mode: Positive values');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('should pass for negative values on main background', () => {
      const result = checkContrast('#B91C1C', '#FFFFFF', 'Light Mode: Negative values');
      expect(result.passes).toBe(true);
      expect(result.ratio).toBeGreaterThanOrEqual(4.5);
    });
  });

  describe('generateContrastReport', () => {
    it('should generate a report with summary statistics', () => {
      const results = auditColorCombinations();
      const report = generateContrastReport(results);
      
      expect(report).toContain('Color Contrast Audit Report');
      expect(report).toContain('Total Combinations Tested');
      expect(report).toContain('Passed (AA)');
      expect(report).toContain('Failed');
    });

    it('should include failed combinations section if any fail', () => {
      const failedResult: ContrastResult = {
        pair: {
          foreground: '#888888',
          background: '#999999',
          usage: 'Test: Low contrast'
        },
        ratio: 1.5,
        passes: false,
        level: 'FAIL',
        recommendation: 'Increase contrast'
      };
      
      const report = generateContrastReport([failedResult]);
      expect(report).toContain('Failed Combinations');
      expect(report).toContain('Recommendation');
    });

    it('should separate dark mode and light mode results', () => {
      const results = auditColorCombinations();
      const report = generateContrastReport(results);
      
      expect(report).toContain('Dark Mode');
      expect(report).toContain('Light Mode');
    });

    it('should include contrast ratios in the report', () => {
      const results = auditColorCombinations();
      const report = generateContrastReport(results);
      
      // Should contain ratio format like "15.8:1"
      expect(report).toMatch(/\d+\.\d+:1/);
    });
  });

  describe('Property: All text meets minimum contrast', () => {
    it('should ensure all text/background combinations meet 4.5:1 minimum', () => {
      const results = auditColorCombinations();
      
      results.forEach(result => {
        expect(result.ratio).toBeGreaterThanOrEqual(4.5);
        expect(result.passes).toBe(true);
      });
    });
  });

  describe('Property: Contrast ratios are symmetric', () => {
    it('should calculate same ratio regardless of color order', () => {
      const ratio1 = getContrastRatio('#000000', '#FFFFFF');
      const ratio2 = getContrastRatio('#FFFFFF', '#000000');
      
      expect(ratio1).toBe(ratio2);
    });

    it('should be symmetric for all color pairs', () => {
      const colors = ['#020617', '#F8FAFC', '#0F172A', '#FFFFFF', '#22C55E', '#EF4444'];
      
      for (let i = 0; i < colors.length; i++) {
        for (let j = i + 1; j < colors.length; j++) {
          const ratio1 = getContrastRatio(colors[i], colors[j]);
          const ratio2 = getContrastRatio(colors[j], colors[i]);
          expect(ratio1).toBe(ratio2);
        }
      }
    });
  });

  describe('Property: Contrast ratio bounds', () => {
    it('should have contrast ratio between 1 and 21', () => {
      const results = auditColorCombinations();
      
      results.forEach(result => {
        expect(result.ratio).toBeGreaterThanOrEqual(1);
        expect(result.ratio).toBeLessThanOrEqual(21);
      });
    });
  });
});
