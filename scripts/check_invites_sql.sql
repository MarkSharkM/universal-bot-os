-- Check invites for user with external_id = 380927579
-- Bot ID: 4f3c45a5-39ac-4d6e-a0eb-263765d70b1a

-- 1. Find user
SELECT 
    id,
    external_id,
    custom_data->>'username' as username,
    custom_data->>'total_invited' as total_invited,
    created_at,
    updated_at
FROM users
WHERE bot_id = '4f3c45a5-39ac-4d6e-a0eb-263765d70b1a'
  AND external_id = '380927579';

-- 2. Count all business_data logs for this inviter (including deleted)
SELECT 
    COUNT(*) as total_logs,
    COUNT(CASE WHEN deleted_at IS NULL THEN 1 END) as active_logs,
    COUNT(CASE WHEN deleted_at IS NOT NULL THEN 1 END) as deleted_logs
FROM business_data
WHERE bot_id = '4f3c45a5-39ac-4d6e-a0eb-263765d70b1a'
  AND data_type = 'log'
  AND (data->>'inviter_external_id') = '380927579';

-- 3. Count referral logs (is_referral = true, active only)
SELECT 
    COUNT(DISTINCT data->>'external_id') as unique_referrals,
    COUNT(*) as total_referral_logs
FROM business_data
WHERE bot_id = '4f3c45a5-39ac-4d6e-a0eb-263765d70b1a'
  AND data_type = 'log'
  AND deleted_at IS NULL
  AND (data->>'inviter_external_id') = '380927579'
  AND (
    (data->>'is_referral') IN ('true', 'True')
    OR (data->>'is_referral')::boolean = true
  )
  AND (data->>'external_id') IS NOT NULL
  AND (data->>'external_id') != '';

-- 4. Show all referral logs with details
SELECT 
    id,
    data->>'external_id' as referred_external_id,
    data->>'user_id' as referred_user_id,
    data->>'is_referral' as is_referral,
    data->>'click_type' as click_type,
    data->>'event_type' as event_type,
    created_at,
    deleted_at
FROM business_data
WHERE bot_id = '4f3c45a5-39ac-4d6e-a0eb-263765d70b1a'
  AND data_type = 'log'
  AND (data->>'inviter_external_id') = '380927579'
  AND (
    (data->>'is_referral') IN ('true', 'True')
    OR (data->>'is_referral')::boolean = true
  )
ORDER BY created_at DESC;

-- 5. Show unique external_ids that were referred
SELECT DISTINCT
    data->>'external_id' as referred_external_id,
    COUNT(*) as referral_count,
    MIN(created_at) as first_referral,
    MAX(created_at) as last_referral
FROM business_data
WHERE bot_id = '4f3c45a5-39ac-4d6e-a0eb-263765d70b1a'
  AND data_type = 'log'
  AND deleted_at IS NULL
  AND (data->>'inviter_external_id') = '380927579'
  AND (
    (data->>'is_referral') IN ('true', 'True')
    OR (data->>'is_referral')::boolean = true
  )
  AND (data->>'external_id') IS NOT NULL
  AND (data->>'external_id') != ''
GROUP BY data->>'external_id'
ORDER BY first_referral DESC;
