import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Collapse,
  IconButton,
  Chip,
  CircularProgress,
  Tooltip,
  Fade,
  Zoom,
  Button,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Psychology as ThinkingIcon,
  Build as ToolIcon,
  Analytics as AnalysisIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';

export interface ReasoningStep {
  step_number: number;
  step_type: 'planning' | 'tool_call' | 'analysis' | 'synthesis' | 'final_answer' | 'error';
  description: string;
  content: string;
  tool_call?: {
    tool: string;
    parameters: Record<string, any>;
  };
  tool_result?: any;
  duration_ms?: number;
  timestamp: string;
}

interface ReasoningChainProps {
  steps: ReasoningStep[];
  isActive: boolean;
  autoCollapse?: boolean;
  showPerformanceMetrics?: boolean;
}

export const ReasoningChain: React.FC<ReasoningChainProps> = ({
  steps,
  isActive,
  autoCollapse = true,
  showPerformanceMetrics = true,
}) => {
  const [expanded, setExpanded] = useState(true);
  const [copiedSnackbar, setCopiedSnackbar] = useState(false);
  const [highlightedStep, setHighlightedStep] = useState<number | null>(null);

  // Auto-collapse after completion if enabled
  useEffect(() => {
    if (!isActive && steps.length > 0 && autoCollapse) {
      const timer = setTimeout(() => {
        setExpanded(false);
      }, 3000); // Collapse 3 seconds after completion
      return () => clearTimeout(timer);
    }
  }, [isActive, steps.length, autoCollapse]);

  // Highlight newest step with animation
  useEffect(() => {
    if (steps.length > 0 && isActive) {
      const latestStep = steps[steps.length - 1].step_number;
      setHighlightedStep(latestStep);

      const timer = setTimeout(() => {
        setHighlightedStep(null);
      }, 1500);

      return () => clearTimeout(timer);
    }
  }, [steps.length, isActive]);

  const getStepIcon = (type: string) => {
    switch (type) {
      case 'planning':
        return <ThinkingIcon sx={{ color: '#007AFF', fontSize: '1.2rem' }} />;
      case 'tool_call':
        return <ToolIcon sx={{ color: '#34C759', fontSize: '1.2rem' }} />;
      case 'analysis':
        return <AnalysisIcon sx={{ color: '#FF9500', fontSize: '1.2rem' }} />;
      case 'synthesis':
        return <ThinkingIcon sx={{ color: '#5856D6', fontSize: '1.2rem' }} />;
      case 'final_answer':
        return <CompleteIcon sx={{ color: '#34C759', fontSize: '1.2rem' }} />;
      case 'error':
        return <ErrorIcon sx={{ color: '#FF3B30', fontSize: '1.2rem' }} />;
      default:
        return <ThinkingIcon sx={{ color: '#8E8E93', fontSize: '1.2rem' }} />;
    }
  };

  const getStepColor = (type: string) => {
    switch (type) {
      case 'planning':
        return 'rgba(0, 122, 255, 0.1)';
      case 'tool_call':
        return 'rgba(52, 199, 89, 0.1)';
      case 'analysis':
        return 'rgba(255, 149, 0, 0.1)';
      case 'synthesis':
        return 'rgba(88, 86, 214, 0.1)';
      case 'final_answer':
        return 'rgba(52, 199, 89, 0.15)';
      case 'error':
        return 'rgba(255, 59, 48, 0.1)';
      default:
        return 'rgba(142, 142, 147, 0.1)';
    }
  };

  const getStepBorderColor = (type: string) => {
    switch (type) {
      case 'planning':
        return 'rgba(0, 122, 255, 0.3)';
      case 'tool_call':
        return 'rgba(52, 199, 89, 0.3)';
      case 'analysis':
        return 'rgba(255, 149, 0, 0.3)';
      case 'synthesis':
        return 'rgba(88, 86, 214, 0.3)';
      case 'final_answer':
        return 'rgba(52, 199, 89, 0.4)';
      case 'error':
        return 'rgba(255, 59, 48, 0.3)';
      default:
        return 'rgba(142, 142, 147, 0.3)';
    }
  };

  const calculateTotalDuration = () => {
    return steps.reduce((total, step) => total + (step.duration_ms || 0), 0);
  };

  const handleCopyChain = () => {
    const chainText = steps.map((step, index) => {
      let text = `Step ${step.step_number}: ${step.description}\n`;
      if (step.content) text += `Reasoning: ${step.content}\n`;
      if (step.tool_call) {
        text += `Tool: ${step.tool_call.tool}\n`;
        text += `Parameters: ${JSON.stringify(step.tool_call.parameters, null, 2)}\n`;
      }
      if (step.tool_result) {
        text += `Result: ${JSON.stringify(step.tool_result, null, 2)}\n`;
      }
      if (step.duration_ms) text += `Duration: ${step.duration_ms}ms\n`;
      return text;
    }).join('\n---\n\n');

    navigator.clipboard.writeText(chainText);
    setCopiedSnackbar(true);
  };

  const handleExportMarkdown = () => {
    const markdown = `# Chain of Thought Reasoning\n\n` +
      `**Total Steps:** ${steps.length}\n` +
      `**Total Duration:** ${calculateTotalDuration()}ms\n` +
      `**Completed:** ${new Date().toLocaleString()}\n\n` +
      `---\n\n` +
      steps.map((step) => {
        let md = `## ${step.step_number}. ${step.description}\n\n`;
        md += `**Type:** ${step.step_type}\n\n`;
        if (step.content) md += `**Reasoning:**\n> ${step.content}\n\n`;
        if (step.tool_call) {
          md += `**Tool Call:**\n\`\`\`json\n${JSON.stringify(step.tool_call, null, 2)}\n\`\`\`\n\n`;
        }
        if (step.tool_result) {
          md += `**Result:**\n\`\`\`json\n${JSON.stringify(step.tool_result, null, 2)}\n\`\`\`\n\n`;
        }
        if (step.duration_ms) md += `⏱️ *${step.duration_ms}ms*\n\n`;
        return md;
      }).join('---\n\n');

    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reasoning-chain-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (steps.length === 0) return null;

  const totalDuration = calculateTotalDuration();
  const avgStepDuration = steps.length > 0 ? Math.round(totalDuration / steps.length) : 0;

  return (
    <>
      <Fade in={true} timeout={500}>
        <Paper
          elevation={0}
          sx={{
            border: '1px solid rgba(0, 0, 0, 0.08)',
            borderRadius: 3,
            overflow: 'hidden',
            mb: 2,
            backgroundColor: '#FAFAFA',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            '&:hover': {
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
            },
          }}
        >
          {/* Header */}
          <Box
            onClick={() => setExpanded(!expanded)}
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              p: 1.5,
              cursor: 'pointer',
              backgroundColor: isActive
                ? 'rgba(0, 122, 255, 0.08)'
                : 'rgba(0, 122, 255, 0.05)',
              borderBottom: expanded ? '1px solid rgba(0, 0, 0, 0.06)' : 'none',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                backgroundColor: 'rgba(0, 122, 255, 0.12)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
              <ThinkingIcon sx={{
                color: '#007AFF',
                fontSize: '1.3rem',
                animation: isActive ? 'pulse 2s ease-in-out infinite' : 'none',
                '@keyframes pulse': {
                  '0%, 100%': { opacity: 1 },
                  '50%': { opacity: 0.5 },
                },
              }} />
              <Typography variant="body2" sx={{ fontWeight: 600, color: '#007AFF' }}>
                Chain of Thought Reasoning
              </Typography>
              <Chip
                label={steps.length}
                size="small"
                sx={{
                  backgroundColor: '#007AFF',
                  color: 'white',
                  height: 20,
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  transition: 'transform 0.2s',
                  '&:hover': {
                    transform: 'scale(1.1)',
                  },
                }}
              />
              {isActive && (
                <Zoom in={true}>
                  <Tooltip title="Processing...">
                    <CircularProgress size={14} sx={{ color: '#007AFF', ml: 0.5 }} />
                  </Tooltip>
                </Zoom>
              )}
              {!isActive && showPerformanceMetrics && totalDuration > 0 && (
                <Fade in={true}>
                  <Chip
                    icon={<SpeedIcon sx={{ fontSize: '0.9rem' }} />}
                    label={`${(totalDuration / 1000).toFixed(1)}s`}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: '0.65rem',
                      backgroundColor: 'rgba(52, 199, 89, 0.1)',
                      color: '#34C759',
                      border: '1px solid rgba(52, 199, 89, 0.2)',
                    }}
                  />
                </Fade>
              )}
            </Box>

            <Box sx={{ display: 'flex', gap: 0.5 }}>
              {!isActive && steps.length > 0 && (
                <>
                  <Tooltip title="Copy reasoning chain">
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCopyChain();
                      }}
                      sx={{
                        opacity: 0.7,
                        '&:hover': { opacity: 1, backgroundColor: 'rgba(0, 122, 255, 0.1)' },
                      }}
                    >
                      <CopyIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Export as Markdown">
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleExportMarkdown();
                      }}
                      sx={{
                        opacity: 0.7,
                        '&:hover': { opacity: 1, backgroundColor: 'rgba(0, 122, 255, 0.1)' },
                      }}
                    >
                      <DownloadIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </>
              )}
              <IconButton
                size="small"
                sx={{
                  transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                }}
              >
                <ExpandMoreIcon />
              </IconButton>
            </Box>
          </Box>

          {/* Steps */}
          <Collapse in={expanded} timeout={400}>
            <Box sx={{ p: 2 }}>
              {steps.map((step, index) => (
                <Fade key={index} in={true} timeout={300} style={{ transitionDelay: `${index * 50}ms` }}>
                  <Box
                    sx={{
                      display: 'flex',
                      gap: 2,
                      mb: index < steps.length - 1 ? 2.5 : 0,
                      position: 'relative',
                      animation: highlightedStep === step.step_number
                        ? 'highlight 1.5s ease-in-out'
                        : 'none',
                      '@keyframes highlight': {
                        '0%, 100%': { transform: 'scale(1)' },
                        '50%': { transform: 'scale(1.02)', backgroundColor: 'rgba(0, 122, 255, 0.05)' },
                      },
                    }}
                  >
                    {/* Connector line */}
                    {index < steps.length - 1 && (
                      <Box
                        sx={{
                          position: 'absolute',
                          left: 20,
                          top: 40,
                          bottom: -20,
                          width: 2,
                          backgroundColor: 'rgba(0, 0, 0, 0.08)',
                          animation: 'growLine 0.5s ease-out',
                          '@keyframes growLine': {
                            '0%': { height: 0 },
                            '100%': { height: '100%' },
                          },
                        }}
                      />
                    )}

                    {/* Step icon */}
                    <Zoom in={true} timeout={300} style={{ transitionDelay: `${index * 50}ms` }}>
                      <Box
                        sx={{
                          width: 40,
                          height: 40,
                          borderRadius: '50%',
                          backgroundColor: getStepColor(step.step_type),
                          border: `2px solid ${getStepBorderColor(step.step_type)}`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                          zIndex: 1,
                          transition: 'transform 0.2s, box-shadow 0.2s',
                          '&:hover': {
                            transform: 'scale(1.1)',
                            boxShadow: '0 4px 8px rgba(0, 0, 0, 0.15)',
                          },
                        }}
                      >
                        {getStepIcon(step.step_type)}
                      </Box>
                    </Zoom>

                    {/* Step content */}
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 600,
                            color: '#1D1D1F',
                            transition: 'color 0.2s',
                          }}
                        >
                          {step.description}
                        </Typography>
                        {step.duration_ms !== undefined && step.duration_ms > 0 && (
                          <Fade in={true}>
                            <Chip
                              label={`${step.duration_ms}ms`}
                              size="small"
                              sx={{
                                height: 18,
                                fontSize: '0.65rem',
                                backgroundColor: step.duration_ms > avgStepDuration
                                  ? 'rgba(255, 149, 0, 0.1)'
                                  : 'rgba(0, 0, 0, 0.05)',
                                color: step.duration_ms > avgStepDuration ? '#FF9500' : '#6e6e73',
                              }}
                            />
                          </Fade>
                        )}
                      </Box>

                      {step.content && step.step_type !== 'final_answer' && (
                        <Typography
                          variant="body2"
                          sx={{
                            color: '#6e6e73',
                            fontSize: '0.875rem',
                            mb: 1,
                            fontStyle: 'italic',
                            lineHeight: 1.5,
                          }}
                        >
                          {step.content}
                        </Typography>
                      )}

                      {/* Tool call details */}
                      {step.tool_call && (
                        <Fade in={true} timeout={400}>
                          <Paper
                            elevation={0}
                            sx={{
                              backgroundColor: 'rgba(0, 0, 0, 0.03)',
                              p: 1.5,
                              borderRadius: 2,
                              border: '1px solid rgba(0, 0, 0, 0.06)',
                              mb: 1,
                              transition: 'all 0.2s',
                              '&:hover': {
                                backgroundColor: 'rgba(0, 0, 0, 0.04)',
                                borderColor: 'rgba(0, 0, 0, 0.12)',
                              },
                            }}
                          >
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                              <ToolIcon sx={{ fontSize: '0.9rem', color: '#34C759' }} />
                              <Typography variant="caption" sx={{ fontWeight: 600, color: '#1D1D1F' }}>
                                Tool: {step.tool_call.tool}
                              </Typography>
                            </Box>
                            <Box
                              component="pre"
                              sx={{
                                fontSize: '0.75rem',
                                margin: 0,
                                fontFamily: '"SF Mono", "Monaco", "Inconsolata", monospace',
                                color: '#6e6e73',
                                overflowX: 'auto',
                                backgroundColor: 'rgba(255, 255, 255, 0.5)',
                                p: 1,
                                borderRadius: 1,
                                '&::-webkit-scrollbar': {
                                  height: '6px',
                                },
                                '&::-webkit-scrollbar-thumb': {
                                  backgroundColor: 'rgba(0, 0, 0, 0.2)',
                                  borderRadius: '3px',
                                },
                              }}
                            >
                              {JSON.stringify(step.tool_call.parameters, null, 2)}
                            </Box>
                          </Paper>
                        </Fade>
                      )}

                      {/* Tool result */}
                      {step.tool_result && (
                        <Fade in={true} timeout={400}>
                          <Paper
                            elevation={0}
                            sx={{
                              backgroundColor: step.tool_result.success
                                ? 'rgba(52, 199, 89, 0.05)'
                                : 'rgba(255, 59, 48, 0.05)',
                              p: 1.5,
                              borderRadius: 2,
                              border: step.tool_result.success
                                ? '1px solid rgba(52, 199, 89, 0.2)'
                                : '1px solid rgba(255, 59, 48, 0.2)',
                              mb: 1,
                              transition: 'all 0.2s',
                              '&:hover': {
                                borderColor: step.tool_result.success
                                  ? 'rgba(52, 199, 89, 0.4)'
                                  : 'rgba(255, 59, 48, 0.4)',
                              },
                            }}
                          >
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                              {step.tool_result.success ? (
                                <CompleteIcon sx={{ fontSize: '0.9rem', color: '#34C759' }} />
                              ) : (
                                <ErrorIcon sx={{ fontSize: '0.9rem', color: '#FF3B30' }} />
                              )}
                              <Typography
                                variant="caption"
                                sx={{
                                  fontWeight: 600,
                                  color: step.tool_result.success ? '#34C759' : '#FF3B30',
                                }}
                              >
                                {step.tool_result.success ? 'Success' : 'Failed'}
                              </Typography>
                            </Box>
                            {step.tool_result.count !== undefined && (
                              <Typography variant="caption" sx={{ display: 'block', color: '#6e6e73' }}>
                                Found: {step.tool_result.count} items
                              </Typography>
                            )}
                            {step.tool_result.email_count !== undefined && (
                              <Typography variant="caption" sx={{ display: 'block', color: '#6e6e73' }}>
                                Emails processed: {step.tool_result.email_count}
                              </Typography>
                            )}
                            {step.tool_result.error && (
                              <Typography
                                variant="caption"
                                sx={{
                                  display: 'block',
                                  color: '#FF3B30',
                                  mt: 0.5,
                                  fontFamily: 'monospace',
                                  fontSize: '0.7rem',
                                }}
                              >
                                Error: {step.tool_result.error}
                              </Typography>
                            )}
                          </Paper>
                        </Fade>
                      )}
                    </Box>
                  </Box>
                </Fade>
              ))}

              {/* Performance Summary */}
              {!isActive && showPerformanceMetrics && steps.length > 0 && (
                <Fade in={true} timeout={600}>
                  <Box
                    sx={{
                      mt: 3,
                      p: 1.5,
                      borderRadius: 2,
                      backgroundColor: 'rgba(88, 86, 214, 0.05)',
                      border: '1px solid rgba(88, 86, 214, 0.15)',
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <SpeedIcon sx={{ fontSize: '1rem', color: '#5856D6' }} />
                      <Typography variant="caption" sx={{ fontWeight: 600, color: '#5856D6' }}>
                        Performance Summary
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                      <Typography variant="caption" sx={{ color: '#6e6e73' }}>
                        Total: <strong>{(totalDuration / 1000).toFixed(2)}s</strong>
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#6e6e73' }}>
                        Avg/step: <strong>{avgStepDuration}ms</strong>
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#6e6e73' }}>
                        Steps: <strong>{steps.length}</strong>
                      </Typography>
                    </Box>
                  </Box>
                </Fade>
              )}
            </Box>
          </Collapse>
        </Paper>
      </Fade>

      {/* Snackbar for copy confirmation */}
      <Snackbar
        open={copiedSnackbar}
        autoHideDuration={2000}
        onClose={() => setCopiedSnackbar(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setCopiedSnackbar(false)}
          severity="success"
          sx={{ width: '100%' }}
        >
          Reasoning chain copied to clipboard!
        </Alert>
      </Snackbar>
    </>
  );
};
