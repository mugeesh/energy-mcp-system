import type { NextConfig } from 'next';
import path from 'path';
import dotenv from 'dotenv';

// Manually load the env from the parent directory
dotenv.config({ path: path.join(process.cwd(), '../.env') });

const nextConfig: NextConfig = {
    /* FIX: 'serverComponentsExternalPackages' moved from 'experimental'
       to 'serverExternalPackages' at the top level in Next 16.
    */
    serverExternalPackages: [
        '@modelcontextprotocol/sdk' // Add other packages that need to skip bundling here
    ],

    env: {
        MCP_BACKEND_SERVER_URL: process.env.MCP_BACKEND_SERVER_URL || '',
    },

    // Ensure Turbopack handles the config correctly
    experimental: {
        // Keep this empty or remove it if you don't have other experimental flags
    },
};

export default nextConfig;
