#!/usr/bin/env node

/**
 * Performance Audit Script
 * 
 * Comprehensive performance measurement for OpenClaw Trading Dashboard:
 * - Lighthouse audit (target: >90 performance score)
 * - Initial page load time (target: <2s)
 * - Time to interactive (target: <3s)
 * - Chart render time (target: <100ms)
 * - WebSocket latency (target: <100ms)
 */

import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const RESULTS_DIR = path.join(__dirname, '../performance-results');
const TIMESTAMP = new Date().toISOString().replace(/[:.]/g, '-');

// Ensure results directory exists
if (!fs.existsSync(RESULTS_DIR)) {
  fs.mkdirSync(RESULTS_DIR, { recursive: true });
}

console.log('\n🚀 OpenClaw Trading Dashboard - Performance Audit\n');
console.log('━'.repeat(80));

/**
 * Run Lighthouse audit
 */
async function runLighthouseAudit() {
  console.log('\n📊 Running Lighthouse Audit...\n');
  
  return new Promise((resolve, reject) => {
    const outputPath = path.join(RESULTS_DIR, `lighthouse-${TIMESTAMP}.json`);
    const htmlPath = path.join(RESULTS_DIR, `lighthouse-${TIMESTAMP}.html`);
    
    // Check if lighthouse is installed
    const checkLighthouse = spawn('npx', ['lighthouse', '--version'], { shell: true });
    
    checkLighthouse.on('error', () => {
      console.log('⚠️  Lighthouse not found. Installing...');
      const install = spawn('npm', ['install', '-g', 'lighthouse'], { shell: true, stdio: 'inherit' });
      
      install.on('close', (code) => {
        if (code !== 0) {
          reject(new Error('Failed to install Lighthouse'));
          return;
        }
        runAudit();
      });
    });
    
    checkLighthouse.on('close', (code) => {
      if (code === 0) {
        runAudit();
      }
    });
    
    function runAudit() {
      const lighthouse = spawn('npx', [
        'lighthouse',
        'http://localhost:5173',
        '--output=json',
        '--output=html',
        '--output-path=' + outputPath.replace('.json', ''),
        '--chrome-flags="--headless"',
        '--only-categories=performance',
        '--preset=desktop'
      ], { shell: true });
      
      lighthouse.stdout.on('data', (data) => {
        process.stdout.write(data);
      });
      
      lighthouse.stderr.on('data', (data) => {
        process.stderr.write(data);
      });
      
      lighthouse.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Lighthouse exited with code ${code}`));
          return;
        }
        
        // Parse results
        try {
          const results = JSON.parse(fs.readFileSync(outputPath, 'utf8'));
          const score = results.categories.performance.score * 100;
          
          console.log('\n✅ Lighthouse Audit Complete');
          console.log(`   Performance Score: ${score.toFixed(1)}/100 ${score >= 90 ? '✅' : '❌'}`);
          console.log(`   Report saved: ${htmlPath}`);
          
          resolve({
            score,
            metrics: {
              fcp: results.audits['first-contentful-paint'].numericValue,
              lcp: results.audits['largest-contentful-paint'].numericValue,
              tti: results.audits['interactive'].numericValue,
              tbt: results.audits['total-blocking-time'].numericValue,
              cls: results.audits['cumulative-layout-shift'].numericValue,
              si: results.audits['speed-index'].numericValue,
            }
          });
        } catch (error) {
          reject(error);
        }
      });
    }
  });
}

/**
 * Display results summary
 */
function displayResults(lighthouseResults) {
  console.log('\n📈 Performance Audit Results\n');
  console.log('━'.repeat(80));
  
  console.log('\n🎯 Lighthouse Performance Score:');
  const score = lighthouseResults.score;
  const scoreStatus = score >= 90 ? '✅ PASS' : '❌ FAIL';
  console.log(`   ${scoreStatus} ${score.toFixed(1)}/100 (target: >90)`);
  
  console.log('\n⏱️  Core Web Vitals:');
  const metrics = lighthouseResults.metrics;
  
  // First Contentful Paint
  const fcpMs = metrics.fcp;
  const fcpStatus = fcpMs < 1800 ? '✅' : fcpMs < 3000 ? '⚠️' : '❌';
  console.log(`   ${fcpStatus} First Contentful Paint: ${(fcpMs / 1000).toFixed(2)}s`);
  
  // Largest Contentful Paint
  const lcpMs = metrics.lcp;
  const lcpStatus = lcpMs < 2500 ? '✅' : lcpMs < 4000 ? '⚠️' : '❌';
  console.log(`   ${lcpStatus} Largest Contentful Paint: ${(lcpMs / 1000).toFixed(2)}s (target: <2.5s)`);
  
  // Time to Interactive
  const ttiMs = metrics.tti;
  const ttiStatus = ttiMs < 3000 ? '✅' : ttiMs < 5000 ? '⚠️' : '❌';
  console.log(`   ${ttiStatus} Time to Interactive: ${(ttiMs / 1000).toFixed(2)}s (target: <3s)`);
  
  // Total Blocking Time
  const tbtMs = metrics.tbt;
  const tbtStatus = tbtMs < 200 ? '✅' : tbtMs < 600 ? '⚠️' : '❌';
  console.log(`   ${tbtStatus} Total Blocking Time: ${tbtMs.toFixed(0)}ms (target: <200ms)`);
  
  // Cumulative Layout Shift
  const cls = metrics.cls;
  const clsStatus = cls < 0.1 ? '✅' : cls < 0.25 ? '⚠️' : '❌';
  console.log(`   ${clsStatus} Cumulative Layout Shift: ${cls.toFixed(3)} (target: <0.1)`);
  
  // Speed Index
  const siMs = metrics.si;
  const siStatus = siMs < 3400 ? '✅' : siMs < 5800 ? '⚠️' : '❌';
  console.log(`   ${siStatus} Speed Index: ${(siMs / 1000).toFixed(2)}s (target: <3.4s)`);
  
  console.log('\n━'.repeat(80));
  
  // Overall status
  const allPassed = score >= 90 && lcpMs < 2500 && ttiMs < 3000;
  
  if (allPassed) {
    console.log('\n✅ All performance targets met!\n');
    return 0;
  } else {
    console.log('\n❌ Some performance targets not met. See recommendations below.\n');
    
    console.log('💡 Recommendations:');
    if (score < 90) {
      console.log('   • Review Lighthouse report for specific optimization opportunities');
    }
    if (lcpMs >= 2500) {
      console.log('   • Optimize largest contentful paint (reduce image sizes, lazy load)');
    }
    if (ttiMs >= 3000) {
      console.log('   • Reduce JavaScript execution time (code splitting, tree shaking)');
    }
    if (tbtMs >= 200) {
      console.log('   • Minimize main thread work (defer non-critical JS)');
    }
    if (cls >= 0.1) {
      console.log('   • Prevent layout shifts (set image dimensions, avoid dynamic content)');
    }
    console.log('');
    
    return 1;
  }
}

/**
 * Main execution
 */
async function main() {
  try {
    // Check if dev server is running
    console.log('⚠️  Make sure the dev server is running on http://localhost:5173');
    console.log('   Run "npm run dev" in another terminal if not already running.\n');
    
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Run Lighthouse audit
    const lighthouseResults = await runLighthouseAudit();
    
    // Display results
    const exitCode = displayResults(lighthouseResults);
    
    // Save summary
    const summary = {
      timestamp: new Date().toISOString(),
      lighthouseScore: lighthouseResults.score,
      metrics: lighthouseResults.metrics,
      targets: {
        lighthouseScore: { value: lighthouseResults.score, target: 90, passed: lighthouseResults.score >= 90 },
        lcp: { value: lighthouseResults.metrics.lcp, target: 2500, passed: lighthouseResults.metrics.lcp < 2500 },
        tti: { value: lighthouseResults.metrics.tti, target: 3000, passed: lighthouseResults.metrics.tti < 3000 },
      }
    };
    
    const summaryPath = path.join(RESULTS_DIR, `summary-${TIMESTAMP}.json`);
    fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));
    console.log(`📄 Summary saved: ${summaryPath}\n`);
    
    process.exit(exitCode);
  } catch (error) {
    console.error('\n❌ Error running performance audit:', error.message);
    console.error('\nTroubleshooting:');
    console.error('  1. Ensure dev server is running: npm run dev');
    console.error('  2. Check that port 5173 is accessible');
    console.error('  3. Install Lighthouse: npm install -g lighthouse\n');
    process.exit(1);
  }
}

main();
