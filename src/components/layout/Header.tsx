import React, { useContext, useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Tooltip,
  Chip,
  InputBase,
  Paper,
  Fade,
  ClickAwayListener,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import MenuOpenIcon from '@mui/icons-material/MenuOpen';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import RefreshIcon from '@mui/icons-material/Refresh';
import SettingsIcon from '@mui/icons-material/Settings';
import SearchIcon from '@mui/icons-material/Search';
import CloseIcon from '@mui/icons-material/Close';
import CircleIcon from '@mui/icons-material/Circle';
import ViewSidebarIcon from '@mui/icons-material/ViewSidebar';
import { ThemeContext, useBackendContext } from '../../App';
import { useUIStore } from '@/store/uiStore';

interface HeaderProps {
  onToggleSidebar: () => void;
  sidebarOpen: boolean;
  onToggleRightToolbar: () => void;
  rightToolbarOpen: boolean;
}

/**
 * Application header with navigation controls and status indicators
 */
const Header: React.FC<HeaderProps> = ({
  onToggleSidebar,
  sidebarOpen,
  onToggleRightToolbar,
  rightToolbarOpen,
}) => {
  const { darkMode, toggleDarkMode } = useContext(ThemeContext);
  const { isReady, error } = useBackendContext();
  const { searchOpen, searchQuery, setSearchOpen, setSearchQuery } = useUIStore();

  const [localSearchQuery, setLocalSearchQuery] = useState('');

  const handleRestartBackend = async (): Promise<void> => {
    if (window.electronAPI) {
      await window.electronAPI.restartPython();
    }
  };

  const handleSearchOpen = (): void => {
    setSearchOpen(true);
    setLocalSearchQuery(searchQuery);
  };

  const handleSearchClose = (): void => {
    setSearchOpen(false);
    setLocalSearchQuery('');
  };

  const handleSearchSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    setSearchQuery(localSearchQuery);
    // TODO: Implement actual search functionality
    console.log('Search query:', localSearchQuery);
  };

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        backgroundColor: 'background.paper',
        borderBottom: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Toolbar>
        {/* Left sidebar toggle */}
        <IconButton
          edge="start"
          color="inherit"
          aria-label="toggle sidebar"
          onClick={onToggleSidebar}
          sx={{ mr: 2, color: 'text.primary' }}
        >
          {sidebarOpen ? <MenuOpenIcon /> : <MenuIcon />}
        </IconButton>

        {/* Logo and title */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <img
            src="/assets/images/stingray_explorer.png"
            alt="Stingray Explorer"
            style={{ width: 32, height: 32 }}
          />
          <Typography
            variant="h6"
            noWrap
            component="div"
            sx={{
              color: 'text.primary',
              fontWeight: 600,
              letterSpacing: '-0.5px',
            }}
          >
            Stingray Explorer
          </Typography>
        </Box>

        {/* Subtitle */}
        <Typography
          variant="caption"
          sx={{
            ml: 2,
            color: 'text.secondary',
            display: { xs: 'none', md: 'block' },
          }}
        >
          Next-Generation Spectral Timing Made Easy
        </Typography>

        {/* Spacer */}
        <Box sx={{ flexGrow: 1 }} />

        {/* Search bar */}
        {searchOpen ? (
          <ClickAwayListener onClickAway={handleSearchClose}>
            <Fade in={searchOpen}>
              <Paper
                component="form"
                onSubmit={handleSearchSubmit}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  width: 300,
                  height: 36,
                  px: 1,
                  mr: 2,
                }}
                elevation={2}
              >
                <SearchIcon sx={{ color: 'text.secondary', mr: 1 }} />
                <InputBase
                  placeholder="Search pages, features..."
                  value={localSearchQuery}
                  onChange={(e) => setLocalSearchQuery(e.target.value)}
                  autoFocus
                  sx={{ flex: 1, fontSize: '0.875rem' }}
                />
                <IconButton size="small" onClick={handleSearchClose}>
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Paper>
            </Fade>
          </ClickAwayListener>
        ) : (
          <Tooltip title="Search (Ctrl+K)">
            <IconButton
              color="inherit"
              onClick={handleSearchOpen}
              sx={{ color: 'text.secondary', mr: 1 }}
            >
              <SearchIcon />
            </IconButton>
          </Tooltip>
        )}

        {/* Backend status indicator */}
        <Tooltip title={isReady ? 'Python backend running' : error || 'Backend not ready'}>
          <Chip
            icon={
              <CircleIcon
                sx={{
                  fontSize: 12,
                  color: isReady ? '#4caf50' : error ? '#f44336' : '#ff9800',
                }}
              />
            }
            label={isReady ? 'Backend Ready' : error ? 'Error' : 'Starting...'}
            size="small"
            variant="outlined"
            color={isReady ? 'success' : error ? 'error' : 'warning'}
            sx={{
              mr: 2,
            }}
          />
        </Tooltip>

        {/* Action buttons */}
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          {/* Restart backend */}
          <Tooltip title="Restart Python backend">
            <IconButton
              color="inherit"
              onClick={handleRestartBackend}
              sx={{ color: 'text.secondary' }}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>

          {/* Dark mode toggle */}
          <Tooltip title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}>
            <IconButton
              color="inherit"
              onClick={toggleDarkMode}
              sx={{ color: 'text.secondary' }}
            >
              {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
            </IconButton>
          </Tooltip>

          {/* Settings */}
          <Tooltip title="Settings">
            <IconButton color="inherit" sx={{ color: 'text.secondary' }}>
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Right toolbar toggle - rightmost */}
        <Tooltip title={rightToolbarOpen ? 'Hide toolbar' : 'Show toolbar'}>
          <IconButton
            edge="end"
            color="inherit"
            aria-label="toggle right toolbar"
            onClick={onToggleRightToolbar}
            sx={{
              ml: 2,
              color: rightToolbarOpen ? 'primary.main' : 'text.primary',
            }}
          >
            <ViewSidebarIcon sx={{ transform: 'scaleX(-1)' }} />
          </IconButton>
        </Tooltip>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
