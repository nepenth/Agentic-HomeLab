import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Box, Paper, useTheme, alpha } from '@mui/material';

interface WebmailLayoutProps {
    sidebar: React.ReactNode;
    emailList: React.ReactNode;
    emailDetail: React.ReactNode;
    layoutMode: 'three-column' | 'horizontal-split' | 'vertical-split';
    emailViewerPosition: 'right' | 'below';
    isSidebarCollapsed: boolean;
    onToggleSidebar: () => void;
}

export const WebmailLayout: React.FC<WebmailLayoutProps> = ({
    sidebar,
    emailList,
    emailDetail,
    layoutMode,
    emailViewerPosition,
    isSidebarCollapsed,
    onToggleSidebar,
}) => {
    const theme = useTheme();

    // Resizable columns state
    const [sidebarWidth, setSidebarWidth] = useState(260);
    const [listWidth, setListWidth] = useState(450);
    const [isDraggingSidebar, setIsDraggingSidebar] = useState(false);
    const [isDraggingList, setIsDraggingList] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    // Resize handlers
    const handleSidebarResizeStart = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDraggingSidebar(true);
    }, []);

    const handleListResizeStart = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDraggingList(true);
    }, []);

    useEffect(() => {
        if (!isDraggingSidebar && !isDraggingList) return;

        let animationFrameId: number | null = null;
        let lastMouseX = 0;

        const handleMouseMove = (e: MouseEvent) => {
            lastMouseX = e.clientX;

            if (animationFrameId === null) {
                animationFrameId = requestAnimationFrame(() => {
                    const containerRect = containerRef.current?.getBoundingClientRect();
                    const containerLeft = containerRect?.left || 0;

                    if (isDraggingSidebar) {
                        const newWidth = lastMouseX - containerLeft;
                        if (newWidth >= 200 && newWidth <= 400) {
                            setSidebarWidth(newWidth);
                        }
                    }
                    if (isDraggingList) {
                        // Calculate width relative to sidebar
                        const newWidth = lastMouseX - containerLeft - sidebarWidth;
                        if (newWidth >= 350 && newWidth <= 800) {
                            setListWidth(newWidth);
                        }
                    }

                    animationFrameId = null;
                });
            }
        };

        const handleMouseUp = () => {
            if (animationFrameId !== null) {
                cancelAnimationFrame(animationFrameId);
            }
            setIsDraggingSidebar(false);
            setIsDraggingList(false);
        };

        document.addEventListener('mousemove', handleMouseMove, { passive: true });
        document.addEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';

        return () => {
            if (animationFrameId !== null) {
                cancelAnimationFrame(animationFrameId);
            }
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
    }, [isDraggingSidebar, isDraggingList, sidebarWidth]);

    // Determine layout styles
    const isVerticalLayout = layoutMode === 'vertical-split' || emailViewerPosition === 'below';

    return (
        <Box
            ref={containerRef}
            sx={{
                flex: 1,
                display: 'flex',
                overflow: 'hidden',
                minHeight: 0,
                backgroundColor: theme.palette.background.default,
                borderRadius: 3,
                flexDirection: isVerticalLayout ? 'column' : 'row',
                position: 'relative',
                boxShadow: theme.shadows[1],
                border: `1px solid ${theme.palette.divider}`,
                [theme.breakpoints.down('md')]: {
                    flexDirection: 'column',
                    borderRadius: 0,
                    border: 'none',
                }
            }}
        >
            {/* Sidebar (Folders) */}
            <Box
                sx={{
                    width: isSidebarCollapsed ? 0 : sidebarWidth,
                    flexShrink: 0,
                    overflow: 'hidden',
                    backgroundColor: alpha(theme.palette.background.paper, 0.8),
                    backdropFilter: 'blur(10px)',
                    borderRight: `1px solid ${alpha(theme.palette.divider, 0.6)}`,
                    transition: isDraggingSidebar ? 'none' : 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    display: 'flex',
                    flexDirection: 'column',
                    [theme.breakpoints.down('md')]: {
                        width: '100%',
                        height: 'auto',
                        maxHeight: '200px',
                        borderRight: 'none',
                        borderBottom: `1px solid ${theme.palette.divider}`,
                    }
                }}
            >
                {sidebar}
            </Box>

            {/* Sidebar Resize Handle */}
            {!isSidebarCollapsed && (
                <Box
                    onMouseDown={handleSidebarResizeStart}
                    sx={{
                        width: '1px',
                        cursor: 'col-resize',
                        backgroundColor: 'transparent',
                        position: 'relative',
                        '&::after': {
                            content: '""',
                            position: 'absolute',
                            top: 0,
                            bottom: 0,
                            left: -2,
                            width: 5,
                            zIndex: 10,
                        },
                        '&:hover': {
                            backgroundColor: theme.palette.primary.main,
                        },
                        transition: 'background-color 0.2s',
                        flexShrink: 0,
                        zIndex: 10,
                        [theme.breakpoints.down('md')]: {
                            display: 'none'
                        }
                    }}
                />
            )}

            {/* Main Content Area (List + Detail) */}
            <Box
                sx={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: isVerticalLayout ? 'column' : 'row',
                    overflow: 'hidden',
                    minWidth: 0, // Critical for flexbox text truncation
                    height: '100%',
                    [theme.breakpoints.down('md')]: {
                        flexDirection: 'column',
                    }
                }}
            >
                {/* Email List */}
                <Paper
                    elevation={0}
                    sx={{
                        width: isVerticalLayout ? '100%' : listWidth,
                        height: isVerticalLayout ? '40%' : '100%',
                        flexShrink: 0,
                        overflow: 'hidden',
                        display: 'flex',
                        flexDirection: 'column',
                        backgroundColor: theme.palette.background.paper,
                        borderRight: isVerticalLayout ? 'none' : `1px solid ${alpha(theme.palette.divider, 0.6)}`,
                        borderBottom: isVerticalLayout ? `1px solid ${alpha(theme.palette.divider, 0.6)}` : 'none',
                        transition: isDraggingList ? 'none' : 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                        [theme.breakpoints.down('md')]: {
                            width: '100%',
                            height: '300px',
                            borderRight: 'none',
                            borderBottom: `1px solid ${theme.palette.divider}`,
                        }
                    }}
                >
                    {emailList}
                </Paper>

                {/* List Resize Handle */}
                {!isVerticalLayout && (
                    <Box
                        onMouseDown={handleListResizeStart}
                        sx={{
                            width: '1px',
                            cursor: 'col-resize',
                            backgroundColor: 'transparent',
                            position: 'relative',
                            '&::after': {
                                content: '""',
                                position: 'absolute',
                                top: 0,
                                bottom: 0,
                                left: -2,
                                width: 5,
                                zIndex: 10,
                            },
                            '&:hover': {
                                backgroundColor: theme.palette.primary.main,
                            },
                            transition: 'background-color 0.2s',
                            flexShrink: 0,
                            zIndex: 10,
                            [theme.breakpoints.down('md')]: {
                                display: 'none'
                            }
                        }}
                    />
                )}

                {/* Email Detail */}
                <Box
                    sx={{
                        flex: 1,
                        overflow: 'hidden',
                        display: 'flex',
                        flexDirection: 'column',
                        minWidth: 0, // Critical for flexbox text truncation
                        height: '100%',
                        backgroundColor: alpha(theme.palette.background.default, 0.6),
                        [theme.breakpoints.down('md')]: {
                            flex: 1,
                            minHeight: '400px'
                        }
                    }}
                >
                    {emailDetail}
                </Box>
            </Box>
        </Box>
    );
};
