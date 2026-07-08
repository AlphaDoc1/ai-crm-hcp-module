// src/features/chat/chatSlice.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { sendChatMessage } from '../../services/api';
import { hydrateFormFromChat, setFollowUpSuggestions } from '../interaction/interactionSlice';

// ── Async thunk: send message through LangGraph agent ────────────────────────

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async ({ message, history }, { dispatch, rejectWithValue }) => {
    try {
      const res = await sendChatMessage(message, history);
      const data = res.data;

      // If the agent logged/summarized an interaction, hydrate the left panel form
      if (data.interaction_data) {
        dispatch(hydrateFormFromChat(data.interaction_data));
      }

      // If the agent generated follow-up suggestions, push them to chips
      if (data.suggestions && data.suggestions.length > 0) {
        dispatch(setFollowUpSuggestions(data.suggestions));
      }

      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message);
    }
  }
);

// ── Slice ─────────────────────────────────────────────────────────────────────

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    messages: [
      {
        id: 'welcome',
        role: 'assistant',
        content:
          "Hi! I'm your HCP Interaction AI Assistant. Log interaction details here (e.g., 'Met Dr. Sharma at Apollo, discussed OncoBoost Phase III efficacy, positive sentiment, shared clinical brochure') or ask for help with HCP search, follow-up suggestions, or editing an existing interaction.",
        timestamp: new Date().toISOString(),
      },
    ],
    status: 'idle',    // idle | loading | failed
    error: null,
    lastToolUsed: null,
  },
  reducers: {
    // Add a user message immediately (optimistic update)
    addUserMessage: (state, action) => {
      state.messages.push({
        id: `user-${Date.now()}`,
        role: 'user',
        content: action.payload,
        timestamp: new Date().toISOString(),
      });
    },

    clearChat: (state) => {
      state.messages = [state.messages[0]]; // keep welcome message
      state.error = null;
      state.lastToolUsed = null;
    },

    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.status = 'idle';
        const { reply, tool_used, tool_result } = action.payload;
        state.lastToolUsed = tool_used || null;

        // Add assistant reply to conversation
        state.messages.push({
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: reply,
          toolUsed: tool_used,
          toolResult: tool_result,
          timestamp: new Date().toISOString(),
        });
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.status = 'idle';
        state.error = action.payload || 'Failed to reach the AI agent.';
        state.messages.push({
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `Sorry, I encountered an error: ${action.payload || 'Unknown error'}. Please try again.`,
          isError: true,
          timestamp: new Date().toISOString(),
        });
      });
  },
});

export const { addUserMessage, clearChat, clearError } = chatSlice.actions;
export default chatSlice.reducer;

// ── Selectors ──────────────────────────────────────────────────────────────────
export const selectMessages = (state) => state.chat.messages;
export const selectChatStatus = (state) => state.chat.status;
export const selectLastToolUsed = (state) => state.chat.lastToolUsed;
