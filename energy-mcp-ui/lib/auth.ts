// lib/auth.ts
export const getToken = (): string | null => {
    return localStorage.getItem("jwt_token");
};

export const setToken = (token: string) => {
    localStorage.setItem("jwt_token", token);
};

export const removeToken = () => {
    localStorage.removeItem("jwt_token");
};

export const isAuthenticated = (): boolean => {
    return !!getToken();
};
