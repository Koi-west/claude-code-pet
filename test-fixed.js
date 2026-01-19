const { ClaudeAgentService } = require('./dist/core/agent/ClaudeAgentService');

console.log('=== Testing Fixed ClaudeAgentService ===\n');

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
    for await (const event of service.sendMessage('Say hello in one word')) {
      receivedData = true;
      console.log('Event:', JSON.stringify(event, null, 2));
    }
    
    if (receivedData) {
      console.log('\n✅ Successfully received response!');
    } else {
      console.log('\n❌ No data received');
    }
  } catch (error) {
    console.error('\n❌ Error:', error.message);
  }
})();
