#!/usr/bin/env node

const { spawnSync } = require('child_process');

console.log('=== TESTING CLAUDE CLI ===');
console.log('Path:', '/opt/homebrew/bin/claude');

// 测试版本
console.log('\n1. Checking version:');
const version = spawnSync('node', ['/opt/homebrew/bin/claude', '--version']);
console.log('Exit code:', version.status);
console.log('Stdout:', version.stdout.toString().trim());
console.log('Stderr:', version.stderr.toString().trim());

// 测试简单查询，超时 10 秒
console.log('\n2. Simple query (timeout 10s):');
const query = spawnSync('node', ['/opt/homebrew/bin/claude', '--output-format', 'stream-json', '--print', 'Hello, world!', '--verbose'], {
  timeout: 10000
});
console.log('Exit code:', query.status);
console.log('Stdout:', query.stdout.toString());
console.log('Stderr:', query.stderr.toString().trim());