// app/api/chat/route.ts
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { message, history } = body;

        if (!message || typeof message !== "string") {
            return NextResponse.json(
                { error: "Message is required and must be a string" },
                { status: 400 }
            );
        }
        console.log(`[Next.js API] Forwarding to Python backend: "${message.substring(0, 60)}..."`);
        const backendUrl = process.env.NEXT_PUBLIC_MCP_BACKEND_SERVER_URL || 'http://localhost:8000';
        const backendResponse = await fetch(`${backendUrl}/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(request.headers.get("authorization") && {
                    Authorization: request.headers.get("authorization")!
                }),
            },
            body: JSON.stringify({
                message: message.trim(),
                history: history || [],
            }),
        });

        if (!backendResponse.ok) {
            const errorText = await backendResponse.text().catch(() => "Unknown error");
            console.error("Backend error:", errorText);
            return NextResponse.json(
                { error: `Backend returned ${backendResponse.status}` },
                { status: backendResponse.status }
            );
        }

        const data = await backendResponse.json();

        return NextResponse.json({
            content: data.content || "No response from agent",
            toolCalls: data.toolCalls || [],
        });

    } catch (error: unknown) {
        console.error("Proxy error in /api/chat:", error);
        return NextResponse.json(
            {
                error: "Failed to connect to the AI agent",
                details: "Make sure the Python FastAPI server is running on http://localhost:8000",
            },
            { status: 500 }
        );
    }
}
