// components/ChatMessage.tsx
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Message } from "@/lib/types";
import ToolCall from "./ui/ToolCall";
import { User, Bot } from "lucide-react";

export default function ChatMessage({ message }: Readonly<{ message: Message }>) {
    const isUser = message.role === "user";

    return (
        <div className={`flex gap-4 mb-8 ${isUser ? "justify-end" : "justify-start"}`}>
            {!isUser && (
                <Avatar className="w-9 h-9 bg-emerald-600">
                    <AvatarFallback>
                        <Bot className="w-5 h-5 text-white" />
                    </AvatarFallback>
                </Avatar>
            )}

            <div className={`max-w-3xl ${isUser ? "items-end" : "items-start"}`}>
                <div
                    className={`rounded-2xl px-5 py-3 ${
                        isUser
                            ? "bg-emerald-600 text-white"
                            : "bg-zinc-800 text-zinc-100"
                    }`}
                >
                    <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                </div>

                {message.toolCalls && message.toolCalls.length > 0 && (
                    <div className="mt-3 space-y-2">
                        {message.toolCalls.map((tool, index) => (
                            <ToolCall key={index} tool={tool} />
                        ))}
                    </div>
                )}
            </div>

            {isUser && (
                <Avatar className="w-9 h-9 bg-zinc-700">
                    <AvatarFallback>
                        <User className="w-5 h-5" />
                    </AvatarFallback>
                </Avatar>
            )}
        </div>
    );
}
