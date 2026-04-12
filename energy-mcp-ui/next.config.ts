import path from 'path';

module.exports = {
    env: {
        MCP_BACKEND_SERVER_URL: process.env.MCP_BACKEND_SERVER_URL,
    },
    // Load env from parent directory
    experimental: {
        serverComponentsExternalPackages: [],
    },
}

// Load custom env file
// eslint-disable-next-line @typescript-eslint/no-require-imports
require('dotenv').config({ path: path.join(__dirname, '../.env') });
