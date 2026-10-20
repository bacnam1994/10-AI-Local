"""API Key and Provider Configuration Dialog."""

import asyncio
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt, QThread, Signal

from app.security.keyring_manager import secret_manager
from app.providers import get_adapter


class HealthCheckWorker(QThread):
    """Asynchronous worker to test provider connectivity without freezing dialog."""
    result_ready = Signal(str, bool, str)

    def __init__(self, provider: str, api_key: str):
        super().__init__()
        self.provider = provider
        self.api_key = api_key

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            adapter = get_adapter(self.provider, api_key=self.api_key)
            is_healthy = loop.run_until_complete(adapter.health_check())
            msg = "Kết nối thành công! API Key hợp lệ và máy chủ phản hồi tốt." if is_healthy else "Kiểm tra kết nối thất bại: Cấu hình chưa hợp lệ."
            self.result_ready.emit(self.provider, is_healthy, msg)
        except Exception as e:
            self.result_ready.emit(self.provider, False, f"Kiểm tra thất bại: {str(e)}")
        finally:
            loop.close()


class ConfigDialog(QDialog):
    """Dialog for configuring and securely saving AI Provider API keys."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cấu hình API Key & Nhà cung cấp AI")
        self.setMinimumWidth(560)
        self.workers: list[HealthCheckWorker] = []

        self._init_ui()
        self._load_keys()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        desc_label = QLabel(
            "API Key được lưu trữ mã hóa an toàn thông qua Windows Credential Manager (Keyring).\n"
            "Tuyệt đối không lưu mật khẩu dạng văn bản thô (plain-text) trên đĩa hoặc trong logs."
        )
        desc_label.setStyleSheet("color: #94A3B8; font-size: 11.5px;")
        layout.addWidget(desc_label)

        # Provider Group
        group = QGroupBox("Danh sách Nhà cung cấp Cloud AI")
        group_layout = QFormLayout(group)
        group_layout.setSpacing(12)

        # 1. OpenAI
        self.openai_input = QLineEdit()
        self.openai_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_input.setPlaceholderText("sk-proj-...")
        btn_test_openai = QPushButton("Kiểm tra")
        btn_test_openai.clicked.connect(lambda: self._test_connection("openai", self.openai_input.text()))

        row_openai = QHBoxLayout()
        row_openai.addWidget(self.openai_input)
        row_openai.addWidget(btn_test_openai)
        group_layout.addRow(QLabel("OpenAI API Key:"), row_openai)

        # 2. Anthropic
        self.anthropic_input = QLineEdit()
        self.anthropic_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_input.setPlaceholderText("sk-ant-api03-...")
        btn_test_anthropic = QPushButton("Kiểm tra")
        btn_test_anthropic.clicked.connect(lambda: self._test_connection("anthropic", self.anthropic_input.text()))

        row_anthropic = QHBoxLayout()
        row_anthropic.addWidget(self.anthropic_input)
        row_anthropic.addWidget(btn_test_anthropic)
        group_layout.addRow(QLabel("Anthropic API Key:"), row_anthropic)

        # 3. Google Gemini
        self.gemini_input = QLineEdit()
        self.gemini_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_input.setPlaceholderText("AIzaSy...")
        btn_test_gemini = QPushButton("Kiểm tra")
        btn_test_gemini.clicked.connect(lambda: self._test_connection("gemini", self.gemini_input.text()))

        row_gemini = QHBoxLayout()
        row_gemini.addWidget(self.gemini_input)
        row_gemini.addWidget(btn_test_gemini)
        group_layout.addRow(QLabel("Google Gemini Key:"), row_gemini)

        # 4. Groq (Ultra-fast LPU)
        self.groq_input = QLineEdit()
        self.groq_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_input.setPlaceholderText("gsk_...")
        btn_test_groq = QPushButton("Kiểm tra")
        btn_test_groq.clicked.connect(lambda: self._test_connection("groq", self.groq_input.text()))

        row_groq = QHBoxLayout()
        row_groq.addWidget(self.groq_input)
        row_groq.addWidget(btn_test_groq)
        group_layout.addRow(QLabel("Groq API Key (LPU):"), row_groq)

        # 5. DeepSeek
        self.deepseek_input = QLineEdit()
        self.deepseek_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepseek_input.setPlaceholderText("sk-...")
        btn_test_deepseek = QPushButton("Kiểm tra")
        btn_test_deepseek.clicked.connect(lambda: self._test_connection("deepseek", self.deepseek_input.text()))

        row_deepseek = QHBoxLayout()
        row_deepseek.addWidget(self.deepseek_input)
        row_deepseek.addWidget(btn_test_deepseek)
        group_layout.addRow(QLabel("DeepSeek API Key:"), row_deepseek)

        # 6. OpenRouter (Multi-Cloud Aggregator)
        self.openrouter_input = QLineEdit()
        self.openrouter_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openrouter_input.setPlaceholderText("sk-or-v1-...")
        btn_test_openrouter = QPushButton("Kiểm tra")
        btn_test_openrouter.clicked.connect(lambda: self._test_connection("openrouter", self.openrouter_input.text()))

        row_openrouter = QHBoxLayout()
        row_openrouter.addWidget(self.openrouter_input)
        row_openrouter.addWidget(btn_test_openrouter)
        group_layout.addRow(QLabel("OpenRouter Key:"), row_openrouter)

        # 7. Hugging Face (Serverless Inference)
        self.huggingface_input = QLineEdit()
        self.huggingface_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.huggingface_input.setPlaceholderText("hf_...")
        btn_test_hf = QPushButton("Kiểm tra")
        btn_test_hf.clicked.connect(lambda: self._test_connection("huggingface", self.huggingface_input.text()))

        row_hf = QHBoxLayout()
        row_hf.addWidget(self.huggingface_input)
        row_hf.addWidget(btn_test_hf)
        group_layout.addRow(QLabel("Hugging Face Key:"), row_hf)

        # 8. OmniRoute AI Gateway (http://localhost:20128/v1)
        self.omniroute_input = QLineEdit()
        self.omniroute_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.omniroute_input.setPlaceholderText("API key nếu có (hoặc để trống cho local gateway)")
        self.omniroute_url_input = QLineEdit()
        self.omniroute_url_input.setPlaceholderText("http://localhost:20128/v1")
        btn_test_omniroute = QPushButton("Kiểm tra")
        btn_test_omniroute.clicked.connect(
            lambda: self._test_connection("omniroute", self.omniroute_input.text())
        )

        row_omni = QHBoxLayout()
        row_omni.addWidget(self.omniroute_input, 6)
        row_omni.addWidget(btn_test_omniroute, 4)
        group_layout.addRow(QLabel("OmniRoute Key:"), row_omni)
        group_layout.addRow(QLabel("OmniRoute Gateway URL:"), self.omniroute_url_input)

        # 9. Custom Router / Ollama Gateway Base URL
        self.router_url_input = QLineEdit()
        self.router_url_input.setPlaceholderText("http://localhost:11434/v1 (Ollama) hoặc proxy riêng")
        group_layout.addRow(QLabel("Ollama / Custom URL:"), self.router_url_input)

        layout.addWidget(group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Lưu cấu hình an toàn")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self._save_keys)

        btn_cancel = QPushButton("Đóng")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _load_keys(self):
        self.openai_input.setText(secret_manager.get_api_key("openai") or "")
        self.anthropic_input.setText(secret_manager.get_api_key("anthropic") or "")
        self.gemini_input.setText(secret_manager.get_api_key("gemini") or "")
        self.groq_input.setText(secret_manager.get_api_key("groq") or "")
        self.deepseek_input.setText(secret_manager.get_api_key("deepseek") or "")
        self.openrouter_input.setText(secret_manager.get_api_key("openrouter") or "")
        self.huggingface_input.setText(secret_manager.get_api_key("huggingface") or "")
        self.omniroute_input.setText(secret_manager.get_api_key("omniroute") or "")
        self.omniroute_url_input.setText(secret_manager.get_api_key("omniroute_url") or "http://localhost:20128/v1")
        self.router_url_input.setText(secret_manager.get_api_key("custom_gateway_url") or "http://localhost:11434/v1")

    def _save_keys(self):
        secret_manager.set_api_key("openai", self.openai_input.text().strip())
        secret_manager.set_api_key("anthropic", self.anthropic_input.text().strip())
        secret_manager.set_api_key("gemini", self.gemini_input.text().strip())
        secret_manager.set_api_key("groq", self.groq_input.text().strip())
        secret_manager.set_api_key("deepseek", self.deepseek_input.text().strip())
        secret_manager.set_api_key("openrouter", self.openrouter_input.text().strip())
        secret_manager.set_api_key("huggingface", self.huggingface_input.text().strip())
        secret_manager.set_api_key("omniroute", self.omniroute_input.text().strip())
        
        omni_url = self.omniroute_url_input.text().strip() or "http://localhost:20128/v1"
        secret_manager.set_api_key("omniroute_url", omni_url)

        custom_url = self.router_url_input.text().strip() or "http://localhost:11434/v1"
        secret_manager.set_api_key("custom_gateway_url", custom_url)

        QMessageBox.information(self, "Thành công", "Đã lưu trữ an toàn các API Key vào Windows Credential Manager.")
        self.accept()

    def _test_connection(self, provider: str, key: str):
        if not key.strip():
            QMessageBox.warning(self, "Thiếu thông tin", f"Vui lòng nhập API Key của {provider.capitalize()} trước khi kiểm tra.")
            return

        worker = HealthCheckWorker(provider, key.strip())
        worker.result_ready.connect(self._on_test_result)
        self.workers.append(worker)
        worker.start()

    def _on_test_result(self, provider: str, is_ok: bool, message: str):
        if is_ok:
            QMessageBox.information(self, f"Kết nối {provider.upper()}", message)
        else:
            QMessageBox.warning(self, f"Lỗi kết nối {provider.upper()}", message)
