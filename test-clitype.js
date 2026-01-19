#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

const cliPath = '/opt/homebrew/bin/claude';

console.log('=== Testing cliPathRequiresNode ===');
console.log(`Path: ${cliPath}`);
console.log(`Exists: ${fs.existsSync(cliPath)}`);

if (fs.existsSync(cliPath)) {
  const stat = fs.statSync(cliPath);
  console.log(`Is file: ${stat.isFile()}`);
  console.log(`Mode: 0o${stat.mode.toString(8)}`);

  // 测试 shebang
  const buffer = Buffer.alloc(200);
  const fd = fs.openSync(cliPath, 'r');
  const bytesRead = fs.readSync(fd, buffer, 0, buffer.length, 0);
  fs.closeSync(fd);

  const header = buffer.slice(0, bytesRead).toString('utf8');
  console.log(`Header:`, JSON.stringify(header));
  console.log(`Has shebang: ${header.startsWith('#!')}`);
  console.log(`Contains node: ${header.toLowerCase().includes('node')}`);

  // 测试是否是 JavaScript 文件
  const jsExtensions = ['.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx'];
  const ext = path.extname(cliPath);
  console.log(`Extension: ${ext}`);
  console.log(`Is JS file: ${jsExtensions.includes(ext.toLowerCase())}`);

  // 尝试运行一下
  console.log('\n=== Testing executable ===');
  const { spawnSync } = require('child_process');
  const result = spawnSync(cliPath, ['--version']);
  console.log(`Exit code: ${result.status}`);
  console.log(`Stdout: ${result.stdout.toString().trim()}`);
  if (result.stderr) {
    console.log(`Stderr: ${result.stderr.toString().trim()}`);
  }
}