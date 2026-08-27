-- DNS Web Manager - Database Schema
-- PostgreSQL 15+

-- ===========================================
-- Tabela de Usuários
-- ===========================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    CONSTRAINT valid_role CHECK (role IN ('admin', 'operator', 'viewer'))
);

-- ===========================================
-- Tabela de Logs de Auditoria
-- ===========================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50),
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_name VARCHAR(255) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================
-- Tabela de Configurações
-- ===========================================
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- ===========================================
-- Tabela de Versões de Zonas
-- ===========================================
CREATE TABLE IF NOT EXISTS zone_versions (
    id SERIAL PRIMARY KEY,
    zone_name VARCHAR(255) NOT NULL,
    serial BIGINT NOT NULL,
    content TEXT NOT NULL,
    changed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    change_type VARCHAR(20) NOT NULL,
    change_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_change CHECK (change_type IN ('create', 'update', 'delete'))
);

-- ===========================================
-- Índices para Performance
-- ===========================================
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_logs(target_type, target_name);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_zone_versions_name ON zone_versions(zone_name);
CREATE INDEX IF NOT EXISTS idx_zone_versions_created ON zone_versions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(active);

-- ===========================================
-- Usuário Admin Padrão
-- Senha: admin (hash bcrypt)
-- ===========================================
INSERT INTO users (username, email, password_hash, role, active)
VALUES (
    'admin',
    'admin@localhost',
    '$2b$12$feThAa0I8/h5YPdBlxV1w.R0CFFPSlU2.Wtd5dxPGwnwegtfmsplS',
    'admin',
    TRUE
) ON CONFLICT (username) DO NOTHING;

-- ===========================================
-- Configurações Padrão
-- ===========================================
INSERT INTO settings (key, value, description) VALUES
    ('dns_default_ttl', '3600', 'TTL padrão para novos registros'),
    ('dns_default_refresh', '86400', 'Refresh padrão para SOA'),
    ('dns_default_retry', '7200', 'Retry padrão para SOA'),
    ('dns_default_expire', '3600000', 'Expire padrão para SOA'),
    ('dns_default_minimum', '86400', 'Minimum padrão para SOA'),
    ('session_timeout', '30', 'Timeout de sessão em minutos'),
    ('max_login_attempts', '5', 'Tentativas máximas de login'),
    ('lockout_duration', '15', 'Duração do bloqueio em minutos')
ON CONFLICT (key) DO NOTHING;

-- ===========================================
-- Função para atualizar updated_at
-- ===========================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para users
DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Trigger para settings
DROP TRIGGER IF EXISTS settings_updated_at ON settings;
CREATE TRIGGER settings_updated_at
    BEFORE UPDATE ON settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ===========================================
-- Log inicial de auditoria
-- ===========================================
INSERT INTO audit_logs (username, action, target_type, target_name, new_value)
VALUES (
    'system',
    'create',
    'system',
    'database',
    '{"message": "Database initialized"}'::jsonb
);
