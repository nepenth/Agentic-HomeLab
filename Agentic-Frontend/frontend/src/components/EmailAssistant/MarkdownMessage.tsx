import React from 'react';
import { Box, Typography, Paper, Chip } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import {
  Email as EmailIcon,
  CalendarToday as CalendarIcon,
  AttachMoney as MoneyIcon,
  LocalShipping as ShippingIcon,
  Link as LinkIcon
} from '@mui/icons-material';

interface MarkdownMessageProps {
  content: string;
  role: 'user' | 'assistant';
}

/**
 * MarkdownMessage component renders chat messages with rich markdown formatting
 * Features:
 * - GitHub Flavored Markdown (tables, strikethrough, task lists)
 * - Syntax highlighting for code blocks
 * - Custom styling for headings, lists, quotes
 * - Email/tracking number detection and highlighting
 * - Apple-inspired design system
 */
const MarkdownMessage: React.FC<MarkdownMessageProps> = ({ content, role }) => {
  // Detect special patterns for enhanced rendering
  const containsTracking = /\b[0-9A-Z]{18,}\b|\b1Z[0-9A-Z]{16}\b/i.test(content);
  const containsOrderNumber = /#[0-9A-Z-]{5,}/i.test(content);
  const containsEmail = /\[Email \d+\]/i.test(content);

  return (
    <Box
      sx={{
        width: '100%',
        '& .markdown-content': {
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
          fontSize: '0.95rem',
          lineHeight: 1.6,
          color: role === 'user' ? '#fff' : '#1d1d1f',

          // Headings
          '& h1, & h2, & h3, & h4, & h5, & h6': {
            fontWeight: 600,
            marginTop: '1.5em',
            marginBottom: '0.5em',
            lineHeight: 1.3,
          },
          '& h1': {
            fontSize: '1.75rem',
            borderBottom: '2px solid rgba(0, 0, 0, 0.1)',
            paddingBottom: '0.3em',
          },
          '& h2': {
            fontSize: '1.5rem',
            borderBottom: '1px solid rgba(0, 0, 0, 0.08)',
            paddingBottom: '0.3em',
          },
          '& h3': {
            fontSize: '1.25rem',
          },
          '& h4': {
            fontSize: '1.1rem',
          },

          // Paragraphs
          '& p': {
            marginTop: '0.5em',
            marginBottom: '0.5em',
          },

          // Lists
          '& ul, & ol': {
            paddingLeft: '1.5em',
            marginTop: '0.5em',
            marginBottom: '0.5em',
          },
          '& li': {
            marginTop: '0.25em',
            marginBottom: '0.25em',
          },
          '& ul > li::marker': {
            color: '#007AFF',
          },

          // Code blocks
          '& pre': {
            backgroundColor: role === 'user' ? 'rgba(0, 0, 0, 0.2)' : '#f5f5f7',
            borderRadius: '8px',
            padding: '1em',
            overflow: 'auto',
            border: role === 'user' ? '1px solid rgba(255, 255, 255, 0.1)' : '1px solid rgba(0, 0, 0, 0.08)',
          },
          '& code': {
            backgroundColor: role === 'user' ? 'rgba(0, 0, 0, 0.2)' : '#f5f5f7',
            padding: '0.2em 0.4em',
            borderRadius: '4px',
            fontSize: '0.9em',
            fontFamily: 'Menlo, Monaco, "Courier New", monospace',
          },
          '& pre code': {
            backgroundColor: 'transparent',
            padding: 0,
          },

          // Blockquotes
          '& blockquote': {
            borderLeft: '4px solid #007AFF',
            paddingLeft: '1em',
            marginLeft: 0,
            marginRight: 0,
            color: role === 'user' ? 'rgba(255, 255, 255, 0.8)' : '#6e6e73',
            fontStyle: 'italic',
          },

          // Links
          '& a': {
            color: role === 'user' ? '#5AC8FA' : '#007AFF',
            textDecoration: 'none',
            fontWeight: 500,
            '&:hover': {
              textDecoration: 'underline',
            },
          },

          // Tables
          '& table': {
            width: '100%',
            borderCollapse: 'collapse',
            marginTop: '1em',
            marginBottom: '1em',
            fontSize: '0.9em',
          },
          '& thead': {
            backgroundColor: role === 'user' ? 'rgba(0, 0, 0, 0.2)' : '#f5f5f7',
          },
          '& th': {
            padding: '0.75em',
            textAlign: 'left',
            fontWeight: 600,
            borderBottom: '2px solid rgba(0, 0, 0, 0.1)',
          },
          '& td': {
            padding: '0.75em',
            borderBottom: '1px solid rgba(0, 0, 0, 0.06)',
          },
          '& tr:last-child td': {
            borderBottom: 'none',
          },

          // Horizontal rules
          '& hr': {
            border: 'none',
            borderTop: '1px solid rgba(0, 0, 0, 0.1)',
            marginTop: '1.5em',
            marginBottom: '1.5em',
          },

          // Strong/Bold
          '& strong, & b': {
            fontWeight: 600,
            color: role === 'user' ? '#fff' : '#1d1d1f',
          },

          // Emphasis/Italic
          '& em, & i': {
            fontStyle: 'italic',
          },

          // Strikethrough
          '& del': {
            textDecoration: 'line-through',
            opacity: 0.7,
          },

          // Task lists (GFM)
          '& input[type="checkbox"]': {
            marginRight: '0.5em',
          },
        },
      }}
    >
      {/* Context chips for detected patterns */}
      {(containsTracking || containsOrderNumber || containsEmail) && (
        <Box sx={{ display: 'flex', gap: 0.5, mb: 1, flexWrap: 'wrap' }}>
          {containsTracking && (
            <Chip
              icon={<ShippingIcon sx={{ fontSize: '0.9rem' }} />}
              label="Tracking Info"
              size="small"
              sx={{
                backgroundColor: role === 'user' ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 122, 255, 0.1)',
                color: role === 'user' ? '#fff' : '#007AFF',
                fontSize: '0.7rem',
                height: 20,
              }}
            />
          )}
          {containsOrderNumber && (
            <Chip
              icon={<MoneyIcon sx={{ fontSize: '0.9rem' }} />}
              label="Order Details"
              size="small"
              sx={{
                backgroundColor: role === 'user' ? 'rgba(255, 255, 255, 0.2)' : 'rgba(52, 199, 89, 0.1)',
                color: role === 'user' ? '#fff' : '#34C759',
                fontSize: '0.7rem',
                height: 20,
              }}
            />
          )}
          {containsEmail && (
            <Chip
              icon={<EmailIcon sx={{ fontSize: '0.9rem' }} />}
              label="Email References"
              size="small"
              sx={{
                backgroundColor: role === 'user' ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 149, 0, 0.1)',
                color: role === 'user' ? '#fff' : '#FF9500',
                fontSize: '0.7rem',
                height: 20,
              }}
            />
          )}
        </Box>
      )}

      {/* Markdown content */}
      <ReactMarkdown
        className="markdown-content"
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, rehypeSanitize]}
        components={{
          // Custom rendering for specific elements
          a: ({ node, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer">
              {props.children}
              <LinkIcon sx={{ fontSize: '0.8rem', ml: 0.3, verticalAlign: 'middle' }} />
            </a>
          ),

          // Enhance code blocks with language detection
          code: ({ node, inline, className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : '';

            return inline ? (
              <code className={className} {...props}>
                {children}
              </code>
            ) : (
              <Box sx={{ position: 'relative' }}>
                {language && (
                  <Typography
                    variant="caption"
                    sx={{
                      position: 'absolute',
                      top: 8,
                      right: 8,
                      backgroundColor: 'rgba(0, 0, 0, 0.1)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      textTransform: 'uppercase',
                    }}
                  >
                    {language}
                  </Typography>
                )}
                <pre>
                  <code className={className} {...props}>
                    {children}
                  </code>
                </pre>
              </Box>
            );
          },

          // Style tables with Paper wrapper
          table: ({ node, ...props }) => (
            <Paper
              elevation={0}
              sx={{
                overflow: 'hidden',
                border: '1px solid rgba(0, 0, 0, 0.08)',
                borderRadius: '8px',
                marginTop: '1em',
                marginBottom: '1em',
              }}
            >
              <table {...props} />
            </Paper>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </Box>
  );
};

export default MarkdownMessage;
