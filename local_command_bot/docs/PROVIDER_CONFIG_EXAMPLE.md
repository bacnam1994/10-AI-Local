# VÍ DỤ CẤU HÌNH NHÀ CUNG CẤP AI (PROVIDER CONFIGURATION EXAMPLES)

---

## 1. CÁC NHÀ CUNG CẤP CHÍNH THỨC ĐƯỢC HỖ TRỢ

Hệ thống hỗ trợ 3 Cloud AI lớn nhất hiện nay cùng chế độ Deterministic Mock:

| Nhà cung cấp | Identifier | Các model mặc định | Endpoint chính thức / Mặc định |
|---|---|---|---|
| **OpenAI** | `openai` | `gpt-4o-mini`, `gpt-4o` | `https://api.openai.com/v1/chat/completions` |
| **Anthropic** | `anthropic` | `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022` | `https://api.anthropic.com/v1/messages` |
| **Google Gemini** | `gemini` | `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash` | `https://generativelanguage.googleapis.com/v1beta/models/...` |
| **Groq (Siêu tốc LPU)** | `groq` | `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768` | `https://api.groq.com/openai/v1/chat/completions` |
| **OpenRouter** | `openrouter` | `anthropic/claude-3.5-sonnet`, `deepseek/deepseek-chat`, `openai/gpt-4o` | `https://openrouter.ai/api/v1/chat/completions` |
| **DeepSeek** | `deepseek` | `deepseek-chat`, `deepseek-reasoner` | `https://api.deepseek.com/v1/chat/completions` |
| **Ollama (Local Offline)** | `ollama` | `llama3.1`, `qwen2.5:14b`, `deepseek-r1:8b` | `http://localhost:11434/v1/chat/completions` |
| **Custom Gateway** | `custom` | Tùy biến bất kỳ model nào | URL tùy biến (OneAPI, LiteLLM, vLLM...) |
| **Mock Engine** | `mock` | `mock-model`, `mock-pro-model` | Bộ giả lập cục bộ (Offline / No Cost) |

---

## 2. PHÂN BỔ MÔ HÌNH THEO VAI TRÒ (ROLE-BASED MODEL MAPPING)

Tùy theo yêu cầu chi phí và độ phức tạp, bạn có thể phân chia vai trò:

### Cấu hình Tiết kiệm Chi phí (Budget-Friendly)
- **Planner (Lập kế hoạch)**: `gemini-1.5-flash` hoặc `gpt-4o-mini`
- **Researcher (Tra cứu)**: `gemini-1.5-flash`
- **Writer (Soạn thảo)**: `gpt-4o-mini`
- **Reviewer (Rà soát)**: `gemini-1.5-flash`

### Cấu hình Chất lượng Cao Chuyên sâu (Premium Quality)
- **Planner (Lập kế hoạch)**: `claude-3-5-sonnet-20241022` hoặc `gpt-4o`
- **Researcher (Tra cứu)**: `gpt-4o`
- **Writer (Soạn thảo)**: `claude-3-5-sonnet-20241022`
- **Reviewer (Rà soát)**: `gpt-4o`

---

## 3. VÍ DỤ CẤU HÌNH QUA CODE PYTHON

```python
from app.providers import get_adapter
from app.core.models import JobPlan

# 1. Khởi tạo adapter OpenAI với key an toàn
openai_adapter = get_adapter("openai", model="gpt-4o-mini")

# 2. Khởi tạo adapter Anthropic
claude_adapter = get_adapter("anthropic", model="claude-3-5-sonnet-20241022")

# 3. Khởi tạo adapter Gemini
gemini_adapter = get_adapter("gemini", model="gemini-1.5-flash")

# 4. Kiểm tra sức khỏe kết nối
async def test_health():
    is_ok = await openai_adapter.health_check()
    print("OpenAI Health:", is_ok)
```

---

## 4. BẢNG ƯỚC TÍNH CHI PHÍ (PRICE TABLE)

| Model | Prompt Tokens (trên 1M) | Completion Tokens (trên 1M) |
|---|:---:|:---:|
| `gpt-4o` | $2.50 | $10.00 |
| `gpt-4o-mini` | $0.15 | $0.60 |
| `claude-3-5-sonnet-20241022` | $3.00 | $15.00 |
| `claude-3-5-haiku-20241022` | $0.80 | $4.00 |
| `gemini-1.5-pro` | $1.25 | $5.00 |
| `gemini-1.5-flash` | $0.075 | $0.30 |
| `gemini-2.0-flash` | $0.10 | $0.40 |
| `mock-model` | $0.00 | $0.00 |
