'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';

interface ChatBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  sources?: Array<{ title: string }>;
}

export function ChatBubble({ role, content, sources = [] }: ChatBubbleProps) {
  const isUser = role === 'user';

  return (
    <div className={`chat-bubble ${isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'}`}>
      {isUser ? (
        <p className="chat-user-text">{content}</p>
      ) : (
        <div className="chat-markdown">
          <ReactMarkdown
            components={{
              h1: ({ children, ...props }) => <h1 className="brand-h1" {...props}>{children}</h1>,
              h2: ({ children, ...props }) => <h2 className="brand-h2" {...props}>{children}</h2>,
              h3: ({ children, ...props }) => <h3 className="brand-h3" {...props}>{children}</h3>,
              p: ({ children, ...props }) => <p className="brand-p" {...props}>{children}</p>,
              strong: ({ children, ...props }) => <strong className="brand-strong" {...props}>{children}</strong>,
              ul: ({ children, ...props }) => <ul className="brand-list" {...props}>{children}</ul>,
              ol: ({ children, ...props }) => <ol className="brand-list" {...props}>{children}</ol>,
              li: ({ children, ...props }) => <li className="brand-list-item" {...props}>{children}</li>,
              blockquote: ({ children, ...props }) => <blockquote className="brand-callout" {...props}>{children}</blockquote>,
            }}
          >
            {content}
          </ReactMarkdown>
          {sources.length > 0 && (
            <p className="chat-sources">Sources: {sources.map((source) => source.title).join(', ')}</p>
          )}
        </div>
      )}
    </div>
  );
}