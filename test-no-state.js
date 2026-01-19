#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const process = require('process');

// 直接测试 Claude Code CLI
console.log('=== DIRECT TEST ===');

const command = 'node';
const args = [
  '/opt/homebrew/bin/claude',
  '--output-format', 'stream-json',
  '--print', '你好，我是直接测试！告诉我你的名字和功能。',
  '--verbose'
];

console.log('Executing:', command, args.join(' '));

const childProcess = spawn(command, args, {
  cwd: '/Users/apple/Documents/Miko-main',
  env: {
    ...process.env,
    FORCE_COLOR: '0'
  },
  stdio: ['pipe', 'pipe', 'pipe']
});

let buffer = '';

process.stdout.on('data', (data) => {
  buffer += data.toString();
  const lines = buffer.split('\n');
  buffer = lines.pop() || '';

  for (const line of lines) {
    if (line.trim()) {
      console.log(`stdout line: ${line}`);
      try {
        const parsed = JSON.parse(line);
        console.log('Parsed:', parsed);
      } catch (e) {
        console.log('Not JSON:', line);
      }
    }
  }
});

process.stderr.on('data', (data) => {
  console.error(`stderr: ${data.toString().trim()}`);
});

process.on('close', (code) => {
  console.log(`Process exited with code ${code}`);

  if (buffer.trim()) {
    console.log(`Remaining buffer: ${buffer}`);
  }
});

process.on('error', (err) => {
  console.error('Spawn error:', err);
});