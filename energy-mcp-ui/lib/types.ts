// lib/types.ts
export type Message = {
    id: string;
    role: "user" | "assistant" | "tool";
    content: string;
    toolCalls?: ToolCall[];
    timestamp?: Date;
};

export type ToolCall = {
    id: string;
    name: string;
    arguments: never;
    status: "pending" | "success" | "error";
    result?: never;
};

export type ChatResponse = {
    content: string;
    toolCalls?: ToolCall[];
};

export type ToolInfo = {
    name: string;
    description: string;
};
