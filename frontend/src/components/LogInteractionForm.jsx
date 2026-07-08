// src/components/LogInteractionForm.jsx
// LEFT PANEL — "Log HCP Interaction" form with all required fields
import React, { useState, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import Select from 'react-select';
import {
  updateFormField,
  appendFollowUpToField,
  addMaterial,
  removeMaterial,
  addSample,
  removeSample,
  resetForm,
  submitInteraction,
  selectForm,
  selectSubmitStatus,
  selectFollowUpSuggestions,
} from '../features/interaction/interactionSlice';
import { searchHCPs } from '../services/api';

// ── Add Material Modal ────────────────────────────────────────────────────────
function AddMaterialModal({ onAdd, onClose }) {
  const [name, setName] = useState('');
  const [type, setType] = useState('Clinical Brochure');

  const materialTypes = [
    'Clinical Brochure', 'Journal Reprint', 'Clinical Summary',
    'Regulatory Document', 'Patient Education Material', 'Reference Card',
    'Health Economics Dossier', 'Conference Abstract', 'Monograph', 'Other',
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-title">Add Material</div>
        <div className="form-section">
          <label className="form-label">Material Name</label>
          <input
            className="form-input"
            placeholder="e.g. OncoBoost Phase III Clinical Summary"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
        </div>
        <div className="form-section">
          <label className="form-label">Type</label>
          <select
            className="form-select"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            {materialTypes.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className="btn btn-primary"
            disabled={!name.trim()}
            onClick={() => { if (name.trim()) { onAdd({ name: name.trim(), type }); onClose(); } }}
          >
            Add Material
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Add Sample Modal ──────────────────────────────────────────────────────────
function AddSampleModal({ onAdd, onClose }) {
  const [drug, setDrug] = useState('');
  const [quantity, setQuantity] = useState('');
  const [lotNumber, setLotNumber] = useState('');
  const [expiry, setExpiry] = useState('');

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-title">Distribute Sample</div>
        <div className="form-section">
          <label className="form-label">Drug / Product Name</label>
          <input
            className="form-input"
            placeholder="e.g. OncoBoost 150mg"
            value={drug}
            onChange={(e) => setDrug(e.target.value)}
            autoFocus
          />
        </div>
        <div className="form-row">
          <div>
            <label className="form-label">Quantity</label>
            <input
              className="form-input"
              type="number"
              min="1"
              placeholder="e.g. 10"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </div>
          <div>
            <label className="form-label">Expiry (MM/YYYY)</label>
            <input
              className="form-input"
              placeholder="e.g. 2027-03"
              value={expiry}
              onChange={(e) => setExpiry(e.target.value)}
            />
          </div>
        </div>
        <div className="form-section">
          <label className="form-label">Lot Number (optional)</label>
          <input
            className="form-input"
            placeholder="e.g. OB-2026-0412"
            value={lotNumber}
            onChange={(e) => setLotNumber(e.target.value)}
          />
        </div>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className="btn btn-primary"
            disabled={!drug.trim()}
            onClick={() => {
              if (drug.trim()) {
                onAdd({
                  drug: drug.trim(),
                  quantity: quantity ? parseInt(quantity, 10) : null,
                  lot_number: lotNumber || null,
                  expiry: expiry || null,
                });
                onClose();
              }
            }}
          >
            Add Sample
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Form Component ───────────────────────────────────────────────────────
export default function LogInteractionForm() {
  const dispatch = useDispatch();
  const form = useSelector(selectForm);
  const submitStatus = useSelector(selectSubmitStatus);
  const followUpSuggestions = useSelector(selectFollowUpSuggestions);

  const [hcpOptions, setHcpOptions] = useState([]);
  const [hcpSearchLoading, setHcpSearchLoading] = useState(false);
  const [showMaterialModal, setShowMaterialModal] = useState(false);
  const [showSampleModal, setShowSampleModal] = useState(false);
  const [toast, setToast] = useState(null);

  // ── Toast helper ────────────────────────────────────────────────────────────
  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  // ── HCP search for react-select ─────────────────────────────────────────────
  const handleHcpInputChange = useCallback(async (inputValue) => {
    if (!inputValue || inputValue.length < 2) return;
    setHcpSearchLoading(true);
    try {
      const res = await searchHCPs(inputValue);
      const opts = res.data.map((h) => ({
        value: h.id,
        label: h.name,
        specialty: h.specialty,
        hospital: h.hospital,
      }));
      setHcpOptions(opts);
    } catch {
      setHcpOptions([]);
    } finally {
      setHcpSearchLoading(false);
    }
  }, []);

  const handleHcpSelect = (selected) => {
    dispatch(updateFormField({ field: 'hcp_id', value: selected ? selected.value : null }));
    dispatch(updateFormField({ field: 'hcp_name', value: selected ? selected.label : '' }));
  };

  // ── Form submit ─────────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.hcp_id) {
      showToast('Please select an HCP.', 'error');
      return;
    }
    const payload = {
      hcp_id: form.hcp_id,
      interaction_type: form.interaction_type,
      date: form.date || null,
      time: form.time || null,
      attendees: form.attendees || null,
      topics_discussed: form.topics_discussed || null,
      materials_shared: form.materials_shared || [],
      samples_distributed: form.samples_distributed || [],
      sentiment: form.sentiment || 'neutral',
      outcomes: form.outcomes || null,
      follow_up_actions: form.follow_up_actions || null,
    };
    const result = await dispatch(submitInteraction(payload));
    if (submitInteraction.fulfilled.match(result)) {
      showToast(`✓ Interaction saved (ID: ${result.payload.id})`);
    } else {
      showToast('Failed to save interaction. Check console.', 'error');
    }
  };

  // ── Custom HCP option format ────────────────────────────────────────────────
  const formatHcpOption = (option) => (
    <div>
      <div className="hcp-option-label">{option.label}</div>
      {(option.specialty || option.hospital) && (
        <div className="hcp-option-meta">
          {[option.specialty, option.hospital].filter(Boolean).join(' · ')}
        </div>
      )}
    </div>
  );

  const isSubmitting = submitStatus === 'loading';

  return (
    <div className="panel-card" style={{ minHeight: '80vh' }}>
      {/* Panel header */}
      <div className="panel-header">
        <div className="panel-header-title">Log HCP Interaction</div>
        <div className="panel-header-name">Interaction Details</div>
        <div className="panel-header-desc">
          Complete the form below or use the AI Chat panel →
        </div>
      </div>

      <div className="panel-body">
        <form onSubmit={handleSubmit} id="log-interaction-form">

          {/* HCP Name — searchable dropdown */}
          <div className="form-section">
            <label className="form-label">
              HCP Name <span className="required">*</span>
            </label>
            <div className="hcp-select-wrapper">
              <Select
                classNamePrefix="react-select"
                inputId="hcp-select"
                placeholder="Search or select HCP..."
                options={hcpOptions}
                isLoading={hcpSearchLoading}
                onInputChange={(val) => { handleHcpInputChange(val); }}
                onChange={handleHcpSelect}
                formatOptionLabel={formatHcpOption}
                isClearable
                noOptionsMessage={({ inputValue }) =>
                  inputValue.length < 2
                    ? 'Type at least 2 characters to search...'
                    : 'No HCPs found'
                }
                value={
                  form.hcp_id
                    ? { value: form.hcp_id, label: form.hcp_name }
                    : null
                }
              />
            </div>
          </div>

          {/* Interaction Type */}
          <div className="form-section">
            <label className="form-label" htmlFor="interaction-type">Interaction Type</label>
            <select
              id="interaction-type"
              className="form-select"
              value={form.interaction_type}
              onChange={(e) =>
                dispatch(updateFormField({ field: 'interaction_type', value: e.target.value }))
              }
            >
              {['Meeting', 'Call', 'Email', 'Conference'].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {/* Date & Time */}
          <div className="form-row form-section">
            <div>
              <label className="form-label" htmlFor="interaction-date">Date</label>
              <input
                id="interaction-date"
                type="date"
                className="form-input"
                value={form.date}
                onChange={(e) =>
                  dispatch(updateFormField({ field: 'date', value: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="form-label" htmlFor="interaction-time">Time</label>
              <input
                id="interaction-time"
                type="time"
                className="form-input"
                value={form.time}
                onChange={(e) =>
                  dispatch(updateFormField({ field: 'time', value: e.target.value }))
                }
              />
            </div>
          </div>

          {/* Attendees */}
          <div className="form-section">
            <label className="form-label" htmlFor="attendees">Attendees</label>
            <input
              id="attendees"
              className="form-input"
              placeholder="Enter names or search..."
              value={form.attendees}
              onChange={(e) =>
                dispatch(updateFormField({ field: 'attendees', value: e.target.value }))
              }
            />
          </div>

          {/* Topics Discussed */}
          <div className="form-section">
            <label className="form-label" htmlFor="topics">Topics Discussed</label>
            <textarea
              id="topics"
              className="form-textarea"
              rows={4}
              placeholder="Enter key discussion points..."
              value={form.topics_discussed}
              onChange={(e) =>
                dispatch(updateFormField({ field: 'topics_discussed', value: e.target.value }))
              }
            />
            <button
              type="button"
              className="btn btn-secondary btn-sm mt-2"
              style={{ width: '100%', marginTop: '8px', fontSize: '12px' }}
            >
              🎤 Summarize from Voice Note (Requires Consent)
            </button>
          </div>

          {/* Materials Shared */}
          <div className="form-section">
            <div className="sub-section">
              <div className="sub-section-header">
                <span className="sub-section-title">Materials Shared</span>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setShowMaterialModal(true)}
                  id="add-material-btn"
                >
                  + Search/Add
                </button>
              </div>
              <div className="sub-section-body">
                {form.materials_shared.length === 0 ? (
                  <div className="empty-state">No materials added</div>
                ) : (
                  <div className="item-list">
                    {form.materials_shared.map((m, i) => (
                      <div className="item-card" key={i}>
                        <div className="item-card-info">
                          <div className="item-card-name">{m.name}</div>
                          <div className="item-card-meta">{m.type}</div>
                        </div>
                        <button
                          type="button"
                          className="btn btn-danger btn-sm btn-icon"
                          onClick={() => dispatch(removeMaterial(i))}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Samples Distributed */}
            <div className="sub-section">
              <div className="sub-section-header">
                <span className="sub-section-title">Samples Distributed</span>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setShowSampleModal(true)}
                  id="add-sample-btn"
                >
                  + Add Sample
                </button>
              </div>
              <div className="sub-section-body">
                {form.samples_distributed.length === 0 ? (
                  <div className="empty-state">No samples added</div>
                ) : (
                  <div className="item-list">
                    {form.samples_distributed.map((s, i) => (
                      <div className="item-card" key={i}>
                        <div className="item-card-info">
                          <div className="item-card-name">{s.drug}</div>
                          <div className="item-card-meta">
                            Qty: {s.quantity || '—'}
                            {s.lot_number && ` · Lot: ${s.lot_number}`}
                            {s.expiry && ` · Exp: ${s.expiry}`}
                          </div>
                        </div>
                        <button
                          type="button"
                          className="btn btn-danger btn-sm btn-icon"
                          onClick={() => dispatch(removeSample(i))}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sentiment */}
          <div className="form-section">
            <label className="form-label">Observed / Inferred HCP Sentiment</label>
            <div className="sentiment-group">
              {[
                { value: 'positive', emoji: '😊', label: 'Positive' },
                { value: 'neutral',  emoji: '😐', label: 'Neutral' },
                { value: 'negative', emoji: '😟', label: 'Negative' },
              ].map(({ value, emoji, label }) => (
                <div className="sentiment-option" key={value}>
                  <input
                    type="radio"
                    id={`sentiment-${value}`}
                    name="sentiment"
                    value={value}
                    checked={form.sentiment === value}
                    onChange={() =>
                      dispatch(updateFormField({ field: 'sentiment', value }))
                    }
                  />
                  <label className={value} htmlFor={`sentiment-${value}`}>
                    {emoji} {label}
                  </label>
                </div>
              ))}
            </div>
          </div>

          {/* Outcomes */}
          <div className="form-section">
            <label className="form-label" htmlFor="outcomes">Outcomes</label>
            <textarea
              id="outcomes"
              className="form-textarea"
              rows={3}
              placeholder="Key outcomes or agreements..."
              value={form.outcomes}
              onChange={(e) =>
                dispatch(updateFormField({ field: 'outcomes', value: e.target.value }))
              }
            />
          </div>

          {/* Follow-up Actions */}
          <div className="form-section">
            <label className="form-label" htmlFor="follow-up-actions">Follow-up Actions</label>
            <textarea
              id="follow-up-actions"
              className="form-textarea"
              rows={3}
              placeholder="Enter next steps or tasks..."
              value={form.follow_up_actions}
              onChange={(e) =>
                dispatch(updateFormField({ field: 'follow_up_actions', value: e.target.value }))
              }
            />
          </div>

          {/* AI Suggested Follow-ups */}
          {followUpSuggestions.length > 0 && (
            <div className="form-section">
              <div className="ai-section-header">
                <label className="form-label" style={{ margin: 0 }}>
                  AI Suggested Follow-ups
                </label>
                <span className="ai-badge">✦ AI</span>
              </div>
              <div className="suggestion-chips">
                {followUpSuggestions.map((suggestion, i) => (
                  <button
                    key={i}
                    type="button"
                    className="suggestion-chip"
                    id={`suggestion-chip-${i}`}
                    onClick={() => dispatch(appendFollowUpToField(suggestion))}
                    title="Click to add to Follow-up Actions"
                  >
                    <span className="suggestion-chip-icon">+</span>
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Static demo chips when no AI chips exist */}
          {followUpSuggestions.length === 0 && (
            <div className="form-section">
              <div className="ai-section-header">
                <label className="form-label" style={{ margin: 0 }}>
                  AI Suggested Follow-ups
                </label>
                <span className="ai-badge">✦ AI</span>
              </div>
              <div className="suggestion-chips">
                {[
                  '+ Schedule follow-up meeting in 2 weeks',
                  '+ Send OncoBoost Phase III PDF',
                  '+ Add Dr. Sharma to advisory board invite list',
                ].map((s, i) => (
                  <button
                    key={i}
                    type="button"
                    className="suggestion-chip"
                    id={`default-chip-${i}`}
                    onClick={() =>
                      dispatch(appendFollowUpToField(s.replace(/^\+\s*/, '')))
                    }
                  >
                    <span className="suggestion-chip-icon">+</span>
                    {s.replace(/^\+\s*/, '')}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Form actions */}
          <div className="flex gap-2 mt-3" style={{ paddingTop: '8px', borderTop: '1px solid var(--color-border)' }}>
            <button
              type="submit"
              className="btn btn-primary btn-lg"
              style={{ flex: 1 }}
              disabled={isSubmitting || !form.hcp_id}
              id="submit-interaction-btn"
            >
              {isSubmitting ? (
                <>
                  <span className="spinner" />
                  Saving...
                </>
              ) : (
                '💾 Save Interaction'
              )}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-lg"
              onClick={() => dispatch(resetForm())}
              disabled={isSubmitting}
              id="reset-form-btn"
            >
              Reset
            </button>
          </div>

        </form>
      </div>

      {/* Modals */}
      {showMaterialModal && (
        <AddMaterialModal
          onAdd={(m) => dispatch(addMaterial(m))}
          onClose={() => setShowMaterialModal(false)}
        />
      )}
      {showSampleModal && (
        <AddSampleModal
          onAdd={(s) => dispatch(addSample(s))}
          onClose={() => setShowSampleModal(false)}
        />
      )}

      {/* Toast */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.type === 'success' ? '✓' : '✕'} {toast.msg}
        </div>
      )}
    </div>
  );
}
