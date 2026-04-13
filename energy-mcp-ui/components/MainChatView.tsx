"use client";
import React from 'react';
import Sidebar from '../app/Sidebar';
import ChatHeader from '../app/ChatHeader';
import ChatArea from '../app/ChatArea';
import ChatInput from '../app/ChatInput';
import { Message, ToolInfo } from "@/lib/types";

interface MainChatViewProps {
    messages: Message[];
    tools: ToolInfo[];
    isLoadingTools: boolean;
    input: string;
    isLoading: boolean;
    onInputChange: (value: string) => void;
    onSendMessage: () => void;
    onLoadTools: () => void;
    onClearChat: () => void;
    onLogout: () => void;
}

export default function MainChatView({
                                         messages,
                                         tools,
                                         isLoadingTools,
                                         input,
                                         isLoading,
                                         onInputChange,
                                         onSendMessage,
                                         onLoadTools,
                                         onClearChat,
                                         onLogout,
                                     }: Readonly<MainChatViewProps>) {
    return (
        <div className="flex h-screen bg-[#f8fafc]">
            <Sidebar
                tools={tools}
                isLoadingTools={isLoadingTools}
                onLoadTools={onLoadTools}
                onClearChat={onClearChat}
                onLogout={onLogout}
            />

            <div className="flex-1 flex flex-col bg-white">
                <ChatHeader backendUrl={process.env.NEXT_PUBLIC_MCP_BACKEND_SERVER_URL} />
                <ChatArea messages={messages} isLoading={isLoading} />
                <ChatInput
                    value={input}
                    onChange={onInputChange}
                    onSend={onSendMessage}
                    isLoading={isLoading}
                />
            </div>
        </div>
    );
}
