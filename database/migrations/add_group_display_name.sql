-- Add display_name column to groups table
ALTER TABLE groups ADD COLUMN IF NOT EXISTS display_name VARCHAR(100);

-- Set display_name to be same as name for existing groups
UPDATE groups SET display_name = name WHERE display_name IS NULL;

-- Add updated_at column to groups table
ALTER TABLE groups ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_groups_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop trigger if exists and create new one
DROP TRIGGER IF EXISTS update_groups_updated_at ON groups;
CREATE TRIGGER update_groups_updated_at 
BEFORE UPDATE ON groups 
FOR EACH ROW 
EXECUTE FUNCTION update_groups_updated_at_column();