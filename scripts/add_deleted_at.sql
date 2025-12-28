-- Add deleted_at column to business_data table
ALTER TABLE business_data ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

-- Add index for efficient soft delete queries
CREATE INDEX IF NOT EXISTS idx_business_data_deleted_at ON business_data(deleted_at);

