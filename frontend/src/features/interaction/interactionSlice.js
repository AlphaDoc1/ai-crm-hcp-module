// src/features/interaction/interactionSlice.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import {
  createInteraction,
  updateInteraction,
  listInteractions,
} from '../../services/api';

// ── Async thunks ─────────────────────────────────────────────────────────────

export const fetchInteractions = createAsyncThunk(
  'interaction/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      const res = await listInteractions();
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

export const submitInteraction = createAsyncThunk(
  'interaction/submit',
  async (formData, { rejectWithValue }) => {
    try {
      const res = await createInteraction(formData);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

export const editInteraction = createAsyncThunk(
  'interaction/edit',
  async ({ id, data }, { rejectWithValue }) => {
    try {
      const res = await updateInteraction(id, data);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

// ── Initial form state ────────────────────────────────────────────────────────

const initialForm = {
  hcp_id: null,
  hcp_name: '',
  interaction_type: 'Meeting',
  date: '',
  time: '',
  attendees: '',
  topics_discussed: '',
  materials_shared: [],
  samples_distributed: [],
  sentiment: 'neutral',
  outcomes: '',
  follow_up_actions: '',
};

// ── Slice ─────────────────────────────────────────────────────────────────────

const interactionSlice = createSlice({
  name: 'interaction',
  initialState: {
    form: initialForm,
    interactions: [],
    total: 0,
    currentInteraction: null,
    followUpSuggestions: [],
    status: 'idle',       // idle | loading | succeeded | failed
    submitStatus: 'idle',
    error: null,
    lastSavedId: null,
  },
  reducers: {
    // Update a single form field
    updateFormField: (state, action) => {
      const { field, value } = action.payload;
      state.form[field] = value;
    },

    // Hydrate the entire form from AI chat data
    hydrateFormFromChat: (state, action) => {
      const data = action.payload;
      if (!data) return;
      if (data.hcp_name) state.form.hcp_name = data.hcp_name;
      if (data.hcp_id) state.form.hcp_id = data.hcp_id;
      if (data.interaction_type) state.form.interaction_type = data.interaction_type;
      if (data.date) state.form.date = data.date;
      if (data.time) state.form.time = data.time;
      if (data.attendees) state.form.attendees = data.attendees;
      if (data.topics_discussed) state.form.topics_discussed = data.topics_discussed;
      if (data.materials_shared) state.form.materials_shared = data.materials_shared;
      if (data.samples_distributed) state.form.samples_distributed = data.samples_distributed;
      if (data.sentiment) state.form.sentiment = data.sentiment;
      if (data.outcomes) state.form.outcomes = data.outcomes;
      if (data.follow_up_actions) state.form.follow_up_actions = data.follow_up_actions;
    },

    // Append a follow-up suggestion chip text to the follow_up_actions field
    appendFollowUpToField: (state, action) => {
      const suggestion = action.payload;
      const existing = state.form.follow_up_actions || '';
      state.form.follow_up_actions = existing
        ? `${existing}\n• ${suggestion}`
        : `• ${suggestion}`;
    },

    // Set AI-suggested follow-up chips
    setFollowUpSuggestions: (state, action) => {
      state.followUpSuggestions = action.payload || [];
    },

    // Add a material to the materials_shared list
    addMaterial: (state, action) => {
      state.form.materials_shared.push(action.payload);
    },

    // Remove a material by index
    removeMaterial: (state, action) => {
      state.form.materials_shared.splice(action.payload, 1);
    },

    // Add a sample to the samples_distributed list
    addSample: (state, action) => {
      state.form.samples_distributed.push(action.payload);
    },

    // Remove a sample by index
    removeSample: (state, action) => {
      state.form.samples_distributed.splice(action.payload, 1);
    },

    // Reset form to initial state
    resetForm: (state) => {
      state.form = initialForm;
      state.followUpSuggestions = [];
      state.submitStatus = 'idle';
      state.lastSavedId = null;
    },

    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // fetchInteractions
      .addCase(fetchInteractions.pending, (state) => {
        state.status = 'loading';
      })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.interactions = action.payload.items || [];
        state.total = action.payload.total || 0;
      })
      .addCase(fetchInteractions.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload;
      })

      // submitInteraction
      .addCase(submitInteraction.pending, (state) => {
        state.submitStatus = 'loading';
      })
      .addCase(submitInteraction.fulfilled, (state, action) => {
        state.submitStatus = 'succeeded';
        state.lastSavedId = action.payload.id;
        state.currentInteraction = action.payload;
        // Add to interactions list
        state.interactions.unshift(action.payload);
        state.total += 1;
      })
      .addCase(submitInteraction.rejected, (state, action) => {
        state.submitStatus = 'failed';
        state.error = action.payload;
      })

      // editInteraction
      .addCase(editInteraction.fulfilled, (state, action) => {
        const updated = action.payload;
        const idx = state.interactions.findIndex((i) => i.id === updated.id);
        if (idx !== -1) state.interactions[idx] = updated;
        if (state.currentInteraction?.id === updated.id) {
          state.currentInteraction = updated;
        }
      });
  },
});

export const {
  updateFormField,
  hydrateFormFromChat,
  appendFollowUpToField,
  setFollowUpSuggestions,
  addMaterial,
  removeMaterial,
  addSample,
  removeSample,
  resetForm,
  clearError,
} = interactionSlice.actions;

export default interactionSlice.reducer;

// ── Selectors ─────────────────────────────────────────────────────────────────
export const selectForm = (state) => state.interaction.form;
export const selectSubmitStatus = (state) => state.interaction.submitStatus;
export const selectFollowUpSuggestions = (state) => state.interaction.followUpSuggestions;
export const selectLastSavedId = (state) => state.interaction.lastSavedId;
export const selectInteractions = (state) => state.interaction.interactions;
