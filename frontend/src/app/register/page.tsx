'use client'; // クライアントコンポーネントとしてマーク

import { useState } from 'react';
import { gql } from 'graphql-request';
import { startRegistration } from '@simplewebauthn/browser';
import { publicGraphQLClient } from '@/lib/graphql-client'; // 認証なしクライアントを使用

// GraphQL クエリ/ミューテーション定義
const GENERATE_REGISTRATION_OPTIONS_MUTATION = gql`
  query GenerateRegistrationOptions($username: String!, $displayName: String!) {
    generateRegistrationOptions(username: $username, displayName: $displayName)
  }
`;

const VERIFY_REGISTRATION_MUTATION = gql`
  mutation VerifyRegistration($verificationInput: RegistrationVerificationInput!) {
    verifyRegistration(verificationInput: $verificationInput)
  }
`;

export default function RegisterPage() {
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleRegister = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsLoading(true);
    setIsSuccess(false);

    let registrationOptions;
    let challengeKey;

    try {
      // 1. 登録オプションをサーバーから取得
      const optionsResponse = await publicGraphQLClient.request<{ generateRegistrationOptions: { options: any, challengeKey: string } }>(
        GENERATE_REGISTRATION_OPTIONS_MUTATION,
        { username, displayName }
      );
      registrationOptions = optionsResponse.generateRegistrationOptions.options;
      challengeKey = optionsResponse.generateRegistrationOptions.challengeKey;

      // 2. @simplewebauthn/browser で登録を開始
      const attestation = await startRegistration(registrationOptions);

      // 3. サーバーに検証をリクエスト
      const verificationResponse = await publicGraphQLClient.request<{ verifyRegistration: boolean }>(
        VERIFY_REGISTRATION_MUTATION,
        {
          verificationInput: {
            username: username,
            // attestation オブジェクト全体を JSON 文字列として送信
            registration_response_json: JSON.stringify(attestation),
            challenge_key: challengeKey,
          },
        }
      );

      if (verificationResponse.verifyRegistration) {
        setIsSuccess(true);
      } else {
        setError('登録検証に失敗しました。');
      }
    } catch (err: any) {
      console.error('Registration failed:', err);
      // エラーメッセージを適切に表示 (GraphQL エラーと WebAuthn エラーの両方を考慮)
      const errorMessage = err.response?.errors?.[0]?.message || err.message || '登録中にエラーが発生しました。';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex justify-center">
      <div className="w-full max-w-md bg-white shadow-md rounded-lg p-8">
        <h1 className="text-2xl font-bold mb-6 text-center">新規登録</h1>
        {isSuccess ? (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative" role="alert">
            <strong className="font-bold">登録成功！</strong>
            <span className="block sm:inline"> ログインページからログインしてください。</span>
          </div>
        ) : (
          <form onSubmit={handleRegister}>
            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
                <strong className="font-bold">エラー:</strong>
                <span className="block sm:inline"> {error}</span>
              </div>
            )}
            <div className="mb-4">
              <label htmlFor="username" className="block text-gray-700 text-sm font-bold mb-2">
                ユーザー名
              </label>
              <input
                type="text"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={3}
                maxLength={50}
                className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                disabled={isLoading}
              />
            </div>
            <div className="mb-6">
              <label htmlFor="displayName" className="block text-gray-700 text-sm font-bold mb-2">
                表示名
              </label>
              <input
                type="text"
                id="displayName"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                maxLength={100}
                className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                disabled={isLoading}
              />
            </div>
            <div className="flex items-center justify-center">
              <button
                type="submit"
                className={`bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline ${
                  isLoading ? 'opacity-50 cursor-not-allowed' : ''
                }`}
                disabled={isLoading}
              >
                {isLoading ? '登録中...' : 'パスキーで登録'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
