import React from 'react';
import { Box, Typography, Paper, Button, Grid, Card, CardContent } from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';

const DataIngestionPage: React.FC = () => {
  const handleOpenFile = async (): Promise<void> => {
    if (window.electronAPI) {
      const files = await window.electronAPI.openFile({
        title: 'Select Data Files',
        filters: [
          { name: 'FITS Files', extensions: ['fits', 'fit', 'fts'] },
          { name: 'HDF5 Files', extensions: ['hdf5', 'h5'] },
          { name: 'Text Files', extensions: ['txt', 'csv', 'dat'] },
          { name: 'All Files', extensions: ['*'] },
        ],
        multiple: true,
      });
      if (files) {
        console.log('Selected files:', files);
        // TODO: Process files
      }
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Data Ingestion
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Load your X-ray astronomy data files for analysis
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent sx={{ textAlign: 'center', py: 4 }}>
              <UploadFileIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Local Files
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Load FITS, HDF5, or text files from your computer
              </Typography>
              <Button variant="contained" startIcon={<FolderOpenIcon />} onClick={handleOpenFile}>
                Browse Files
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent sx={{ textAlign: 'center', py: 4 }}>
              <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                From URL
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Fetch data directly from a remote URL
              </Typography>
              <Button variant="outlined" disabled>
                Coming Soon
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent sx={{ textAlign: 'center', py: 4 }}>
              <FolderOpenIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Sample Data
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Load example datasets for testing
              </Typography>
              <Button variant="outlined" disabled>
                Coming Soon
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper variant="outlined" sx={{ mt: 4, p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Loaded Data
        </Typography>
        <Typography variant="body2" color="text.secondary">
          No data files loaded yet. Use the options above to load your data.
        </Typography>
      </Paper>
    </Box>
  );
};

export default DataIngestionPage;
