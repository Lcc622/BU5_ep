import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import App from './App';
import { queryClient } from './lib/queryClient';
import './index.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
 <React.StrictMode>
 <QueryClientProvider client={queryClient}>
 <App />
 <Toaster
 position="top-right"
 toastOptions={{
  duration: 3500,
  style: {
  border: '1px solid #d7e0e8',
  borderRadius: '16px',
  background: '#f8fafc',
  color: '#16212f',
  },
 }}
 />
 </QueryClientProvider>
 </React.StrictMode>
);
