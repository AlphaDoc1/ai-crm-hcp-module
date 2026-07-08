// src/services/api.js
// Axios client wired to the FastAPI backend
import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
  timeout: 60000,          // 60s — LLM calls can take time
  headers: { 'Content-Type': 'application/json' },
});

// ── HCP endpoints ──────────────────────────────────────────────────────────

export const searchHCPs = (query) =>
  API.get(`/api/hcps/search?q=${encodeURIComponent(query)}`);

export const listHCPs = () => API.get('/api/hcps');

// ── Interaction endpoints ──────────────────────────────────────────────────

export const createInteraction = (data) => API.post('/api/interactions', data);

export const listInteractions = (params = {}) =>
  API.get('/api/interactions', { params });

export const getInteraction = (id) => API.get(`/api/interactions/${id}`);

export const updateInteraction = (id, data) =>
  API.put(`/api/interactions/${id}`, data);

// ── Follow-up endpoints ────────────────────────────────────────────────────

export const getFollowUps = (interactionId) =>
  API.get(`/api/interactions/${interactionId}/follow-ups`);

export const updateFollowUpStatus = (followUpId, status) =>
  API.patch(`/api/follow-ups/${followUpId}/status`, { status });

// ── Chat endpoint ──────────────────────────────────────────────────────────

export const sendChatMessage = (message, conversationHistory = []) =>
  API.post('/api/chat', { message, conversation_history: conversationHistory });

export default API;
