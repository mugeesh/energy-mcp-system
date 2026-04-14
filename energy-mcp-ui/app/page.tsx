"use client";
import React, { useState, useEffect } from 'react';
import { Message, ToolInfo } from "@/lib/types";
import { getToken, setToken, removeToken, isAuthenticated } from "@/lib/auth";
import LoginForm from "@/components/login";
import MainChatView from "@/components/MainChatView";

export default function EnergyMCPChat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [tools, setTools] = useState<ToolInfo[]>([]);
    const [isLoadingTools, setIsLoadingTools] = useState(false);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [loginError, setLoginError] = useState("");

    // Check authentication on mount
    useEffect(() => {
        if (isAuthenticated()) {
            setIsLoggedIn(true);
            loadTools();
        }
    }, []);

    const handleLogin = async (email: string, password: string) => {
        setLoginError("");

        try {
            const res = await fetch("https://iam.staging.energybox.com/api/v1/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            if (!res.ok) {
                throw new Error("Invalid email or password");
            }
            const data = await res.json();
            setToken(data.accessToken);
            setIsLoggedIn(true);
            await loadTools();
        } catch (err: unknown) {
            if (err instanceof Error) {
                setLoginError(err.message);
            } else {
                setLoginError("An unexpected error occurred");
            }
            throw err;
        }
    };

    const handleLogout = () => {
        removeToken();
        setIsLoggedIn(false);
        setMessages([]);
        setTools([]);
    };

    const loadTools = async () => {
        setIsLoadingTools(true);
        try {
            const res = await fetch('/api/tools');
            if (!res.ok) {
                throw new Error("Failed to load tools");
            }
            const data = await res.json();
            setTools(data.tools || []);
        } catch (err) {
            console.error("Failed to load tools:", err);
            // Fallback tools
            const fallbackTools: ToolInfo[] = [
                { index: 1, name: "list_all_sites", description: "List all energy sites" },
                { index: 2, name: "search_sites", description: "Search sites by name" },
                { index: 3, name: "get_energy_consumption", description: "Get energy consumption data" },
                { index: 4, name: "get_site_details", description: "Get detailed site information" },
            ];
            setTools(fallbackTools);
        } finally {
            setIsLoadingTools(false);
        }
    };

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
                    ...(token && { Authorization: `Bearer ${token}` }),
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

    const clearChat = async () => {
        setMessages([]);
        try {
            await fetch("/api/clearHistory", {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            });
        } catch (err) {
            console.error("Failed to clear history:", err);
        }
    };

    // Load tools on component mount (only once)
    useEffect(() => {
        if (isLoggedIn) {
            loadTools();
        }
    }, [isLoggedIn]);

    if (!isLoggedIn) {
        return <LoginForm onLogin={handleLogin} error={loginError} />;
    }

    return (
        <MainChatView
            messages={messages}
            tools={tools}
            isLoadingTools={isLoadingTools}
            input={input}
            isLoading={isLoading}
            onInputChange={setInput}
            onSendMessage={sendMessage}
            onLoadTools={loadTools}
            onClearChat={clearChat}
            onLogout={handleLogout}
        />
    );
}
