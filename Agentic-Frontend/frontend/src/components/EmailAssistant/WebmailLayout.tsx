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
    const [sidebarWidth, setSidebarWidth] = useState(250);
    const [listWidth, setListWidth] = useState(400);
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
                        if (newWidth >= 200 && newWidth <= 500) {
                            setSidebarWidth(newWidth);
                        }
                    }
                    if (isDraggingList) {
                        // Calculate width relative to sidebar
                        const newWidth = lastMouseX - containerLeft - sidebarWidth - 4; // 4px for handle
                        if (newWidth >= 300 && newWidth <= 800) {
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
                backgroundColor: theme.palette.background.paper,
                borderRadius: '0 0 8px 8px',
                flexDirection: isVerticalLayout ? 'column' : 'row',
                position: 'relative',
                [theme.breakpoints.down('md')]: {
                    flexDirection: 'column',
                }
            }}
        >
            {/* Sidebar (Folders) */}
            <Box
                sx={{
                    width: isSidebarCollapsed ? 0 : sidebarWidth,
                    flexShrink: 0,
                    overflow: 'hidden',
                    backgroundColor: theme.palette.background.paper,
                    borderRight: `1px solid ${theme.palette.divider}`,
                    transition: isDraggingSidebar ? 'none' : 'width 0.2s ease',
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
                        width: 4,
                        cursor: 'col-resize',
                        backgroundColor: 'transparent',
                        '&:hover': {
                            backgroundColor: theme.palette.primary.main,
                            opacity: 0.5
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
                    minWidth: 0,
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
                        borderRight: isVerticalLayout ? 'none' : `1px solid ${theme.palette.divider}`,
                        borderBottom: isVerticalLayout ? `1px solid ${theme.palette.divider}` : 'none',
                        transition: isDraggingList ? 'none' : 'all 0.2s ease',
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
                            width: 4,
                            cursor: 'col-resize',
                            backgroundColor: 'transparent',
                            '&:hover': {
                                backgroundColor: theme.palette.primary.main,
                                opacity: 0.5
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
                        minWidth: 0,
                        backgroundColor: alpha(theme.palette.background.default, 0.3),
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
