package handlers

import (
    "encoding/json"
    "fmt"
    "log"
    "net/http"
)

// TelegramUpdate — минимальная структура запроса от Telegram
type TelegramUpdate struct {
    Message struct {
        Text string `json:"text"`
        Chat struct {
            ID int64 `json:"id"`
        } `json:"chat"`
    } `json:"message"`
}

// TelegramHandler — базовый HTTP-хендлер для Telegram webhook
func TelegramHandler(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost {
        w.WriteHeader(http.StatusMethodNotAllowed)
        w.Write([]byte("Метод не поддерживается"))
        return
    }

    var update TelegramUpdate
    if err := json.NewDecoder(r.Body).Decode(&update); err != nil {
        log.Printf("❌ Ошибка разбора запроса Telegram: %v", err)
        w.WriteHeader(http.StatusBadRequest)
        return
    }

    log.Printf("📩 Получено сообщение от Telegram: %s", 
update.Message.Text)

    // Временно отвечаем заглушкой
    fmt.Fprintf(w, "Принято сообщение: %s", update.Message.Text)
}

