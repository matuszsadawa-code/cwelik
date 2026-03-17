#!/usr/bin/env node

/**
 * Bundle Size Measurement Script
 * 
 * Analyzes the production build to ensure bundle size targets are met:
 * - Initial bundle: <500KB
 * - Total bundle: <2MB
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const distPath = path.join(__dirname, '../dist');

function getDirectorySize(dirPath) {
  let totalSize = 0;
  const files = fs.readdirSync(dirPath);

  for (const file of files) {
    const filePath = path.join(dirPath, file);
    const stats = fs.statSync(filePath);

    if (stats.isDirectory()) {
      totalSize += getDirectorySize(filePath);
    } else {
      totalSize += stats.size;
    }
  }

  return totalSize;
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function analyzeBundle() {
  if (!fs.existsSync(distPath)) {
    console.error('❌ Build directory not found. Run "npm run build" first.');
    process.exit(1);
  }

  const assetsPath = path.join(distPath, 'assets');
  
  if (!fs.existsSync(assetsPath)) {
    console.error('❌ Assets directory not found in build.');
    process.exit(1);
  }

  const files = fs.readdirSync(assetsPath);
  const jsFiles = files.filter(f => f.endsWith('.js'));
  const cssFiles = files.filter(f => f.endsWith('.css'));

  let totalJsSize = 0;
  let totalCssSize = 0;
  let initialJsSize = 0;

  const fileDetails = [];

  // Analyze JS files
  for (const file of jsFiles) {
    const filePath = path.join(assetsPath, file);
    const size = fs.statSync(filePath).size;
    totalJsSize += size;

    // Assume index-*.js is the initial bundle
    if (file.startsWith('index-')) {
      initialJsSize += size;
    }

    fileDetails.push({
      name: file,
      size: size,
      type: 'JS',
      isInitial: file.startsWith('index-')
    });
  }

  // Analyze CSS files
  for (const file of cssFiles) {
    const filePath = path.join(assetsPath, file);
    const size = fs.statSync(filePath).size;
    totalCssSize += size;

    if (file.startsWith('index-')) {
      initialJsSize += size; // CSS is also part of initial load
    }

    fileDetails.push({
      name: file,
      size: size,
      type: 'CSS',
      isInitial: file.startsWith('index-')
    });
  }

  const totalSize = totalJsSize + totalCssSize;

  // Sort by size descending
  fileDetails.sort((a, b) => b.size - a.size);

  console.log('\n📦 Bundle Size Analysis\n');
  console.log('━'.repeat(80));
  
  console.log('\n📊 Summary:');
  console.log(`  Initial Bundle: ${formatBytes(initialJsSize)}`);
  console.log(`  Total JS:       ${formatBytes(totalJsSize)}`);
  console.log(`  Total CSS:      ${formatBytes(totalCssSize)}`);
  console.log(`  Total Bundle:   ${formatBytes(totalSize)}`);

  console.log('\n🎯 Targets:');
  const initialTarget = 500 * 1024; // 500KB
  const totalTarget = 2 * 1024 * 1024; // 2MB

  const initialStatus = initialJsSize <= initialTarget ? '✅' : '❌';
  const totalStatus = totalSize <= totalTarget ? '✅' : '❌';

  console.log(`  ${initialStatus} Initial: ${formatBytes(initialJsSize)} / ${formatBytes(initialTarget)} (${((initialJsSize / initialTarget) * 100).toFixed(1)}%)`);
  console.log(`  ${totalStatus} Total:   ${formatBytes(totalSize)} / ${formatBytes(totalTarget)} (${((totalSize / totalTarget) * 100).toFixed(1)}%)`);

  console.log('\n📁 File Breakdown:');
  console.log('━'.repeat(80));
  
  for (const file of fileDetails) {
    const marker = file.isInitial ? '🔴' : '🔵';
    const percentage = ((file.size / totalSize) * 100).toFixed(1);
    console.log(`  ${marker} ${file.name.padEnd(50)} ${formatBytes(file.size).padStart(10)} (${percentage}%)`);
  }

  console.log('\n━'.repeat(80));
  console.log('🔴 Initial load  🔵 Lazy loaded\n');

  // Exit with error if targets not met
  if (initialJsSize > initialTarget || totalSize > totalTarget) {
    console.error('❌ Bundle size targets not met!\n');
    process.exit(1);
  } else {
    console.log('✅ All bundle size targets met!\n');
    process.exit(0);
  }
}

analyzeBundle();
