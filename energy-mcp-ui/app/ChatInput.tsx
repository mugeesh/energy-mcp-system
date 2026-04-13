"use client";
import React from 'react';
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ChatInputProps {
    value: string;
    onChange: (value: string) => void;
    onSend: () => void;
    isLoading: boolean;
}

export default function ChatInput({ value, onChange, onSend, isLoading }: Readonly<ChatInputProps>) {
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSend();
        }
    };

    return (
        <div className="p-6 border-t border-slate-200 bg-white">
            <div className="flex gap-3 max-w-4xl mx-auto">
                <input
                    type="text"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask about energy consumption, sites, or data..."
                    className="flex-1 bg-white border border-slate-300 rounded-2xl px-6 py-4 focus:outline-none focus:border-emerald-600 text-base"
                    disabled={isLoading}
                />
                <Button
                    onClick={onSend}
                    disabled={isLoading || !value.trim()}
                    size="lg"
                    className="px-8 bg-emerald-600 hover:bg-emerald-700"
                >
                    {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                </Button>
            </div>
        </div>
    );
}
