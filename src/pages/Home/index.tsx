import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActionArea,
  Grid,
  Chip,
  Paper,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import BuildIcon from '@mui/icons-material/Build';
import ModelTrainingIcon from '@mui/icons-material/ModelTraining';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import ScienceIcon from '@mui/icons-material/Science';
import UploadFileIcon from '@mui/icons-material/UploadFile';

interface QuickAccessCard {
  title: string;
  description: string;
  icon: React.ReactNode;
  path: string;
  color: string;
}

/**
 * Home page with quick access cards and welcome message
 */
const HomePage: React.FC = () => {
  const navigate = useNavigate();

  const quickAccessCards: QuickAccessCard[] = [
    {
      title: 'Load Data',
      description: 'Import FITS, HDF5, or text files for analysis',
      icon: <UploadFileIcon sx={{ fontSize: 40 }} />,
      path: '/data-ingestion',
      color: '#1976d2',
    },
    {
      title: 'QuickLook Analysis',
      description: 'Power spectra, cross spectra, light curves, and more',
      icon: <AnalyticsIcon sx={{ fontSize: 40 }} />,
      path: '/quicklook/power-spectrum',
      color: '#5ead61',
    },
    {
      title: 'Pulsar Analysis',
      description: 'Period search, phase folding, and phaseograms',
      icon: <AccessTimeIcon sx={{ fontSize: 40 }} />,
      path: '/pulsar/search',
      color: '#9c27b0',
    },
    {
      title: 'Modeling',
      description: 'Model fitting with MLE and MCMC methods',
      icon: <ModelTrainingIcon sx={{ fontSize: 40 }} />,
      path: '/modeling/builder',
      color: '#ff9800',
    },
    {
      title: 'Simulator',
      description: 'Generate synthetic light curves and event lists',
      icon: <ScienceIcon sx={{ fontSize: 40 }} />,
      path: '/simulator',
      color: '#f44336',
    },
    {
      title: 'Utilities',
      description: 'GTI handling, statistics, and I/O tools',
      icon: <BuildIcon sx={{ fontSize: 40 }} />,
      path: '/utilities/gti',
      color: '#607d8b',
    },
  ];

  return (
    <Box>
      {/* Welcome section */}
      <Paper
        elevation={0}
        sx={{
          p: 4,
          mb: 4,
          background: 'linear-gradient(135deg, #5ead61 0%, #2e7d32 100%)',
          color: 'white',
          borderRadius: 2,
        }}
      >
        <Typography variant="h4" gutterBottom fontWeight="bold">
          Welcome to Stingray Explorer
        </Typography>
        <Typography variant="h6" sx={{ opacity: 0.9, mb: 2 }}>
          Next-Generation Spectral Timing Made Easy
        </Typography>
        <Typography variant="body1" sx={{ opacity: 0.85, maxWidth: 800 }}>
          A comprehensive data analysis and visualization dashboard for X-ray astronomy
          time series data. Built on top of the Stingray library, it provides an intuitive
          graphical interface for analyzing event lists, generating light curves, computing
          various types of spectra, and performing advanced timing analysis.
        </Typography>
        <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
          <Chip label="Stingray 2.0+" sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }} />
          <Chip label="X-ray Astronomy" sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }} />
          <Chip label="Time Series Analysis" sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }} />
        </Box>
      </Paper>

      {/* Quick Access Cards */}
      <Typography variant="h5" gutterBottom fontWeight="medium" sx={{ mb: 3 }}>
        Quick Access
      </Typography>
      <Grid container spacing={3}>
        {quickAccessCards.map((card) => (
          <Grid item xs={12} sm={6} md={4} key={card.title}>
            <Card
              elevation={0}
              sx={{
                height: '100%',
                border: '1px solid',
                borderColor: 'divider',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 4,
                  borderColor: card.color,
                },
              }}
            >
              <CardActionArea
                onClick={() => navigate(card.path)}
                sx={{ height: '100%', p: 2 }}
              >
                <CardContent>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 2,
                      mb: 2,
                    }}
                  >
                    <Box sx={{ color: card.color }}>{card.icon}</Box>
                    <Typography variant="h6" fontWeight="medium">
                      {card.title}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {card.description}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default HomePage;
