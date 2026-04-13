"use client";
import React from 'react';

interface ChatHeaderProps {
    backendUrl?: string;
}

export default function ChatHeader({ backendUrl }: Readonly<ChatHeaderProps>) {
    return (
        <header className="h-16 border-b border-slate-200 flex items-center px-8 bg-white">
            <h2 className="font-semibold text-xl text-slate-900">Energy Consumption AI Assistant</h2>
            {backendUrl && (
                <div className="ml-auto text-xs text-emerald-600 font-mono">
                    Backend: {backendUrl}
                </div>
            )}
        </header>
    );
}
