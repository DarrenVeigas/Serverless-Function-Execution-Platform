const fs = require('fs');
const path = require('path');

async function main() {
    try {
        // Get event data from stdin
        let inputData = '';
        
        process.stdin.on('data', (chunk) => {
            inputData += chunk;
        });
        
        process.stdin.on('end', async () => {
            try {
                // Parse the event data
                const eventData = JSON.parse(inputData.trim());
                
                // Create a simple context object
                const context = {
                    functionName: process.env.FUNCTION_NAME || 'unknown',
                    requestId: process.env.REQUEST_ID || 'unknown',
                    startTime: Date.now()
                };
                
                // Handle sleep parameter for long timeout tests
                if (eventData.sleep && typeof eventData.sleep === 'number') {
                    await new Promise(resolve => setTimeout(resolve, eventData.sleep * 1000));
                }
                
                // Load and execute the function
                try {
                    const functionModule = require('/function/function.js');
                    const result = await functionModule.handler(eventData, context);
                    
                    // Output the result as JSON
                    process.stdout.write(JSON.stringify(result));
                } catch (err) {
                    console.error(`Error executing function: ${err.message}\n${err.stack}`);
                    process.exit(1);
                }
            } catch (err) {
                console.error(`Error parsing input data: ${err.message}\n${err.stack}`);
                process.exit(1);
            }
        });
    } catch (err) {
        console.error(`Unhandled error in entrypoint: ${err.message}\n${err.stack}`);
        process.exit(1);
    }
}

main();