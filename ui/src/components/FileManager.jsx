import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Box, Button, Typography, Alert, CircularProgress } from '@mui/material';
import axios from 'axios';

const FileManager = () => {
  const queryClient = useQueryClient();
  const token = localStorage.getItem('token');

  const uploadMutation = useMutation({
    mutationFn: async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      return axios.post('http://localhost:8000/api/v1/files/', formData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['files']);
    },
  });

  const onDrop = useCallback((acceptedFiles) => {
    acceptedFiles.forEach((file) => {
      uploadMutation.mutate(file);
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/*': ['.pdf', '.docx'], 'image/*': [] },
    maxSize: 100 * 1024 * 1024, // 100MB
  });

  return (
    <Box sx={{ p: 4, maxWidth: 600, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom>📁 File Manager</Typography>
      
      <Box
        {...getRootProps()}
        sx={{
          border: '2px dashed #ccc',
          borderRadius: 2,
          p: 4,
          textAlign: 'center',
          bgcolor: isDragActive ? '#f0f8ff' : 'grey.50',
          cursor: 'pointer',
        }}
      >
        <input {...getInputProps()} />
        <Typography variant="h6">
          {isDragActive ? 'Drop files here...' : 'Drag & drop files or click to select'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Up to 100MB - PDF, Images, Documents supported
        </Typography>
      </Box>

      {uploadMutation.isPending && <CircularProgress sx={{ mt: 2, display: 'block', mx: 'auto' }} />}
      {uploadMutation.isError && (
        <Alert severity="error" sx={{ mt: 2 }}>
          Upload failed: {uploadMutation.error.response?.data?.detail}
        </Alert>
      )}
    </Box>
  );
};

export default FileManager;
