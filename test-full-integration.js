#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// 测试应用中的实际执行
console.log('=== Testing Claude Code integration ===');
console.log('Claude CLI path:', '/opt/homebrew/bin/claude');

// 测试 1: 直接运行 Claude CLI 命令
console.log('\n=== Test 1: Direct Claude CLI ===');
const test1 = spawn('node', [
  '/opt/homebrew/bin/claude',
  '--output-format', 'stream-json',
  '--print', '你好，我是来自测试脚本的消息！',
  '--verbose'
]);

test1.stdout.on('data', (data) => {
  console.log('stdout:', data.toString().trim());
  try {
    const lines = data.toString().split('\n');
    lines.forEach(line => {
      if (line.trim()) {
        const parsed = JSON.parse(line);
        console.log('Parsed:', JSON.stringify(parsed, null, 2));
      }
    });
  } catch (e) {
    console.log('Error parsing:', e);
  }
});

test1.stderr.on('data', (data) => {
  console.error('stderr:', data.toString().trim());
});

test1.on('close', (code) => {
  console.log('=== Test 1 completed ===');
  console.log('Exit code:', code);

  // 测试 2: 使用相同参数但直接执行
  console.log('\n=== Test 2: Direct execution ===');
  const test2 = spawn('node', [
    '/opt/homebrew/bin/claude',
    '--output-format', 'stream-json',
    '--print', '告诉我一些有趣的事实！',
    '--verbose'
  ]);

  test2.stdout.on('data', (data) => {
    console.log('stdout:', data.toString().trim());
  });

  test2.stderr.on('data', (data) => {
    console.error('stderr:', data.toString().trim());
  });

  test2.on('close', (code) => {
    console.log('=== Test 2 completed ===');
    console.log('Exit code:', code);

    // 测试 3: 使用 --version 参数
    console.log('\n=== Test 3: Version check ===');
    const test3 = spawn('node', ['/opt/homebrew/bin/claude', '--version']);
    test3.stdout.pipe(process.stdout);
    test3.stderr.pipe(process.stderr);
    test3.on('close', (code) => {
      console.log('=== Test 3 completed ===');
      console.log('Exit code:', code);
    });
  });
});