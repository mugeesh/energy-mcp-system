// components/ToolCall.tsx
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { CheckCircle, XCircle, Clock } from "lucide-react";
import { ToolCall as ToolCallType } from "@/lib/types";

export default function ToolCall({ tool }: { tool: ToolCallType }) {
    const getStatusIcon = () => {
        if (tool.status === "success") return <CheckCircle className="w-4 h-4 text-emerald-500" />;
        if (tool.status === "error") return <XCircle className="w-4 h-4 text-red-500" />;
        return <Clock className="w-4 h-4 text-yellow-500" />;
    };

    return (
        <Card className="bg-zinc-900 border-zinc-700 p-4 text-sm">
            <div className="flex items-center gap-3 mb-2">
                {getStatusIcon()}
                <Badge variant="outline" className="font-mono text-xs">
                    {tool.name}
                </Badge>
            </div>

            <div className="text-zinc-400 text-xs mb-2">Arguments:</div>
            <pre className="bg-zinc-950 p-3 rounded text-xs overflow-auto">
        {JSON.stringify(tool.arguments, null, 2)}
      </pre>

            {tool.result && (
                <>
                    <div className="text-zinc-400 text-xs mt-3 mb-1">Result:</div>
                    <pre className="bg-zinc-950 p-3 rounded text-xs overflow-auto">
            {JSON.stringify(tool.result, null, 2)}
          </pre>
                </>
            )}
        </Card>
    );
}
