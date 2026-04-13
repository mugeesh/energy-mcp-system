"use client";
import React, {useState} from 'react';
import {Zap} from "lucide-react";
import {Button} from "@/components/ui/button";

interface LoginFormProps {
    onLogin: (email: string, password: string) => Promise<void>;
    error?: string;
}

export default function LoginForm({onLogin, error}: Readonly<LoginFormProps>) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setIsLoading(true);
        try {
            await onLogin(email, password);
        } finally {
            setIsLoading(false);
        }
    };

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

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:outline-none focus:border-emerald-600"
                            placeholder="mugeesh@gmail.com"
                            required
                            disabled={isLoading}
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
                            disabled={isLoading}
                        />
                    </div>

                    {error && <p className="text-red-600 text-sm text-center">{error}</p>}

                    <Button
                        type="submit"
                        className="w-full py-6 text-lg bg-emerald-600 hover:bg-emerald-700"
                        disabled={isLoading}
                    >
                        {isLoading ? "Signing in..." : "Sign In"}
                    </Button>
                </form>

                <p className="text-center text-xs text-slate-500 mt-8">
                    Demo: email = <strong>admin@energybox.com</strong>, password = <strong>password123</strong>
                </p>
            </div>
        </div>
    );
}
