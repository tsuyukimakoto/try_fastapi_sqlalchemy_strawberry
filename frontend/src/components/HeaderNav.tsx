'use client';

import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';

export default function HeaderNav() {
  const { isLoggedIn, logout, isLoading } = useAuth();

  return (
    <header className="bg-white shadow-md sticky top-0 z-50"> {/* Make header sticky */}
      <nav className="container mx-auto px-4 py-3 flex justify-between items-center">
        <Link href="/" className="text-xl font-bold text-blue-600">
          MyApp
        </Link>
        <div className="space-x-4 flex items-center"> {/* Use flex to align items */}
          <Link href="/" className="text-gray-600 hover:text-blue-600">ホーム</Link>
          {/* アイテム一覧はログイン時のみ表示 */}
          {isLoggedIn && (
            <Link href="/items" className="text-gray-600 hover:text-blue-600">アイテム一覧</Link>
          )}

          {/* ローディング中は何も表示しないか、スピナーを表示 */}
          {isLoading ? (
            <span className="text-gray-500">Loading...</span>
          ) : isLoggedIn ? (
            // ログイン中の表示
            <button
              onClick={logout}
              className="bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-3 rounded text-sm"
            >
              ログアウト
            </button>
          ) : (
            // 未ログイン時の表示
            <>
              <Link href="/login" className="text-gray-600 hover:text-blue-600">ログイン</Link>
              <Link href="/register" className="text-gray-600 hover:text-blue-600">新規登録</Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
