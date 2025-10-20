import React from 'react';
import { Box } from '@mui/material';
import { EmailAssistantComponent } from '../components/EmailAssistant/EmailAssistantComponent';

/**
 * Email Assistant Page
 *
 * This is a wrapper component that renders the Email Assistant V2 interface.
 *
 * V2 Features:
 * - Modern 4-tab design (Overview, Inbox & Tasks, Assistant, Settings)
 * - Unified email + task workflow
 * - Real-time streaming chat with SSE
 * - Semantic search integration
 * - Embedding management
 * - Smart dashboard with metrics & insights
 * - Context-aware assistant
 * - 85% backend feature coverage
 *
 * Note: The old V1 implementation (7-tab design) has been backed up to
 * EmailAssistant.v1.backup.tsx and can be restored via git if needed.
 */
const EmailAssistant: React.FC = () => {
  return (
    <Box
      sx={{
        // Fill the available height in the Layout's content area
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <EmailAssistantComponent />
    </Box>
  );
};

export default EmailAssistant;
