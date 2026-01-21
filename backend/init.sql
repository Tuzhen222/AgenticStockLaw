-- =============================================
-- SEED DATA - Agentic Stock Law
-- =============================================
-- Demo user credentials:
--   Username: user001
--   Password: user123456
--
--   Username: admin
--   Password: admin123456
-- =============================================

-- Insert default roles
INSERT INTO roles (id, name, description, created_at, updated_at) VALUES
(1, 'admin', 'Administrator with full access', NOW(), NOW()),
(2, 'user', 'Regular user', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Insert demo users
-- Password hashed with bcrypt (compatible with bcrypt 4.0.x)
INSERT INTO users (id, email, username, hashed_password, full_name, is_active, role_id, created_at, updated_at) VALUES
(1, 'admin@example.com', 'admin', '$2b$12$eD5j.vag3enuU8Z75RnB..aKPjxN/exixJHhdLLRhRJo4YAqTF48S', 'Administrator', true, 1, NOW(), NOW()),
(2, 'user001@example.com', 'user001', '$2b$12$ICD1vo09wJlo1rYm60oqNeIWn2N0nbK1O4e.ixf5T5IZEB2nzmeum', 'Demo User', true, 2, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Reset sequences
SELECT setval('roles_id_seq', (SELECT MAX(id) FROM roles));
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
