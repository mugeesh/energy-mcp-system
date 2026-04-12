"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Zap, Trash2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import ChatMessage from "@/components/ChatMessage";
import {Message, ToolInfo} from "@/lib/types";

export default function EnergyMCPChat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [tools, setTools] = useState<ToolInfo[]>([]);
    const [isLoadingTools, setIsLoadingTools] = useState(false);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);


    // Load available tools on component mount
    const loadTools = async () => {
        setIsLoadingTools(true);
        try {
            const res = await fetch('/api/tools');  // Note: no /app prefix
            if (!res.ok) throw new Error("Failed to load tools");
            const data = await res.json();

            setTools(data.tools || []);
            console.log("Loaded tools:", data.tools);
        } catch (err) {
            console.error("Failed to load tools:", err);
            // Fallback tools if API fails
            const fallbackTools: ToolInfo[] = [
                 { name: "list_all_sites", description: "List all energy sites" },
                { name: "search_sites", description: "Search sites by name" },
                { name: "get_energy_consumption", description: "Get energy consumption data" },
                { name: "get_site_details", description: "Get detailed site information" },
            ];
            setTools(fallbackTools);
        } finally {
            setIsLoadingTools(false);
        }
    };

    // Load tools when component mounts
    useEffect(() => {
        loadTools();
    }, []);

    const sendMessage = async () => {
        if (!input.trim() || isLoading) return;

        const userMsg: Message = {
            id: Date.now().toString(),
            role: "user",
            content: input.trim(),
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMsg]);
        const currentInput = input.trim();
        setInput("");
        setIsLoading(true);

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: currentInput,
                    history: messages.slice(-8),
                }),
            });

            if (!res.ok) {
                const errorData = await res.json().catch(() => ({}));
                throw new Error(errorData.error || `Server error: ${res.status}`);
            }

            const data = await res.json();

            const assistantMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: data.content || "No response received from agent.",
                toolCalls: data.toolCalls || [],
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, assistantMsg]);

        } catch (err: any) {
            console.error("Failed to send message:", err);

            const errorMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: err.message.includes("connect")
                    ? "❌ Cannot connect to AI agent. Please make sure the Python backend is running on port 8000."
                    : "Sorry, something went wrong while processing your request.",
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, errorMsg]);
        } finally {
            setIsLoading(false);
        }
    };

    const clearChat = () => {
        setMessages([]);
        clearAllBackendHistory()
    };

    const clearAllBackendHistory = async () => {
        // setInput("");
        // setIsLoading(true);

        try {
            const res = await fetch("/api/clear_history", {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            });

            if (!res.ok) {
                const errorData = await res.json().catch(() => ({}));
                throw new Error(errorData.error || `Server error: ${res.status}`);
            }

            const data = await res.json();

            const assistantMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: data.content || "No response received from agent.",
                toolCalls: data.toolCalls || [],
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, assistantMsg]);

        } catch (err: any) {
            console.error("Failed to send message:", err);

            const errorMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: err.message.includes("connect")
                    ? "❌ Cannot connect to AI agent. Please make sure the Python backend is running on port 8000."
                    : "Sorry, something went wrong while processing your request.",
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, errorMsg]);
        } finally {
            setIsLoading(false);
        }
    };

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTo({
                top: scrollRef.current.scrollHeight,
                behavior: "smooth",
            });
        }
    }, [messages]);

    return (
        <div className="flex h-screen bg-zinc-950 text-white">
            {/* Sidebar */}
            <div className="w-72 border-r border-zinc-800 p-6 flex flex-col">
                <div className="flex items-center gap-3 mb-10">
                    <div className="w-11 h-11 bg-emerald-600 rounded-2xl flex items-center justify-center">
                        <Zap className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">EnergyInsight</h1>
                        <p className="text-emerald-500 text-sm">MCP + Ollama Agent</p>
                    </div>
                </div>

                <div className="flex items-center justify-between mb-3">
                    <div className="text-xs uppercase tracking-widest text-zinc-500">
                        AVAILABLE TOOLS
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={loadTools}
                        disabled={isLoadingTools}
                        className="h-7 w-7 p-0"
                    >
                        <RefreshCw className={`w-4 h-4 ${isLoadingTools ? "animate-spin" : ""}`} />
                    </Button>
                </div>

                <div className="space-y-1 text-sm overflow-y-auto flex-1 pr-2">
                    {tools.length > 0 ? (
                        tools.map((tool, index) => (
                            <div
                                key={index}
                                className="px-3 py-2.5 bg-zinc-900 hover:bg-zinc-800 rounded-lg transition-colors"
                                title={tool.description}
                            >
                                <div className="font-mono text-emerald-400 text-xs">{tool.name}</div>
                                {tool.description && (
                                    <div className="text-zinc-500 text-xs mt-0.5 line-clamp-2">
                                        {tool.description}
                                    </div>
                                )}
                            </div>
                        ))
                    ) : (
                        <div className="text-zinc-500 text-sm py-4 text-center">
                            Loading tools...
                        </div>
                    )}
                </div>

                <Button
                    variant="destructive"
                    className="mt-6 flex items-center gap-2"
                    onClick={clearChat}
                >
                    <Trash2 className="w-4 h-4" />
                    Clear Conversation
                </Button>
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col">
                <header className="h-16 border-b border-zinc-800 flex items-center px-8 bg-zinc-950">
                    <h2 className="font-semibold text-lg">Energy Consumption AI Assistant</h2>
                    <div className="ml-auto text-xs text-emerald-500 font-mono">
                        Backend: http://localhost:8000
                    </div>
                </header>

                {/* Messages Area */}
                <div
                    ref={scrollRef}
                    className="flex-1 overflow-y-auto p-8 space-y-8 chat-scroll"
                >
                    {messages.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-center">
                            <Zap className="w-20 h-20 text-emerald-600 mb-6 opacity-80" />
                            <h3 className="text-3xl font-medium mb-3">Welcome to EnergyInsight</h3>
                            <p className="text-zinc-500 max-w-md text-lg">
                                Ask anything about your User, sites and site energy consumption
                            </p>
                            <p className="text-sm text-zinc-600 mt-8">
                                Example: &quot;Show me energy consumption of Mugeesh Site for last 10 days&quot;
                                Example: &quot;tell me who is Marcus Hunger&quot;
                            </p>
                        </div>
                    ) : (
                        messages.map((msg) => (
                            <ChatMessage key={msg.id} message={msg} />
                        ))
                    )}

                    {isLoading && (
                        <div className="flex items-center gap-3 text-zinc-500 mt-4">
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span>Agent is thinking and may call tools...</span>
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <div className="p-6 border-t border-zinc-800 bg-zinc-950">
                    <div className="flex gap-3 max-w-4xl mx-auto">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                            placeholder="Ask about energy consumption, sites, or data..."
                            className="flex-1 bg-zinc-900 border border-zinc-700 rounded-2xl px-6 py-4 focus:outline-none focus:border-emerald-600 text-base placeholder:text-zinc-500"
                            disabled={isLoading}
                        />
                        <Button
                            onClick={sendMessage}
                            disabled={isLoading || !input.trim()}
                            size="lg"
                            className="px-8 bg-emerald-600 hover:bg-emerald-700"
                        >
                            {isLoading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <Send className="w-5 h-5" />
                            )}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
