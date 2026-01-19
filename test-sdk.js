const { ClaudeAgentService } = require('./dist/core/agent/ClaudeAgentService');

console.log('=== Testing SDK-based ClaudeAgentService ===\n');

const service = new ClaudeAgentService({
  workingDirectory: '/Users/apple/Documents/Miko-main'
});

if (!service.isCliAvailable()) {
  console.error('❌ Claude CLI not available');
  process.exit(1);
}

console.log('✅ CLI available at:', service.getCliPath());
console.log('\n=== Sending test message ===\n');

(async () => {
  try {
    let receivedData = false;
    let textContent = '';
    
    for await (const event of service.sendMessage('Say hello in one word')) {
      receivedData = true;
      
      if (event.type === 'text') {
        textContent += event.content;
        process.stdout.write(event.content);
      } else if (event.type === 'done') {
        console.log('\n\n✅ Stream completed!');
      } else if (event.type === 'error') {
        console.error('\n❌ Error:', event.content);
      } else {
        console.log('\nEvent:', event.type);
      }
    }
    
    if (receivedData) {
      console.log('\n✅ Successfully received response!');
      console.log('Response:', textContent);
    } else {
      console.log('\n❌ No data received');
    }
  } catch (error) {
    console.error('\n❌ Error:', error.message);
    console.error(error.stack);
  }
})();
