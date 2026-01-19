-- Migration: Add greeting fields to prompts table
-- Date: 2025-01-19
-- Description: Adds greeting_text and greeting_duration_ms columns for per-prompt greetings

-- Add greeting_text column (nullable)
ALTER TABLE prompts
ADD COLUMN IF NOT EXISTS greeting_text TEXT;

-- Add greeting_duration_ms column (nullable)
ALTER TABLE prompts
ADD COLUMN IF NOT EXISTS greeting_duration_ms FLOAT;

-- Verification
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'prompts'
  AND column_name IN ('greeting_text', 'greeting_duration_ms');
