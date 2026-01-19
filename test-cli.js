#!/usr/bin/env node

const { spawn } = require('child_process');

console.log('Testing Claude CLI...');

const process = spawn('claude', [
  '--output-format', 'stream-json',
  '--print', 'Say hello in one word'
], {
  cwd: '/Users/apple/Documents/Miko-main',
  stdio: ['pipe', 'pipe', 'pipe']
});

let stdoutData = '';
let stderrData = '';

process.stdout.on('data', (data) => {
  const text = data.toString();
  stdoutData += text;
  console.log('[STDOUT]:', text);
});

process.stderr.on('data', (data) => {
  const text = data.toString();
  stderrData += text;
  console.log('[STDERR]:', text);
});

process.on('close', (code) => {
  console.log(`\n=== Process exited with code ${code} ===`);
  console.log('Total stdout:', stdoutData.length, 'bytes');
  console.log('Total stderr:', stderrData.length, 'bytes');
});

process.on('error', (err) => {
  console.error('Process error:', err);
});

// Kill after 10 seconds
setTimeout(() => {
  console.log('\n=== Timeout - killing process ===');
  process.kill();
  process.exit(1);
}, 10000);
