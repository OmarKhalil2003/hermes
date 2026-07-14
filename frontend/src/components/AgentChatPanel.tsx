"use client";

import React, { useState, useRef, useEffect } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  thoughtProcess: string[];
  citations: Array<{ filename: string; content: string }>;
  isStreaming?: boolean;
}

export default function AgentChatPanel() {
  const [query, setQuery] = useState("");
  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [activeNodes, setActiveNodes] = useState<string[]>([]);
  const [currentNode, setCurrentNode] = useState<string | null>(null);
  
  // Citation Modal state
  const [selectedCitation, setSelectedCitation] = useState<{ filename: string; content: string } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat window
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeNodes]);

  // Clean Markdown Parser
  const parseMarkdown = (text: string): string => {
    let html = text;

    // Escaping tags for safety
    html = html
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Code blocks
    html = html.replace(/```(.*?)\n([\s\S]*?)```/g, (_, lang, code) => {
      return `<pre class="bg-zinc-950 p-4 rounded-xl border border-zinc-800 overflow-x-auto text-xs font-mono text-zinc-300 my-4"><code class="language-${lang}">${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(
      /`(.*?)`/g,
      '<code class="bg-zinc-900 px-1.5 py-0.5 rounded text-xs font-mono text-indigo-400">$1</code>'
    );

    // Headings
    html = html.replace(
      /^### (.*?)$/gm,
      '<h3 class="text-md font-bold text-emerald-400 mt-4 mb-2">$1</h3>'
    );
    html = html.replace(
      /^## (.*?)$/gm,
      '<h2 class="text-lg font-bold text-indigo-400 mt-5 mb-2">$1</h2>'
    );
    html = html.replace(
      /^# (.*?)$/gm,
      '<h1 class="text-xl font-extrabold text-white mt-6 mb-3 border-b border-zinc-900 pb-1">$1</h1>'
    );

    // Bold & Italic
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

    // Bullet points
    html = html.replace(/^\s*-\s+(.*?)$/gm, '<li class="ml-4 list-disc text-zinc-300 text-sm my-1">$1</li>');

    // Base64 Images Embed
    html = html.replace(
      /!\[(.*?)\]\((data:image\/.*?;base64,.*?)\)/g,
      '<img src="$2" alt="$1" class="my-4 rounded-xl border border-zinc-800 max-w-full shadow-lg h-auto" />'
    );

    // Paragraph wrapping for free lines
    const lines = html.split("\n");
    const parsedLines = lines.map((line) => {
      const trimmed = line.trim();
      if (!trimmed) return "<br/>";
      if (
        trimmed.startsWith("<h") ||
        trimmed.startsWith("<pre") ||
        trimmed.startsWith("</pre") ||
        trimmed.startsWith("<img") ||
        trimmed.startsWith("<li")
      ) {
        return line;
      }
      return `<p class="my-2 leading-relaxed text-zinc-300 text-sm">${line}</p>`;
    });

    return parsedLines.join("\n");
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isSending) return;

    const userMessage: Message = {
      id: Math.random().toString(),
      role: "user",
      content: query,
      thoughtProcess: [],
      citations: [],
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setIsSending(true);
    setActiveNodes([]);
    setCurrentNode(null);

    // Initial assistant streaming slot
    const assistantMessageId = Math.random().toString();
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      thoughtProcess: [],
      citations: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      const accessToken = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const apiUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/agents/research`;

      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({
          query: userMessage.content,
          thread_id: threadId || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error("FastAPI Agent router connection failed.");
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Response body is not readable.");
      }

      const decoder = new TextDecoder();
      let buffer = "";
      let accumulatedToken = "";
      let retrievedDocs: Array<{ filename: string; content: string }> = [];

      // Fetch sample citations in the background to mock tooltip snippet contents if available
      try {
        const docSearchUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/documents/search?query=${encodeURIComponent(userMessage.content)}&limit=3`;
        const docRes = await fetch(docSearchUrl, {
          headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        });
        if (docRes.ok) {
          const docData = await docRes.json();
          retrievedDocs = docData.map((d: { filename: string; content: string }) => ({
            filename: d.filename,
            content: d.content,
          }));
        }
      } catch (err) {
        console.error("Failed to preload background citations:", err);
      }

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          if (trimmed.startsWith("event:")) {
            currentEvent = trimmed.slice(6).trim();
          } else if (trimmed.startsWith("data:")) {
            const dataStr = trimmed.slice(5).trim();
            try {
              const payload = JSON.parse(dataStr);
              
              if (currentEvent === "connect") {
                if (payload.thread_id) {
                  setThreadId(payload.thread_id);
                }
              } else if (currentEvent === "node_start") {
                const node = payload.node;
                setCurrentNode(node);
                setActiveNodes((prev) => [...prev, `${node} started`]);
                
                // Add to current message thoughtProcess logs
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, thoughtProcess: [...msg.thoughtProcess, `Entering Node: ${node}`] }
                      : msg
                  )
                );
              } else if (currentEvent === "node_end") {
                const node = payload.node;
                setCurrentNode(null);
                setActiveNodes((prev) => [...prev, `${node} finished`]);
                
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, thoughtProcess: [...msg.thoughtProcess, `Exited Node: ${node}`] }
                      : msg
                  )
                );
              } else if (currentEvent === "token") {
                const token = payload.token;
                accumulatedToken += token;
                
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: accumulatedToken }
                      : msg
                  )
                );
              } else if (currentEvent === "complete") {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, isStreaming: false, citations: retrievedDocs }
                      : msg
                  )
                );
              } else if (currentEvent === "error") {
                const errDetail = payload.detail || "Agent workflow execution failed.";
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? {
                          ...msg,
                          isStreaming: false,
                          content: `${msg.content}\n\n*Error during streaming: ${errDetail}*`,
                        }
                      : msg
                  )
                );
              }
            } catch (err) {
              console.error("Failed to parse SSE event segment:", err);
            }
          }
        }
      }
    } catch (err: unknown) {
      console.error(err);
      const errMsg = err instanceof Error ? err.message : String(err);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                isStreaming: false,
                content: `Failed to compile research response: ${errMsg}`,
              }
            : msg
        )
      );
    } finally {
      setIsSending(false);
      setCurrentNode(null);
    }
  };

  return (
    <div className="w-full rounded-2xl border border-zinc-800 bg-zinc-900/30 backdrop-blur-sm shadow-xl flex flex-col h-[650px] relative overflow-hidden">
      {/* Thread Metadata header */}
      <div className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between bg-zinc-900/40">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-indigo-500 animate-pulse"></span>
          <h3 className="text-sm font-semibold text-white">Multi-Agent Researcher</h3>
        </div>
        {threadId && (
          <span className="text-[10px] font-mono text-zinc-500 truncate max-w-[200px]" title={threadId}>
            Session: {threadId}
          </span>
        )}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4 px-8">
            <div className="h-12 w-12 rounded-xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h4 className="text-zinc-300 font-bold">Start Cooperative Research</h4>
            <p className="text-xs text-zinc-500 max-w-sm leading-relaxed">
              Ask questions or request documents. The Supervisor agent will coordinate the Retrieve, Research, Review, and Report compile nodes to generate deep answers.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex flex-col max-w-[85%] space-y-2 ${
                message.role === "user" ? "ml-auto items-end" : "mr-auto items-start"
              }`}
            >
              {/* Message content bubble */}
              <div
                className={`rounded-2xl px-5 py-4 text-sm shadow-md border ${
                  message.role === "user"
                    ? "bg-indigo-650 text-white border-indigo-550"
                    : "bg-zinc-950 text-zinc-100 border-zinc-850"
                }`}
              >
                {message.role === "user" ? (
                  <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
                ) : (
                  <div
                    className="prose prose-invert prose-sm leading-relaxed max-w-none text-zinc-200"
                    dangerouslySetInnerHTML={{ __html: parseMarkdown(message.content) }}
                  />
                )}
              </div>

              {/* Expandable Agent Thought Process timeline */}
              {message.role === "assistant" && message.thoughtProcess.length > 0 && (
                <details className="w-full text-xs text-zinc-500 border border-zinc-800/40 rounded-xl bg-zinc-950/20 transition-all select-none">
                  <summary className="px-4 py-2 hover:text-zinc-300 cursor-pointer font-medium flex items-center justify-between">
                    <span>Thought Process Timeline</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800">
                      {message.thoughtProcess.length} transitions
                    </span>
                  </summary>
                  <div className="px-4 pb-3 pt-1 border-t border-zinc-900/60 font-mono text-[10px] space-y-1.5 text-zinc-400 bg-zinc-950/40">
                    {message.thoughtProcess.map((log, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <span className="text-indigo-500">▶</span>
                        <span>{log}</span>
                      </div>
                    ))}
                  </div>
                </details>
              )}

              {/* Citations section */}
              {message.role === "assistant" && message.citations.length > 0 && (
                <div className="w-full flex flex-wrap gap-2 pt-1.5 items-center">
                  <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Citations:</span>
                  {message.citations.map((cit, idx) => (
                    <button
                      key={idx}
                      onClick={() => setSelectedCitation(cit)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-zinc-950 hover:bg-zinc-900 text-indigo-400 hover:text-indigo-300 border border-zinc-850 hover:border-zinc-700 font-mono text-[10px] transition-all cursor-pointer shadow-sm"
                    >
                      [{idx + 1}] {cit.filename}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))
        )}

        {/* Live stream loader */}
        {isSending && currentNode && (
          <div className="mr-auto max-w-[85%] rounded-2xl border border-zinc-850 bg-zinc-950 p-4 space-y-3 shadow-md animate-pulse">
            <div className="flex items-center gap-2.5 text-xs text-indigo-400 font-medium">
              <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Agent node active: {currentNode}...</span>
            </div>
            <div className="space-y-1.5">
              <div className="h-3 w-48 bg-zinc-900 rounded"></div>
              <div className="h-3 w-32 bg-zinc-900 rounded"></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input panel container */}
      <form onSubmit={handleSendMessage} className="border-t border-zinc-800 p-4 bg-zinc-900/40">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Ask Researcher: 'Compile a deep markdown study of deep neural network architectures...'"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isSending}
            className="flex-1 h-11 px-4 bg-zinc-950/80 text-white text-sm placeholder-zinc-500 rounded-xl border border-zinc-850 focus:border-indigo-500 focus:outline-none transition-all focus:ring-1 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={isSending || !query.trim()}
            className={`h-11 px-5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 shadow ${
              isSending || !query.trim()
                ? "bg-zinc-800 text-zinc-500 border border-zinc-750 cursor-not-allowed"
                : "bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer hover:shadow-indigo-500/10"
            }`}
          >
            {isSending ? "Streaming..." : "Analyze"}
          </button>
        </div>
      </form>

      {/* Citation Tooltip/Popup Modal */}
      {selectedCitation && (
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-zinc-950 border border-zinc-850 rounded-2xl max-w-xl w-full max-h-[85%] flex flex-col shadow-2xl relative overflow-hidden">
            {/* Header */}
            <div className="border-b border-zinc-900 px-5 py-4 flex items-center justify-between bg-zinc-900/20">
              <h4 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <span className="text-indigo-400">📄 Citation Snippet</span>
                <span className="text-[10px] text-zinc-500 font-normal truncate max-w-[200px]" title={selectedCitation.filename}>
                  ({selectedCitation.filename})
                </span>
              </h4>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-zinc-500 hover:text-zinc-300 text-xs font-bold cursor-pointer font-sans"
              >
                Close
              </button>
            </div>

            {/* Scrollable Snippet content */}
            <div className="flex-1 overflow-y-auto p-5 text-sm leading-relaxed text-zinc-300 whitespace-pre-wrap font-sans bg-zinc-950/40">
              {selectedCitation.content}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
