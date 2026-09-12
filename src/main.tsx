import '@fontsource/inter/latin-400.css';
import '@fontsource/inter/latin-500.css';
import '@fontsource/inter/latin-600.css';
import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './FundingApp';
import './funding.css';
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
