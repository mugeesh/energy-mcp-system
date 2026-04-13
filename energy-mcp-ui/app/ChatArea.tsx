"use client";
import React, { useRef, useEffect } from 'react';
import { Zap, Loader2 } from "lucide-react";
import ChatMessage from "@/components/ChatMessage";
import { Message } from "@/lib/types";

interface ChatAreaProps {
    messages: Message[];
    isLoading: boolean;
}

export default function ChatArea({ messages, isLoading }: Readonly<ChatAreaProps>) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTo({
                top: scrollRef.current.scrollHeight,
                behavior: "smooth",
            });
        }
    }, [messages]);

    return (
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-8 space-y-8 chat-scroll bg-[#f8fafc]">
            {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center">
                    <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mb-6">
                        <Zap className="w-12 h-12 text-emerald-600" />
                    </div>
                    <h3 className="text-3xl font-semibold text-slate-900 mb-3">Welcome to EnergyInsight</h3>
                    <p className="text-slate-600 max-w-md">
                        Ask me anything about energy sites and consumption data or User information
                    </p>
                </div>
            ) : (
                messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
            )}

            {isLoading && (
                <div className="flex items-center gap-3 text-slate-500">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Agent is thinking...
                </div>
            )}
        </div>
    );
}
