import Image from "next/image";

export default function Home() {
  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h1 className="text-2xl font-bold mb-4">ようこそ！</h1>
      <p>FastAPI + Next.js + Passkey 認証デモアプリケーションへようこそ。</p>
      <p className="mt-2">ヘッダーのリンクから各機能へアクセスしてください。</p>
    </div>
  );
}
