"use client";

import { useState } from 'react';

export default function ProlificIDInput({ onSubmit }) {
  const [prolificId, setProlificId] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(prolificId.trim() ? prolificId : 'XXX');
  };

  return (
    <form onSubmit={handleSubmit} className="form" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <label htmlFor="prolificId" className="form-label">
        Please enter your Prolific ID:
      </label>
      <div className="prolific-input-container">
        <input
          id="prolificId"
          type="text"
          value={prolificId}
          onChange={(e) => setProlificId(e.target.value)}
          className="input"
          required
          placeholder="e.g. 387d13f3eab7d9136c28b5c1"
        />
      </div>
      <button type="submit" className="button">
        Continue
      </button>
    </form>
  );
} 