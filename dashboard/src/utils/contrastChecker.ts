/**
 * Color Contrast Checker Utility
 * 
 * Validates WCAG 2.1 AA compliance for color combinations.
 * Minimum contrast ratio: 4.5:1 for normal text, 3:1 for large text (18pt+)
 */

export interface ColorPair {
  foreground: string;
  background: string;
  usage: string;
  element?: string;
}

export interface ContrastResult {
  pair: ColorPair;
  ratio: number;
  passes: boolean;
  level: 'AAA' | 'AA' | 'FAIL';
  recommendation?: string;
}

/**
 * Convert hex color to RGB
 */
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  // Remove # if present
  hex = hex.replace('#', '');
  
  // Handle 3-digit hex
  if (hex.length === 3) {
    hex = hex.split('').map(c => c + c).join('');
  }
  
  const result = /^([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

/**
 * Calculate relative luminance
 * https://www.w3.org/TR/WCAG20-TECHS/G17.html
 */
function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map(c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Calculate contrast ratio between two colors
 * https://www.w3.org/TR/WCAG20-TECHS/G17.html
 */
export function getContrastRatio(color1: string, color2: string): number {
  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);
  
  if (!rgb1 || !rgb2) {
    throw new Error(`Invalid color format: ${color1} or ${color2}`);
  }
  
  const lum1 = getLuminance(rgb1.r, rgb1.g, rgb1.b);
  const lum2 = getLuminance(rgb2.r, rgb2.g, rgb2.b);
  
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Check if contrast ratio meets WCAG standards
 */
export function checkContrast(
  foreground: string,
  background: string,
  usage: string,
  element?: string
): ContrastResult {
  const ratio = getContrastRatio(foreground, background);
  
  // WCAG 2.1 AA requires 4.5:1 for normal text, 3:1 for large text
  // AAA requires 7:1 for normal text, 4.5:1 for large text
  const passesAA = ratio >= 4.5;
  const passesAAA = ratio >= 7.0;
  
  let level: 'AAA' | 'AA' | 'FAIL';
  let recommendation: string | undefined;
  
  if (passesAAA) {
    level = 'AAA';
  } else if (passesAA) {
    level = 'AA';
  } else {
    level = 'FAIL';
    recommendation = `Increase contrast to at least 4.5:1. Current: ${ratio.toFixed(2)}:1`;
  }
  
  return {
    pair: { foreground, background, usage, element },
    ratio: parseFloat(ratio.toFixed(2)),
    passes: passesAA,
    level,
    recommendation
  };
}

/**
 * Audit all color combinations in the design system
 */
export function auditColorCombinations(): ContrastResult[] {
  const results: ContrastResult[] = [];
  
  // Dark Mode Colors
  const darkMode = {
    background: '#020617',
    backgroundSecondary: '#0F172A',
    backgroundTertiary: '#1E293B',
    textPrimary: '#F8FAFC',
    textSecondary: '#CBD5E1',
    textMuted: '#94A3B8', // Updated for WCAG AA compliance
    positive: '#22C55E',
    negative: '#EF4444',
    border: 'rgba(255, 255, 255, 0.1)', // Will need special handling
  };
  
  // Light Mode Colors
  const lightMode = {
    background: '#FFFFFF',
    backgroundSecondary: '#F8FAFC',
    backgroundTertiary: '#F1F5F9',
    textPrimary: '#0F172A',
    textSecondary: '#475569',
    textMuted: '#475569', // Updated for WCAG AA compliance
    positive: '#15803D', // Updated for WCAG AA compliance
    negative: '#B91C1C', // Updated for WCAG AA compliance
    border: '#E2E8F0',
  };
  
  // Dark Mode Audits
  results.push(checkContrast(darkMode.textPrimary, darkMode.background, 'Dark Mode: Primary text on main background', 'body, headings'));
  results.push(checkContrast(darkMode.textPrimary, darkMode.backgroundSecondary, 'Dark Mode: Primary text on secondary background', 'cards, panels'));
  results.push(checkContrast(darkMode.textPrimary, darkMode.backgroundTertiary, 'Dark Mode: Primary text on tertiary background', 'nested elements'));
  
  results.push(checkContrast(darkMode.textSecondary, darkMode.background, 'Dark Mode: Secondary text on main background', 'labels, metadata'));
  results.push(checkContrast(darkMode.textSecondary, darkMode.backgroundSecondary, 'Dark Mode: Secondary text on secondary background', 'card labels'));
  results.push(checkContrast(darkMode.textSecondary, darkMode.backgroundTertiary, 'Dark Mode: Secondary text on tertiary background', 'nested labels'));
  
  results.push(checkContrast(darkMode.textMuted, darkMode.background, 'Dark Mode: Muted text on main background', 'disabled, hints'));
  results.push(checkContrast(darkMode.textMuted, darkMode.backgroundSecondary, 'Dark Mode: Muted text on secondary background', 'card hints'));
  
  results.push(checkContrast(darkMode.positive, darkMode.background, 'Dark Mode: Positive values on main background', 'gains, success'));
  results.push(checkContrast(darkMode.positive, darkMode.backgroundSecondary, 'Dark Mode: Positive values on secondary background', 'card gains'));
  
  results.push(checkContrast(darkMode.negative, darkMode.background, 'Dark Mode: Negative values on main background', 'losses, errors'));
  results.push(checkContrast(darkMode.negative, darkMode.backgroundSecondary, 'Dark Mode: Negative values on secondary background', 'card losses'));
  
  // Light Mode Audits
  results.push(checkContrast(lightMode.textPrimary, lightMode.background, 'Light Mode: Primary text on main background', 'body, headings'));
  results.push(checkContrast(lightMode.textPrimary, lightMode.backgroundSecondary, 'Light Mode: Primary text on secondary background', 'cards, panels'));
  results.push(checkContrast(lightMode.textPrimary, lightMode.backgroundTertiary, 'Light Mode: Primary text on tertiary background', 'nested elements'));
  
  results.push(checkContrast(lightMode.textSecondary, lightMode.background, 'Light Mode: Secondary text on main background', 'labels, metadata'));
  results.push(checkContrast(lightMode.textSecondary, lightMode.backgroundSecondary, 'Light Mode: Secondary text on secondary background', 'card labels'));
  results.push(checkContrast(lightMode.textSecondary, lightMode.backgroundTertiary, 'Light Mode: Secondary text on tertiary background', 'nested labels'));
  
  results.push(checkContrast(lightMode.textMuted, lightMode.background, 'Light Mode: Muted text on main background', 'disabled, hints'));
  results.push(checkContrast(lightMode.textMuted, lightMode.backgroundSecondary, 'Light Mode: Muted text on secondary background', 'card hints'));
  results.push(checkContrast(lightMode.textMuted, lightMode.backgroundTertiary, 'Light Mode: Muted text on tertiary background', 'nested hints'));
  
  results.push(checkContrast(lightMode.positive, lightMode.background, 'Light Mode: Positive values on main background', 'gains, success'));
  results.push(checkContrast(lightMode.positive, lightMode.backgroundSecondary, 'Light Mode: Positive values on secondary background', 'card gains'));
  results.push(checkContrast(lightMode.positive, lightMode.backgroundTertiary, 'Light Mode: Positive values on tertiary background', 'nested gains'));
  
  results.push(checkContrast(lightMode.negative, lightMode.background, 'Light Mode: Negative values on main background', 'losses, errors'));
  results.push(checkContrast(lightMode.negative, lightMode.backgroundSecondary, 'Light Mode: Negative values on secondary background', 'card losses'));
  results.push(checkContrast(lightMode.negative, lightMode.backgroundTertiary, 'Light Mode: Negative values on tertiary background', 'nested losses'));
  
  return results;
}

/**
 * Generate a human-readable report
 */
export function generateContrastReport(results: ContrastResult[]): string {
  const passed = results.filter(r => r.passes);
  const failed = results.filter(r => !r.passes);
  
  let report = '# Color Contrast Audit Report\n\n';
  report += `**Total Combinations Tested:** ${results.length}\n`;
  report += `**Passed (AA):** ${passed.length}\n`;
  report += `**Failed:** ${failed.length}\n\n`;
  
  if (failed.length > 0) {
    report += '## ❌ Failed Combinations\n\n';
    failed.forEach(result => {
      report += `### ${result.pair.usage}\n`;
      report += `- **Foreground:** ${result.pair.foreground}\n`;
      report += `- **Background:** ${result.pair.background}\n`;
      report += `- **Contrast Ratio:** ${result.ratio}:1\n`;
      report += `- **Status:** ${result.level}\n`;
      if (result.recommendation) {
        report += `- **Recommendation:** ${result.recommendation}\n`;
      }
      report += '\n';
    });
  }
  
  report += '## ✅ Passed Combinations\n\n';
  
  // Group by theme
  const darkModePassed = passed.filter(r => r.pair.usage.startsWith('Dark Mode'));
  const lightModePassed = passed.filter(r => r.pair.usage.startsWith('Light Mode'));
  
  if (darkModePassed.length > 0) {
    report += '### Dark Mode\n\n';
    report += '| Usage | Foreground | Background | Ratio | Level |\n';
    report += '|-------|------------|------------|-------|-------|\n';
    darkModePassed.forEach(result => {
      const usage = result.pair.usage.replace('Dark Mode: ', '');
      report += `| ${usage} | ${result.pair.foreground} | ${result.pair.background} | ${result.ratio}:1 | ${result.level} |\n`;
    });
    report += '\n';
  }
  
  if (lightModePassed.length > 0) {
    report += '### Light Mode\n\n';
    report += '| Usage | Foreground | Background | Ratio | Level |\n';
    report += '|-------|------------|------------|-------|-------|\n';
    lightModePassed.forEach(result => {
      const usage = result.pair.usage.replace('Light Mode: ', '');
      report += `| ${usage} | ${result.pair.foreground} | ${result.pair.background} | ${result.ratio}:1 | ${result.level} |\n`;
    });
    report += '\n';
  }
  
  return report;
}
