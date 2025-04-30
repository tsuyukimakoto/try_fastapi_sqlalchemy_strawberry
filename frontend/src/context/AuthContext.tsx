'use client';

import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation'; // Import usePathname

interface AuthContextType {
  token: string | null;
  isLoggedIn: boolean;
  login: (newToken: string) => void;
  logout: () => void;
  isLoading: boolean; // Add loading state
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true); // Start with loading true
  const router = useRouter();
  const pathname = usePathname(); // Get current path

  useEffect(() => {
    // コンポーネントマウント時に localStorage からトークンを読み込む
    const storedToken = localStorage.getItem('accessToken');
    if (storedToken) {
      setToken(storedToken);
      // TODO: ここでトークンの有効性をサーバーに確認する処理を追加することが望ましい
    }
    setIsLoading(false); // ローディング完了
  }, []);

  // トークンが変更されたら localStorage に保存/削除
  useEffect(() => {
    if (token) {
      localStorage.setItem('accessToken', token);
    } else {
      localStorage.removeItem('accessToken');
    }
  }, [token]);

  // ログイン状態が変化したときの副作用 (例: ログアウト後にログインページへ)
  useEffect(() => {
      if (!isLoading && !token && !['/login', '/register'].includes(pathname)) {
          // ローディングが完了していて、トークンがなく、
          // かつログイン/登録ページ以外にいる場合はログインページへリダイレクト
          // (アイテムページなど保護されたページからのログアウトを想定)
          // router.push('/login'); // 無限ループを避けるため、必要に応じて有効化
      }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isLoading, pathname, router]); // pathname を依存関係に追加


  const login = (newToken: string) => {
    setToken(newToken);
    // ログイン後にリダイレクトが必要な場合はここで行う
    // router.push('/items'); // ログインページ側でリダイレクトしているので、通常は不要
  };

  const logout = () => {
    setToken(null);
    // ログアウト後、ログインページにリダイレクト
    router.push('/login');
  };

  const isLoggedIn = !!token;

  return (
    <AuthContext.Provider value={{ token, isLoggedIn, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
