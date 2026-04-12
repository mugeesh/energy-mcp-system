// app/api/clear/route.ts
import { NextResponse } from "next/server";

export async function POST() {
    try {
        // Call your FastAPI backend (port 8000)
        const backendResponse = await fetch("http://localhost:8000/clear_history", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            }
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
            content: data.content || "not clear",
            toolCalls: data.toolCalls || [],
        });

    } catch (error: unknown) {
        console.error("Proxy error in /clear-history:", error);
        return NextResponse.json(
            {
                error: "Failed to connect to the AI agent",
                details: "Make sure the Python FastAPI server is running on http://localhost:8000",
            },
            { status: 500 }
        );
    }
}
