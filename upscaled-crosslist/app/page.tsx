export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8 text-center">
          Upscaled Cross-List Platform
        </h1>
        <p className="text-center text-xl mb-4">
          Multi-marketplace inventory management with AI-powered optimization
        </p>
        <div className="mt-8 grid text-center lg:grid-cols-3 gap-4">
          <div className="rounded-lg border border-gray-300 p-6">
            <h2 className="text-2xl font-semibold mb-2">10+ Marketplaces</h2>
            <p>List once, sell everywhere</p>
          </div>
          <div className="rounded-lg border border-gray-300 p-6">
            <h2 className="text-2xl font-semibold mb-2">AI-Powered</h2>
            <p>Claude + OpenAI optimization</p>
          </div>
          <div className="rounded-lg border border-gray-300 p-6">
            <h2 className="text-2xl font-semibold mb-2">Auto-Delist</h2>
            <p>Prevent double-selling</p>
          </div>
        </div>
        <div className="mt-8 text-center">
          <a
            href="/dashboard"
            className="rounded-lg bg-blue-600 px-8 py-4 text-white text-lg font-semibold hover:bg-blue-700 transition-colors inline-block"
          >
            Go to Dashboard
          </a>
        </div>
      </div>
    </main>
  );
}
