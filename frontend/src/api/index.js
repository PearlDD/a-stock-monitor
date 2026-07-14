import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// Watchlist
export const getWatchlist = () => api.get('/watchlist')
export const addToWatchlist = (stock) => api.post('/watchlist', stock)
export const removeFromWatchlist = (code) => api.delete(`/watchlist/${code}`)

// Quotes
export const getQuotes = (codes) => api.get('/stocks/quotes', { params: { codes: codes.join(',') } })

// Stock detail
export const getStockInfo = (code) => api.get(`/stocks/${code}/info`)
export const getStockNews = (code, limit = 10) => api.get(`/stocks/${code}/news`, { params: { limit } })

// Alerts
export const getAlerts = () => api.get('/alerts')
export const createAlert = (rule) => api.post('/alerts', rule)
export const updateAlert = (id, data) => api.put(`/alerts/${id}`, data)
export const deleteAlert = (id) => api.delete(`/alerts/${id}`)

// Search
export const searchStocks = (q) => api.get('/search', { params: { q } })

// Settings
export const getSettings = () => api.get('/settings')
export const updateSettings = (data) => api.post('/settings', data)
export const testPush = () => api.post('/test-push')
export const getPushQuota = () => api.get('/push-quota')

export default api
