"use client";
import React from 'react';
import {useState, useRef, useEffect} from "react";
import { Send, Loader2, Zap, Trash2, RefreshCw, LogOut } from "lucide-react";
import {Button} from "@/components/ui/button";
import ChatMessage from "@/components/ChatMessage";
import {Message, ToolInfo} from "@/lib/types";
import {getToken, setToken, removeToken, isAuthenticated} from "@/lib/auth";

export default function EnergyMCPChat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [tools, setTools] = useState<ToolInfo[]>([]);
    const [isLoadingTools, setIsLoadingTools] = useState(false);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loginError, setLoginError] = useState("");

    // Check if already logged in
    useEffect(() => {
        if (isAuthenticated()) {
            setIsLoggedIn(true);
            loadTools();
        }
    }, []);

    const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setLoginError("");

        try {
            const res = await fetch("https://iam.staging.energybox.com/api/v1/auth/login", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    email: email,
                    password: password
                })
            });

            if (!res.ok) {
                throw new Error("Invalid email or password");
            }

            const data = await res.json();
            setToken(data.access_token);
            setIsLoggedIn(true);
            await loadTools();
        } catch (err: unknown) {
            if (err instanceof Error) {
                setLoginError(err.message);
            } else {
                setLoginError("An unexpected error occurred");
            }
        }
    };

    const handleLogout = () => {
        removeToken();
        setIsLoggedIn(false);
        setMessages([]);
        setTools([]);
    };

    // Load available tools on component mount
    const loadTools = async () => {
        setIsLoadingTools(true);
        try {
            const res = await fetch('/api/tools');
            if (!res.ok) {
                console.error("Failed to load tools:", res.status);
                throw new Error("Failed to load tools");
            }
            const data = await res.json();

            setTools(data.tools || []);
            console.log("Loaded tools:", data.tools);
        } catch (err) {
            console.error("Failed to load tools:", err);
            // Fallback tools if API fails
            const fallbackTools: ToolInfo[] = [
                {index: 1, name: "list_all_sites", description: "List all energy sites"},
                {index: 2, name: "search_sites", description: "Search sites by name"},
                {index: 3, name: "get_energy_consumption", description: "Get energy consumption data"},
                {index: 4, name: "get_site_details", description: "Get detailed site information"},
            ];
            setTools(fallbackTools);
        } finally {
            setIsLoadingTools(false);
        }
    };

    // Load tools when component mounts
    useEffect(() => {
        loadTools().then(() => {
            console.log("clear history")
        });
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
            const token = getToken();
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(token && {Authorization: `Bearer ${token}`}),
                },
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
        } catch (err: unknown) {
            console.error("Failed to send message:", err);

            const errorMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: err instanceof Error && err.message.includes("connect")
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
        setMessages([])
        clearAllBackendHistory().then(() => {
            console.log("clear history")
        });

    };

    const clearAllBackendHistory = async () => {
        try {
            const res = await fetch("/api/clearHistory", {
                method: "POST",
                headers: {"Content-Type": "application/json"}
            });
            if (!res.ok) {
                const errorData = await res.json().catch(() => ({}));
                console.error("Failed to clear backend:", errorData);
            }
        } catch (err: unknown) {
            console.error("Failed to clear history:", err);
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

    // Show Login Screen if not logged in
    if (!isLoggedIn) {
        return (
            <div className="min-h-screen bg-[#f8fafc] flex items-center justify-center">
                <div className="bg-white p-10 rounded-3xl shadow-xl w-full max-w-md">
                    <div className="flex justify-center mb-8">
                        <div className="w-16 h-16 bg-emerald-600 rounded-2xl flex items-center justify-center">
                            <Zap className="w-9 h-9 text-white"/>
                        </div>
                    </div>
                    <h2 className="text-3xl font-bold text-center mb-2">Welcome Back</h2>
                    <p className="text-slate-600 text-center mb-8">Sign in to access EnergyInsight</p>

                    <form onSubmit={handleLogin} className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">email</label>
                            <input
                                type="text"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:outline-none focus:border-emerald-600"
                                placeholder="mugeesh@gmail.com"
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:outline-none focus:border-emerald-600"
                                placeholder="••••••••"
                                required
                            />
                        </div>

                        {loginError && (
                            <p className="text-red-600 text-sm text-center">{loginError}</p>
                        )}

                        <Button type="submit" className="w-full py-6 text-lg bg-emerald-600 hover:bg-emerald-700">
                            Sign In
                        </Button>
                    </form>

                    <p className="text-center text-xs text-slate-500 mt-8">
                        Demo: email = <strong>admin@energybox.com</strong>, password = <strong>password123</strong>
                    </p>
                </div>
            </div>
        );
    }

    // Main Chat UI (Logged In)
    return (
        <div className="flex h-screen bg-[#f8fafc]">
            {/* Sidebar */}
            <div className="w-72 border-r border-slate-200 bg-white p-6 flex flex-col">
                <div className="flex items-center gap-3 mb-10">
                    <div className="w-11 h-11 bg-emerald-600 rounded-2xl flex items-center justify-center">
                        <Zap className="w-6 h-6 text-white"/>
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">EnergyInsight</h1>
                        <p className="text-emerald-600 text-sm">MCP + Ollama Agent</p>
                    </div>
                </div>

                <div className="flex items-center justify-between mb-4">
                    <div className="text-xs uppercase tracking-widest text-slate-500 font-medium">
                        AVAILABLE TOOLS
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={loadTools}
                        disabled={isLoadingTools}
                    >
                        <RefreshCw className={`w-4 h-4 ${isLoadingTools ? "animate-spin" : ""}`}/>
                    </Button>
                </div>

                <div className="space-y-2 flex-1 overflow-y-auto pr-2">
                    {tools.length > 0 ? (
                        tools.map((tool, index) => (
                            <div
                                key={index}
                                className="tool-card px-4 py-3 rounded-xl text-sm border"
                            >
                                <div className="font-mono text-emerald-600 font-medium">{tool.name}</div>
                                {tool.description && (
                                    <div className="text-slate-600 text-xs mt-1 line-clamp-2">
                                        {tool.description}
                                    </div>
                                )}
                            </div>
                        ))
                    ) : (
                        <div className="text-slate-400 text-sm py-8 text-center">Loading tools...</div>
                    )}
                </div>

                {/* Clear Button - Now properly visible */}
                <Button
                    variant="destructive"
                    className="mt-8 flex items-center gap-2"
                    onClick={clearChat}
                >
                    <Trash2 className="w-4 h-4"/>
                    Clear Conversation
                </Button>
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col bg-white">
                <header className="h-16 border-b border-slate-200 flex items-center px-8">
                    <h2 className="font-semibold text-xl text-slate-900">Energy Consumption AI Assistant</h2>
                    <div className="ml-auto text-xs text-emerald-600 font-mono">
                        Backend: {process.env.NEXT_PUBLIC_MCP_BACKEND_SERVER_URL}
                    </div>
                    <div>
                    <Button
                        variant="outline"
                        className="mt-3 flex items-center gap-2"
                        onClick={handleLogout}
                    >
                        <LogOut className="w-4 h-4" />
                        Logout
                    </Button>
                    </div>
                </header>

                <div
                    ref={scrollRef}
                    className="flex-1 overflow-y-auto p-8 space-y-8 chat-scroll bg-[#f8fafc]"
                >
                    {messages.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-center">
                            <div
                                className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mb-6">
                                <Zap className="w-12 h-12 text-emerald-600"/>
                            </div>
                            <h3 className="text-3xl font-semibold text-slate-900 mb-3">Welcome to EnergyInsight</h3>
                            <p className="text-slate-600 max-w-md">
                                Ask me anything about energy sites and consumption data or User information
                            </p>
                        </div>
                    ) : (
                        messages.map((msg) => <ChatMessage key={msg.id} message={msg}/>)
                    )}

                    {isLoading && (
                        <div className="flex items-center gap-3 text-slate-500">
                            <Loader2 className="w-5 h-5 animate-spin"/>
                            Agent is thinking...
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <div className="p-6 border-t border-slate-200 bg-white">
                    <div className="flex gap-3 max-w-4xl mx-auto">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                            placeholder="Ask about energy consumption, sites, or data..."
                            className="flex-1 bg-white border border-slate-300 rounded-2xl px-6 py-4 focus:outline-none focus:border-emerald-600 text-base"
                            disabled={isLoading}
                        />
                        <Button
                            onClick={sendMessage}
                            disabled={isLoading || !input.trim()}
                            size="lg"
                            className="px-8 bg-emerald-600 hover:bg-emerald-700"
                        >
                            {isLoading ? <Loader2 className="w-5 h-5 animate-spin"/> : <Send className="w-5 h-5"/>}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
