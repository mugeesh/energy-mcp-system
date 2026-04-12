// app/api/tools/route.ts
import { NextResponse } from "next/server";

export async function GET() {
    try {
        const backendUrl = process.env.MCP_BACKEND_SERVER_URL || 'http://localhost:8000';
        const backendResponse = await fetch(`${backendUrl}/tools`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
            },
        });
        if (!backendResponse.ok) {
            console.error(`Backend responded with status: ${backendResponse.status}`);
            return NextResponse.json(
                { error: `Backend error: ${backendResponse.status}` },
                { status: backendResponse.status }
            );
        }

        const toolsData = await backendResponse.json();
        console.log("[Tools API] Successfully fetched tools:", toolsData);

        return NextResponse.json(toolsData, { status: 200 });

    } catch (error) {
        console.error("[Tools API] Error fetching tools:", error);
        return NextResponse.json(
            { error: "Failed to fetch tools from backend" },
            { status: 500 }
        );
    }
}

