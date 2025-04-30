'use client';

import { useState } from 'react';
import { gql } from 'graphql-request';
import { startAuthentication } from '@simplewebauthn/browser';
import { publicGraphQLClient } from '@/lib/graphql-client'; // 認証なしクライアント
import { useRouter } from 'next/navigation'; // Use useRouter for redirection

// GraphQL クエリ/ミューテーション定義
const GENERATE_AUTHENTICATION_OPTIONS_QUERY = gql`
  query GenerateAuthenticationOptions($username: String) {
    generateAuthenticationOptions(username: $username)
  }
`;

const VERIFY_AUTHENTICATION_MUTATION = gql`
  mutation VerifyAuthentication($verificationInput: AuthenticationVerificationInput!) {
    verifyAuthentication(verificationInput: $verificationInput) {
      accessToken
      tokenType
    }
  }
`;

export default function LoginPage() {
  const [username, setUsername] = useState(''); // Optional username
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter(); // Initialize router

  const handleLogin = async (event?: React.FormEvent<HTMLFormElement>) => {
    event?.preventDefault(); // Prevent form submission if called from form
    setError(null);
    setIsLoading(true);

    let authenticationOptions;
    let challengeKey;

    try {
      // 1. 認証オプションをサーバーから取得 (ユーザー名があれば指定)
      const optionsResponse = await publicGraphQLClient.request<{ generateAuthenticationOptions: { options: any, challengeKey: string } }>(
        GENERATE_AUTHENTICATION_OPTIONS_QUERY,
        { username: username || null } // Send null if username is empty
      );
      authenticationOptions = optionsResponse.generateAuthenticationOptions.options;
      challengeKey = optionsResponse.generateAuthenticationOptions.challengeKey;

      // 2. @simplewebauthn/browser で認証を開始
      const assertion = await startAuthentication(authenticationOptions);

      // 3. サーバーに検証をリクエスト
      const verificationResponse = await publicGraphQLClient.request<{ verifyAuthentication: { accessToken: string, tokenType: string } }>(
        VERIFY_AUTHENTICATION_MUTATION,
        {
          verificationInput: {
            // assertion.id は Base64URL エンコードされている
            credential_id_b64: assertion.id,
            // assertion オブジェクト全体を JSON 文字列として送信
            authentication_response_json: JSON.stringify(assertion),
            challenge_key: challengeKey,
          },
        }
      );

      // 4. 認証成功後、JWT を保存 (例: localStorage)
      if (verificationResponse.verifyAuthentication.accessToken) {
        localStorage.setItem('accessToken', verificationResponse.verifyAuthentication.accessToken);
        // ログイン成功後、アイテム一覧ページなどにリダイレクト
        router.push('/items');
      } else {
        setError('認証に失敗しました。トークンが取得できませんでした。');
      }
    } catch (err: any) {
      console.error('Authentication failed:', err);
      const errorMessage = err.response?.errors?.[0]?.message || err.message || '認証中にエラーが発生しました。';
      // Check for cancellation error
      if (err.name === 'AbortError' || errorMessage.includes('cancelled')) {
          setError('認証プロセスがキャンセルされました。');
      } else {
          setError(errorMessage);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex justify-center">
      <div className="w-full max-w-md bg-white shadow-md rounded-lg p-8">
        <h1 className="text-2xl font-bold mb-6 text-center">ログイン</h1>
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
            <strong className="font-bold">エラー:</strong>
            <span className="block sm:inline"> {error}</span>
          </div>
        )}
        {/* Discoverable Credentials を考慮し、ユーザー名入力はオプションとする */}
        {/* <form onSubmit={handleLogin}> */}
          <div className="mb-4">
            <label htmlFor="username" className="block text-gray-700 text-sm font-bold mb-2">
              ユーザー名 (オプション)
            </label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              disabled={isLoading}
              placeholder="登録済みの場合は空白でも可"
            />
             <p className="text-xs text-gray-600 mt-1">Discoverable Credential (Resident Key) を使用する場合、ここは空欄のままでログインボタンを押してください。</p>
          </div>

          <div className="flex items-center justify-center mt-6">
             {/* フォーム送信ではなく、ボタンクリックで直接 handleLogin を呼び出す */}
            <button
              // type="submit"
              onClick={() => handleLogin()}
              className={`bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline ${
                isLoading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
              disabled={isLoading}
            >
              {isLoading ? '認証中...' : 'パスキーでログイン'}
            </button>
          </div>
        {/* </form> */}
      </div>
    </div>
  );
}
