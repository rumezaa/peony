'use client';

import { useState, useRef, useEffect } from 'react';
import { Reenie_Beanie } from 'next/font/google';

interface CloneResponse {
  success: boolean;
  html?: string;
  error?: string;
  metadata?: {
    processing_time_seconds: number;
    html_length: number;
    timestamp: string;
    source_url: string;
  };
}

interface MultiPageResponse {
  success: boolean;
  pages?: { [path: string]: string };
  total_pages?: number;
  error?: string;
  metadata?: {
    processing_time_seconds: number;
    total_pages_cloned: number;
    total_html_length: number;
    timestamp: string;
    source_url: string;
    pages_list: string[];
  };
}

interface StreamData {
  status: 'starting' | 'extracting' | 'generating' | 'complete' | 'error';
  message: string;
  html?: string;
}

const reenieBeanie = Reenie_Beanie({
  weight: '400',
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-reenie-beanie',
});

export default function WebsiteCloner() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [multiPageResult, setMultiPageResult] = useState<{ [path: string]: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cloneMode, setCloneMode] = useState<'single' | 'multipage'>('single');
  const [maxPages, setMaxPages] = useState(5);
  const [streamingMode, setStreamingMode] = useState(false);
  const [streamStatus, setStreamStatus] = useState<string>('');
  const [selectedPage, setSelectedPage] = useState<string>('');
  const [metadata, setMetadata] = useState<any>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setMultiPageResult(null);
    setMetadata(null);
    setStreamStatus('');

    try {
      if (streamingMode && cloneMode === 'single') {
        await handleStreamingClone();
      } else if (cloneMode === 'multipage') {
        await handleMultiPageClone();
      } else {
        await handleSinglePageClone();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleSinglePageClone = async () => {
    const response = await fetch('http://localhost:8000/api/clone', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url }),
    });


    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: Failed to clone website`);
    }

    const data: CloneResponse = await response.json();

    if (!data.html || data.html.length < 100) {
      throw new Error('Generated HTML is incomplete or empty');
    }

    setResult(data.html);
    setMetadata(data.metadata);
  };

  const handleMultiPageClone = async () => {
    const response = await fetch('http://localhost:8000/api/clone/multipage', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        url, 
        max_pages: maxPages 
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: Failed to clone website`);
    }

    const data: MultiPageResponse = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to clone website');
    }

    if (!data.pages || Object.keys(data.pages).length === 0) {
      throw new Error('No pages were successfully cloned');
    }

    setMultiPageResult(data.pages);
    setMetadata(data.metadata);
    
    const firstPage = Object.keys(data.pages)[0];
    setSelectedPage(firstPage);
    setResult(data.pages[firstPage]);
  };

  const handleStreamingClone = async () => {
    return new Promise<void>((resolve, reject) => {
      const eventSource = new EventSource(
        `http://localhost:8000/api/clone/stream?url=${encodeURIComponent(url)}`
      );
      
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          const data: StreamData = JSON.parse(event.data);
          
          setStreamStatus(`${data.status}: ${data.message}`);

          if (data.status === 'complete' && data.html) {
            setResult(data.html);
            eventSource.close();
            resolve();
          } else if (data.status === 'error') {
            eventSource.close();
            reject(new Error(data.message));
          }
        } catch (e) {
          console.error('Error parsing stream data:', e);
        } finally {
          setLoading(false);
        }
      };

      eventSource.onerror = (error) => {
        console.error('EventSource error:', error);
        eventSource.close();
        reject(new Error('Streaming connection failed'));
      };
    });
  };

  const handlePageSelect = (pagePath: string) => {
    if (multiPageResult && multiPageResult[pagePath]) {
      setSelectedPage(pagePath);
      setResult(multiPageResult[pagePath]);
    }
  };

  const downloadHtml = () => {
    if (!result) return;
    
    const blob = new Blob([result], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cloned-website-${Date.now()}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadAllPages = () => {
    if (!multiPageResult) return;

    Object.entries(multiPageResult).forEach(([path, html]) => {
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `page-${path.replace(/[^a-zA-Z0-9]/g, '_')}-${Date.now()}.html`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  };

  return (
    <div className="max-w-[1200px] mx-auto p-8 min-h-screen font-sans text-[#333]">
      <h1 className="text-center text-black text-4xl md:text-6xl font-semibold mb-2 drop-shadow-lg font-reenie">Peony</h1>
      <span className="block text-center text-indigo-500 text-2xl mb-8 font-reenie">Your AI-powered site duplicator</span>
      <form
        className="bg-white/95 backdrop-blur-lg p-8 rounded-2xl shadow-xl border border-white/20 mb-8"
        onSubmit={handleSubmit}
      >
        <div className="mb-6">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Enter website URL"
            required
            className="w-full p-4 border-2 border-[#e1e5e9] rounded-lg text-base transition-all bg-white focus:outline-none focus:border-indigo-400 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
            disabled={loading}
          />
        </div>
        <div className="flex gap-8 justify-center mb-6">
          <label className="flex items-center gap-2 font-medium cursor-pointer px-4 py-2 rounded-lg transition hover:bg-indigo-100">
            <input
              type="radio"
              value="single"
              checked={cloneMode === 'single'}
              onChange={(e) => setCloneMode(e.target.value as 'single')}
              className="accent-indigo-500 scale-110"
            />
            Single Page
          </label>
          <label className="flex items-center gap-2 font-medium cursor-pointer px-4 py-2 rounded-lg transition hover:bg-indigo-100">
            <input
              type="radio"
              value="multipage"
              checked={cloneMode === 'multipage'}
              onChange={(e) => setCloneMode(e.target.value as 'multipage')}
              className="accent-indigo-500 scale-110"
            />
            Multi-Page Site
          </label>
        </div>
        {cloneMode === 'multipage' && (
          <div className="mb-6 p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
            <label className="flex items-center gap-2 font-medium relative group text-nowrap">
              Max Pages:
              <span className="ml-1 cursor-pointer text-indigo-500 relative">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-4 w-4 inline-block"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="white"/>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 16v-4m0-4h.01" />
                </svg>
                <span className="absolute left-1/2 top-full z-20 mt-2 w-72 -translate-x-1/2 rounded bg-gray-900 text-white text-xs px-3 py-2 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-200 shadow-lg font-roboto whitespace-normal">
                  <span className="absolute -top-2 left-1/2 -translate-x-1/2 w-3 h-3 bg-gray-900 rotate-45"></span>
                  Note: The number of pages you can clone is limited to 20. For most websites, use single page clone mode. If you need more pages, it is recommended to clone them individually for better design accuracy.
                </span>
              </span>
              <input
                type="number"
                value={maxPages}
                onChange={(e) => setMaxPages(Number(e.target.value))}
                min="1"
                max="20"
                className="p-2 border border-[#e1e5e9] rounded w-20 ml-2"
              />
            </label>
          </div>
        )}
        {cloneMode === 'single' && (
          <div className="mb-6 flex justify-center">
            <label className="flex items-center gap-2 font-medium cursor-pointer px-4 py-2 rounded-lg transition hover:bg-indigo-100">
              <input
                type="checkbox"
                checked={streamingMode}
                onChange={(e) => setStreamingMode(e.target.checked)}
                className="accent-indigo-500 scale-110"
              />
              Real-time streaming
            </label>
          </div>
        )}
        <div className="flex gap-4 justify-center mb-4">
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-3 rounded-lg text-white font-medium min-w-[120px] bg-gradient-to-br from-indigo-400 to-purple-700 shadow-md transition-all disabled:opacity-60 disabled:cursor-not-allowed hover:-translate-y-0.5 hover:shadow-lg"
          >
            {loading ? (cloneMode === 'multipage' ? 'Cloning Pages...' : 'Cloning...') : (cloneMode === 'multipage' ? 'Clone Website' : 'Clone Page')}
          </button>
        </div>
        {streamingMode && streamStatus && (
          <div className="bg-white/95 backdrop-blur-lg p-6 rounded-xl mb-8 border border-white/20">
            <div className="flex items-center gap-4 text-indigo-500 font-medium">
              {!streamStatus.toLowerCase().includes("complete") && (
                <span className="w-5 h-5 border-2 border-indigo-200 border-t-indigo-500 rounded-full animate-spin"></span>
              )}
              <span>{streamStatus}</span>
            </div>
          </div>
        )}
      </form>
      {error && (
        <div className="bg-red-100 text-red-700 p-4 rounded mb-4 font-medium">{error}</div>
      )}
      {metadata && (
        <div className="bg-white/90 rounded-lg p-4 mb-6 shadow border border-white/20">
          <h3 className="font-semibold mb-2">Clone Statistics</h3>
          <div className="flex flex-wrap gap-4 text-sm">
            {cloneMode === 'multipage' && metadata.total_pages_cloned && (
              <span>Pages cloned: {metadata.total_pages_cloned}</span>
            )}
            <span>Processing time: {metadata.processing_time_seconds?.toFixed(2)}s</span>
            <span>HTML size: {(metadata.html_length || metadata.total_html_length || 0).toLocaleString()} chars</span>
          </div>
        </div>
      )}
      {multiPageResult && (
        <div className="bg-white/90 rounded-lg p-4 mb-6 shadow border border-white/20">
          <h3 className="font-semibold mb-2">Select Page to Preview:</h3>
          <select
            value={selectedPage}
            onChange={(e) => handlePageSelect(e.target.value)}
            className="p-2 border border-indigo-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-400 mb-2"
          >
            {Object.keys(multiPageResult).map((path) => (
              <option key={path} value={path}>
                {path === '' || path === '/' ? 'Homepage' : path}
              </option>
            ))}
          </select>
          <button
            onClick={downloadAllPages}
            className="ml-4 px-4 py-2 rounded-lg border-2 border-indigo-400 text-indigo-600 bg-white hover:bg-indigo-500 hover:text-white transition font-medium"
          >
            Download All Pages
          </button>
        </div>
      )}
      {result && (
        <div className="mt-8 bg-white/95 rounded-2xl shadow-xl p-6 border border-white/20">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">{cloneMode === 'multipage' && selectedPage ? `Page: ${selectedPage === '' || selectedPage === '/' ? 'Homepage' : selectedPage}` : 'Cloned Website Preview'}</h2>
            <button
              onClick={downloadHtml}
              className="px-4 py-2 rounded-lg border-2 border-indigo-400 text-indigo-600 bg-white hover:bg-indigo-500 hover:text-white transition font-medium"
            >
              Download HTML
            </button>
          </div>
          <div className="w-full min-h-[600px] border rounded-xl bg-white shadow overflow-auto">
            <iframe
              srcDoc={result}
              className="w-full min-h-[600px] rounded-xl border-none"
              title="Cloned Website Preview"
              sandbox="allow-same-origin allow-scripts"
            />
          </div>
          {showAdvanced && (
            <details className="mt-6">
              <summary className="cursor-pointer text-indigo-600 font-medium">View Generated HTML</summary>
              <pre className="bg-gray-100 rounded p-4 mt-2 overflow-x-auto text-xs">
                <code>{result}</code>
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}