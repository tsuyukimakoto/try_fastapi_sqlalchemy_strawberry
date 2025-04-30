import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import Link from 'next/link';
import { AuthProvider } from '@/context/AuthContext'; // Import AuthProvider
import HeaderNav from '@/components/HeaderNav'; // Import a new component for header logic

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'FastAPI + Next.js App', // Update title
  description: 'Frontend for FastAPI backend with Passkey auth', // Update description
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja"> {/* Change language to Japanese */}
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-50 text-gray-900 min-h-screen flex flex-col`} // Updated styles
      >
        {/* Wrap everything in AuthProvider */}
        <AuthProvider>
          <HeaderNav /> {/* Use HeaderNav component */}
          <main className="container mx-auto p-4 mt-4 flex-grow"> {/* Ensure main content grows */}
            {children}
          </main>
          <footer className="text-center mt-8 py-4 text-gray-500 text-sm">
            © {new Date().getFullYear()} MyApp
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
