"use client";
import React from 'react';
import { Zap, RefreshCw, Trash2, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ToolInfo } from "@/lib/types";

interface SidebarProps {
    tools: ToolInfo[];
    isLoadingTools: boolean;
    onLoadTools: () => void;
    onClearChat: () => void;
    onLogout: () => void;
}

export default function Sidebar({
                                    tools,
                                    isLoadingTools,
                                    onLoadTools,
                                    onClearChat,
                                    onLogout
                                }: Readonly<SidebarProps>) {
    return (
        <div className="w-72 border-r border-slate-200 bg-white p-6 flex flex-col">
            {/* Logo Section */}
            <div className="flex items-center gap-3 mb-10">
                <div className="w-11 h-11 bg-emerald-600 rounded-2xl flex items-center justify-center">
                    <Zap className="w-6 h-6 text-white" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">EnergyInsight</h1>
                    <p className="text-emerald-600 text-sm">MCP + Ollama Agent</p>
                </div>
            </div>

            {/* Tools Section */}
            <div className="flex items-center justify-between mb-4">
                <div className="text-xs uppercase tracking-widest text-slate-500 font-medium">
                    AVAILABLE TOOLS
                </div>
                <Button variant="ghost" size="sm" onClick={onLoadTools} disabled={isLoadingTools}>
                    <RefreshCw className={`w-4 h-4 ${isLoadingTools ? "animate-spin" : ""}`} />
                </Button>
            </div>

            <div className="space-y-2 flex-1 overflow-y-auto pr-2">
                {tools.length > 0 ? (
                    tools.map((tool, index) => (
                        <div key={index} className="px-4 py-3 rounded-xl text-sm border">
                            <div className="font-mono text-emerald-600 font-medium">{tool.name}</div>
                            {tool.description && (
                                <div className="text-slate-600 text-xs mt-1 line-clamp-2">
                                    {tool.description}
                                </div>
                            )}
                        </div>
                    ))
                ) : (
                    <div className="text-slate-400 text-sm py-8 text-center">
                        {isLoadingTools ? "Loading tools..." : "No tools available"}
                    </div>
                )}
            </div>

            {/* Action Buttons */}
            <Button variant="destructive" className="mt-8 flex items-center gap-2" onClick={onClearChat}>
                <Trash2 className="w-4 h-4" />
                Clear Conversation
            </Button>

            <Button variant="outline" className="mt-3 flex items-center gap-2" onClick={onLogout}>
                <LogOut className="w-4 h-4" />
                Logout
            </Button>
        </div>
    );
}
