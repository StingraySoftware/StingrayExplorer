import React from 'react';
import { Box, Typography, Paper, Chip, Alert } from '@mui/material';
import ConstructionIcon from '@mui/icons-material/Construction';

interface PageTemplateProps {
  title: string;
  description?: string;
  category?: string;
  status?: 'ready' | 'coming-soon' | 'in-development';
  children?: React.ReactNode;
}

/**
 * Reusable page template component
 */
const PageTemplate: React.FC<PageTemplateProps> = ({
  title,
  description,
  category,
  status = 'coming-soon',
  children,
}) => {
  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        {category && (
          <Chip
            label={category}
            size="small"
            color="primary"
            variant="outlined"
            sx={{ mb: 1 }}
          />
        )}
        <Typography variant="h4" gutterBottom>
          {title}
        </Typography>
        {description && (
          <Typography variant="body1" color="text.secondary">
            {description}
          </Typography>
        )}
      </Box>

      {/* Status indicator for pages under development */}
      {status !== 'ready' && (
        <Alert
          severity={status === 'in-development' ? 'warning' : 'info'}
          icon={<ConstructionIcon />}
          sx={{ mb: 3 }}
        >
          {status === 'in-development'
            ? 'This feature is currently under development.'
            : 'This feature is coming soon in a future release.'}
        </Alert>
      )}

      {/* Page content */}
      {children || (
        <Paper variant="outlined" sx={{ p: 4, textAlign: 'center' }}>
          <ConstructionIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            {title}
          </Typography>
          <Typography variant="body2" color="text.disabled">
            This analysis module will be implemented soon.
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default PageTemplate;
