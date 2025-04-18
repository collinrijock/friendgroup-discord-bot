CREATE TABLE IF NOT EXISTS `warns` (
  `id` int(11) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Rename table and columns for monthly tracking
DROP TABLE IF EXISTS `voice_activity`; -- Drop old table if exists (or use ALTER TABLE if data needs preserving, but this is simpler for schema change)
CREATE TABLE IF NOT EXISTS `voice_activity_monthly` (
  `user_id` varchar(20) NOT NULL,
  `month_year` varchar(7) NOT NULL, -- Format: YYYY-MM (e.g., 2024-04)
  `monthly_minutes` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `month_year`) -- Composite primary key
);

-- Add new table for tracking total voice activity minutes
CREATE TABLE IF NOT EXISTS `voice_activity_total` (
  `user_id` varchar(20) PRIMARY KEY NOT NULL,
  `total_minutes` int(11) NOT NULL DEFAULT 0
);