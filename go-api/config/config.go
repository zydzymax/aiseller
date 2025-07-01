package config

import (
    "log"
    "os"
    "sync"

    "github.com/joho/godotenv"
)

// Config — структура для хранения конфигурации приложения
type Config struct {
    Env         string
    Port        string
    PostgresDSN string
    RedisAddr   string
    OpenAIKey   string
}

var (
    cfg  *Config
    once sync.Once
)

// LoadConfig загружает конфигурацию только один раз (singleton)
func LoadConfig() *Config {
    once.Do(func() {
        _ = godotenv.Load("../.env") // Загружаем .env файл, если он есть

        cfg = &Config{
            Env:         getEnv("APP_ENV", "development"),
            Port:        getEnv("PORT", "8080"),
            PostgresDSN: mustHave("POSTGRES_DSN"),
            RedisAddr:   mustHave("REDIS_ADDR"),
            OpenAIKey:   mustHave("OPENAI_KEY"),
        }
    })
    return cfg
}

// getEnv — возвращает значение или дефолт
func getEnv(key string, defaultVal string) string {
    if val, ok := os.LookupEnv(key); ok {
        return val
    }
    return defaultVal
}

// mustHave — проверяет наличие обязательной переменной
func mustHave(key string) string {
    if val, ok := os.LookupEnv(key); ok && val != "" {
        return val
    }
    log.Fatalf("❌ Обязательная переменная окружения %s не установлена", 
key)
    return ""
}

