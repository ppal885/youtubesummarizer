import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AppConfigProvider } from './context/AppConfigContext'
import { AppProviders } from './providers/AppProviders'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AppProviders>
        <AppConfigProvider>
          <App />
        </AppConfigProvider>
      </AppProviders>
    </BrowserRouter>
  </StrictMode>,
)
