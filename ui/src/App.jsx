import React, { useState } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { BrowserRouter as Router, Routes, Route, AppBar, Toolbar, Typography, Box } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import FileManager from './components/FileManager';
import PDFTools from './components/PDFTools';
import QRTools from './components/QRTools';
import ARMenu from './components/ARMenu';
import PhotoEditor from './components/PhotoEditor';
import Converter from './components/Converter';
import DataAnalysis from './components/DataAnalysis';
import Summarizer from './components/Summarizer';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

const theme = createTheme({
  palette: {
    primary: { main: '#1976d2' },
    secondary: { main: '#dc004e' },
    mode: 'dark',
  },
});

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <Router>
          <Box sx={{ flexGrow: 1 }}>
            <AppBar position="static">
              <Toolbar>
                <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                  🚀 AI Platform
                </Typography>
                {!token && <Login setToken={setToken} />}
              </Toolbar>
            </AppBar>
            {token && (
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/files" element={<FileManager />} />
                <Route path="/pdf" element={<PDFTools />} />
                <Route path="/qr" element={<QRTools />} />
                <Route path="/ar" element={<ARMenu />} />
                <Route path="/photo" element={<PhotoEditor />} />
                <Route path="/convert" element={<Converter />} />
                <Route path="/analysis" element={<DataAnalysis />} />
                <Route path="/summarize" element={<Summarizer />} />
              </Routes>
            )}
          </Box>
        </Router>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
