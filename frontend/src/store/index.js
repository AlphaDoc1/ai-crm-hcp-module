// src/store/index.js
import { configureStore } from '@reduxjs/toolkit';
import interactionReducer from '../features/interaction/interactionSlice';
import chatReducer from '../features/chat/chatSlice';

const store = configureStore({
  reducer: {
    interaction: interactionReducer,
    chat: chatReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Date objects in form state are fine — ignore serialization warnings
        ignoredPaths: ['interaction.form.date', 'interaction.form.time'],
      },
    }),
});

export default store;
