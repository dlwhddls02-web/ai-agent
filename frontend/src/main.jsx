import React from 'react'
import ReactDOM from 'react-dom/client'
import axios from 'axios'
import App from './App.jsx'
import './index.css'

// VITE_API_URL이 설정된 경우 해당 URL을, 미설정 시 vite proxy(/api)를 사용
axios.defaults.baseURL = import.meta.env.VITE_API_URL || ''

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
