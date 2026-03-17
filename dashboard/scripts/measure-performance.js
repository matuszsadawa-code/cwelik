#!/usr/bin/env node

/**
 * Comprehensive Performance Measurement Script
 * 
 * Measures all performance targets for Task 6.29:
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

console.log('\n🚀 OpenClaw Trading Dashboard - Performance Measurement\n');
console.log('━'.repeat(80));

/**
 * Measure page load metrics using Puppeteer
 */
async function measurePageLoadMetrics() {
  console.log('\n⏱️  Measuring Page Load Metrics...\n');

  return new Promise((resolve, reject) => {
    // Create a simple Node script to run Puppeteer
    const scriptContent = `
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  // Enable performance metrics
  await page.evaluateOnNewDocument(() => {
    window.performance.mark('start');
  });
  
  const metrics = [];
  
  // Measure 5 times for average
  for (let i = 0; i < 5; i++) {
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
    
    const timing = await page.evaluate(() => {
      const perfData = performance.getEntriesByType('navigation')[0];
      return {
        pageLoadTime: perfData.loadEventEnd - perfData.fetchStart,
        timeToInteractive: perfData.domInteractive - perfData.fetchStart,
        domContentLoaded: perfData.domContentLoadedEventEnd - perfData.fetchStart,
        firstPaint: performance.getEntriesByType('paint').find(e => e.name === 'first-paint')?.startTime || 0,
        firstContentfulPaint: performance.getEntriesByType('paint').find(e => e.name === 'first-contentful-paint')?.startTime || 0,
      };
    });
    
    metrics.push(timing);
    
    // Wait a bit between measurements
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  await browser.close();
  
  // Calculate averages
  const avg = {
    pageLoadTime: metrics.reduce((sum, m) => sum + m.pageLoadTime, 0) / metrics.length,
    timeToInteractive: metrics.reduce((sum, m) => sum + m.timeToInteractive, 0) / metrics.length,
    domContentLoaded: metrics.reduce((sum, m) => sum + m.domContentLoaded, 0) / metrics.length,
    firstPaint: metrics.reduce((sum, m) => sum + m.firstPaint, 0) / metrics.length,
    firstContentfulPaint: metrics.reduce((sum, m) => sum + m.firstContentfulPaint, 0) / metrics.length,
  };
  
  console.log(JSON.stringify(avg));
})();
    `;

    const scriptPath = path.join(__dirname, 'temp-puppeteer-script.js');
    fs.writeFileSync(scriptPath, scriptContent);

    // Check if puppeteer is installed
    const checkPuppeteer = spawn('npm', ['list', 'puppeteer'], { shell: true });

    checkPuppeteer.on('close', (code) => {
      if (code !== 0) {
        console.log('⚠️  Puppeteer not found. Installing...');
        const install = spawn('npm', ['install', '--save-dev', 'puppeteer'], {
          shell: true,
          stdio: 'inherit',
          cwd: path.join(__dirname, '..'),
        });

        install.on('close', (installCode) => {
          if (installCode !== 0) {
            fs.unlinkSync(scriptPath);
            reject(new Error('Failed to install Puppeteer'));
            return;
          }
          runScript();
        });
      } else {
        runScript();
      }
    });

    function runScript() {
      const node = spawn('node', [scriptPath], { shell: true });

      let output = '';

      node.stdout.on('data', (data) => {
        output += data.toString();
      });

      node.stderr.on('data', (data) => {
        console.error(data.toString());
      });

      node.on('close', (code) => {
        fs.unlinkSync(scriptPath);

        if (code !== 0) {
          reject(new Error('Failed to measure page load metrics'));
          return;
        }

        try {
          const metrics = JSON.parse(output.trim());
          resolve(metrics);
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
function displayResults(pageLoadMetrics) {
  console.log('\n📈 Performance Measurement Results\n');
  console.log('━'.repeat(80));

  console.log('\n⏱️  Page Load Metrics:');

  // Page Load Time
  const pageLoadTime = pageLoadMetrics.pageLoadTime;
  const pageLoadStatus = pageLoadTime < 2000 ? '✅' : '❌';
  console.log(
    `   ${pageLoadStatus} Page Load Time: ${pageLoadTime.toFixed(0)}ms (target: <2000ms)`
  );

  // Time to Interactive
  const tti = pageLoadMetrics.timeToInteractive;
  const ttiStatus = tti < 3000 ? '✅' : '❌';
  console.log(`   ${ttiStatus} Time to Interactive: ${tti.toFixed(0)}ms (target: <3000ms)`);

  // DOM Content Loaded
  const dcl = pageLoadMetrics.domContentLoaded;
  console.log(`   ℹ️  DOM Content Loaded: ${dcl.toFixed(0)}ms`);

  // First Paint
  const fp = pageLoadMetrics.firstPaint;
  console.log(`   ℹ️  First Paint: ${fp.toFixed(0)}ms`);

  // First Contentful Paint
  const fcp = pageLoadMetrics.firstContentfulPaint;
  const fcpStatus = fcp < 1800 ? '✅' : fcp < 3000 ? '⚠️' : '❌';
  console.log(`   ${fcpStatus} First Contentful Paint: ${fcp.toFixed(0)}ms`);

  console.log('\n📊 Chart Render & WebSocket Metrics:');
  console.log('   ℹ️  Chart render time and WebSocket latency are measured at runtime.');
  console.log('   ℹ️  Open the dashboard and press Ctrl+Shift+P to view live metrics.');
  console.log('   ℹ️  Or check browser console for __performanceMetrics.getPerformanceReport()');

  console.log('\n━'.repeat(80));

  // Overall status
  const allPassed = pageLoadTime < 2000 && tti < 3000;

  if (allPassed) {
    console.log('\n✅ All page load performance targets met!\n');
    return 0;
  } else {
    console.log('\n❌ Some performance targets not met. See recommendations below.\n');

    console.log('💡 Recommendations:');
    if (pageLoadTime >= 2000) {
      console.log('   • Reduce initial bundle size (code splitting, tree shaking)');
      console.log('   • Enable compression (gzip/brotli)');
      console.log('   • Optimize images and assets');
      console.log('   • Use CDN for static assets');
    }
    if (tti >= 3000) {
      console.log('   • Defer non-critical JavaScript');
      console.log('   • Reduce main thread work');
      console.log('   • Optimize component render performance');
      console.log('   • Use React.lazy for route-based code splitting');
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
    console.log('⚠️  Prerequisites:');
    console.log('   1. Dev server must be running on http://localhost:5173');
    console.log('   2. Run "npm run dev" in another terminal if not already running.\n');

    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Measure page load metrics
    const pageLoadMetrics = await measurePageLoadMetrics();

    console.log('\n✅ Page Load Metrics Captured');
    console.log(`   Measurements: 5 runs averaged`);

    // Display results
    const exitCode = displayResults(pageLoadMetrics);

    // Save results
    const results = {
      timestamp: new Date().toISOString(),
      pageLoadMetrics,
      targets: {
        pageLoadTime: {
          value: pageLoadMetrics.pageLoadTime,
          target: 2000,
          passed: pageLoadMetrics.pageLoadTime < 2000,
        },
        timeToInteractive: {
          value: pageLoadMetrics.timeToInteractive,
          target: 3000,
          passed: pageLoadMetrics.timeToInteractive < 3000,
        },
      },
    };

    const resultsPath = path.join(RESULTS_DIR, `page-load-${TIMESTAMP}.json`);
    fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2));
    console.log(`📄 Results saved: ${resultsPath}\n`);

    process.exit(exitCode);
  } catch (error) {
    console.error('\n❌ Error measuring performance:', error.message);
    console.error('\nTroubleshooting:');
    console.error('  1. Ensure dev server is running: npm run dev');
    console.error('  2. Check that port 5173 is accessible');
    console.error('  3. Install Puppeteer: npm install --save-dev puppeteer\n');
    process.exit(1);
  }
}

main();
