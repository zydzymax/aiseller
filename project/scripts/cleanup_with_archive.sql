-- Создание архивных таблиц
CREATE TABLE IF NOT EXISTS archived_messages (LIKE messages INCLUDING ALL);
CREATE TABLE IF NOT EXISTS archived_conversations (LIKE conversations INCLUDING ALL);
CREATE TABLE IF NOT EXISTS archived_leads (LIKE leads INCLUDING ALL);
CREATE TABLE IF NOT EXISTS archived_analytics (LIKE analytics INCLUDING ALL);

-- Архивация и удаление сообщений старше 90 дней
INSERT INTO archived_messages SELECT * FROM messages WHERE timestamp < NOW() - INTERVAL '90 days';
DELETE FROM messages WHERE timestamp < NOW() - INTERVAL '90 days';

-- Архивация и удаление завершённых диалогов старше 90 дней
INSERT INTO archived_conversations SELECT * FROM conversations
WHERE ended_at IS NOT NULL AND ended_at < NOW() - INTERVAL '90 days';
DELETE FROM conversations WHERE ended_at IS NOT NULL AND ended_at < NOW() - INTERVAL '90 days';

-- Архивация и удаление лидов старше 180 дней в статусах 'rejected', 'unresponsive'
INSERT INTO archived_leads SELECT * FROM leads
WHERE created_at < NOW() - INTERVAL '180 days' AND status IN ('rejected', 'unresponsive');
DELETE FROM leads
WHERE created_at < NOW() - INTERVAL '180 days' AND status IN ('rejected', 'unresponsive');

-- Архивация и удаление аналитики старше 180 дней
INSERT INTO archived_analytics SELECT * FROM analytics
WHERE timestamp < NOW() - INTERVAL '180 days';
DELETE FROM analytics
WHERE timestamp < NOW() - INTERVAL '180 days';