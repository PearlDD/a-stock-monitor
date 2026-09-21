import axios from 'axios'
import { supabase } from '../lib/supabase'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase?.auth.getSession() || { data: {} }
  if (session?.access_token) config.headers.Authorization = `Bearer ${session.access_token}`
  return config
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
export const getAlertNotifications = () => api.get('/alert-notifications')

// Search
export const searchStocks = (q) => api.get('/search', { params: { q } })

// Stock detail
export const getFinancials = (code) => api.get(`/stocks/${code}/financials`)
export const getPriceHistory = (code, days = 5) => api.get(`/stocks/${code}/history`, { params: { days } })
export const getAnnouncements = (code, limit = 10) => api.get(`/stocks/${code}/announcements`, { params: { limit } })

// Capital flow
export const getCapitalFlowTop = () => api.get('/capital-flow/top')

// Settings
export const getSettings = () => api.get('/settings')
export const updateSettings = (data) => api.post('/settings', data)
export const testPush = () => api.post('/test-push')
export const getPushQuota = () => api.get('/push-quota')

export default api
