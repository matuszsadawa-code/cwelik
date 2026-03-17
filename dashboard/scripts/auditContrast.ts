#!/usr/bin/env node
/**
 * Color Contrast Audit CLI Tool
 * 
 * Runs a comprehensive audit of all color combinations in the dashboard
 * and generates a detailed report.
 */

import { auditColorCombinations, generateContrastReport } from '../src/utils/contrastChecker';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function main() {
  console.log('🎨 Running Color Contrast Audit...\n');
  
  // Run the audit
  const results = auditColorCombinations();
  
  // Generate the report
  const report = generateContrastReport(results);
  
  // Print to console
  console.log(report);
  
  // Save to file
  const outputPath = path.join(__dirname, '..', 'COLOR_CONTRAST_AUDIT.md');
  fs.writeFileSync(outputPath, report, 'utf-8');
  
  console.log(`\n✅ Report saved to: ${outputPath}`);
  
  // Exit with error code if any tests failed
  const failed = results.filter(r => !r.passes);
  if (failed.length > 0) {
    console.error(`\n❌ ${failed.length} color combinations failed WCAG AA compliance`);
    process.exit(1);
  } else {
    console.log(`\n✅ All ${results.length} color combinations pass WCAG 2.1 AA compliance!`);
    process.exit(0);
  }
}

main();
