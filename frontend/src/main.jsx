import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from '@clerk/clerk-react'
import App from './App.jsx'

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!PUBLISHABLE_KEY) {
  console.warn("Missing Publishable Key: Add VITE_CLERK_PUBLISHABLE_KEY to your .env file")
}

createRoot(document.getElementById('root')).render(
    <StrictMode>
        {PUBLISHABLE_KEY ? (
            <ClerkProvider publishableKey={PUBLISHABLE_KEY} afterSignOutUrl="/">
                <App />
            </ClerkProvider>
        ) : (
            <div style={{ color: 'white', padding: '2rem', textAlign: 'center' }}>
                <h2>Authentication Error</h2>
                <p>Missing Clerk Publishable Key. Please add VITE_CLERK_PUBLISHABLE_KEY to your frontend .env file.</p>
            </div>
        )}
    </StrictMode>,
)
