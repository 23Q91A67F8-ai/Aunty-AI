import uuid
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QTextEdit, QPushButton, QFileDialog, QLabel, QLineEdit,
    QSplitter, QCheckBox, QMessageBox, QListWidgetItem, QComboBox, QMenu, QFrame
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont

from config import ConfigManager, STEALTH_MODEL_ID, AVAILABLE_MODELS
from storage import StorageManager
from workspace import WorkspaceManager
from api_client import OpenRouterClient, OllamaClient, CompletionWorker
from tts import SpeechWorker


class MainWindow(QMainWindow):
    """Main Application Window for aunty.ai - Your Personal Coding Assistant."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("aunty.ai — Your Personal Coding Assistant")
        self.resize(1280, 800)

        # Initialize Managers
        self.config = ConfigManager()
        self.storage = StorageManager()
        self.workspace = WorkspaceManager()

        self.current_session_id = None
        self.attached_images = []
        self.active_worker = None
        self.voice_enabled = False
        self.speech_worker = None
        self.current_response_text = ""

        self._init_ui()
        self._apply_dark_theme()
        self.load_sessions()
        self._refresh_model_status()
        self._refresh_workspace_display()
        self._refresh_session_status()
        self._update_attachment_label()

    def _init_ui(self):
        main_widget = QWidget()
        main_widget.setObjectName("appRoot")
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Main horizontal splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left Sidebar (Sessions & Workspace Setup)
        sidebar = QFrame()
        sidebar.setObjectName("sidebarPanel")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)
        sidebar_layout.setSpacing(12)

        app_title = QLabel("aunty.ai")
        app_title.setObjectName("brandTitle")
        sidebar_layout.addWidget(app_title)

        app_subtitle = QLabel("Your coding workspace for project-aware AI help.")
        app_subtitle.setObjectName("mutedLabel")
        app_subtitle.setWordWrap(True)
        sidebar_layout.addWidget(app_subtitle)

        sidebar_layout.addSpacing(8)

        # Model & Provider Selection
        sidebar_layout.addWidget(self._section_label("Model Configuration"))
        self.model_selector = QComboBox()
        for model_id, model_info in AVAILABLE_MODELS.items():
            self.model_selector.addItem(model_info["name"], model_id)
        current_model = self.config.get("model", STEALTH_MODEL_ID)
        index = self.model_selector.findData(current_model)
        if index >= 0:
            self.model_selector.setCurrentIndex(index)
        self.model_selector.currentIndexChanged.connect(self._on_model_changed)
        sidebar_layout.addWidget(QLabel("Select Model"))
        sidebar_layout.addWidget(self.model_selector)

        self.lbl_provider_badge = QLabel("")
        self.lbl_provider_badge.setObjectName("chipInfo")
        sidebar_layout.addWidget(self.lbl_provider_badge)

        # API Key input
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter OpenRouter API Key...")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setText(self.config.get("api_key", ""))
        self.api_key_input.textChanged.connect(self._on_api_key_changed)
        sidebar_layout.addWidget(QLabel("OpenRouter API Key"))
        sidebar_layout.addWidget(self.api_key_input)

        # New Chat Button
        new_chat_btn = QPushButton("+ New Chat")
        new_chat_btn.clicked.connect(self.create_new_session)
        new_chat_btn.setObjectName("primaryButton")
        sidebar_layout.addWidget(new_chat_btn)

        # Sessions List
        sidebar_layout.addWidget(self._section_label("Recent Chats"))
        self.session_list_widget = QListWidget()
        self.session_list_widget.itemClicked.connect(self._on_session_selected)
        self.session_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.session_list_widget.customContextMenuRequested.connect(self._on_session_context_menu)
        self.session_list_widget.setAlternatingRowColors(True)
        sidebar_layout.addWidget(self.session_list_widget)

        # Delete Chat Button
        self.btn_delete_chat = QPushButton("Delete Selected Chat")
        self.btn_delete_chat.clicked.connect(self._delete_selected_session)
        self.btn_delete_chat.setObjectName("dangerButton")
        sidebar_layout.addWidget(self.btn_delete_chat)

        # Workspace Directory Picker
        sidebar_layout.addWidget(self._section_label("Workspace"))
        self.btn_select_workspace = QPushButton("Open Project Folder")
        self.btn_select_workspace.clicked.connect(self.select_workspace)
        sidebar_layout.addWidget(self.btn_select_workspace)

        self.lbl_workspace_path = QLabel("")
        self.lbl_workspace_path.setObjectName("mutedLabel")
        self.lbl_workspace_path.setWordWrap(True)
        sidebar_layout.addWidget(self.lbl_workspace_path)

        self.lbl_workspace_hint = QLabel("Load a repository to provide project context during coding chats.")
        self.lbl_workspace_hint.setObjectName("hintLabel")
        self.lbl_workspace_hint.setWordWrap(True)
        sidebar_layout.addWidget(self.lbl_workspace_hint)

        sidebar_layout.addStretch(1)
        sidebar.setFixedWidth(280)
        splitter.addWidget(sidebar)

        # Right Panel (Chat and Code Interaction)
        chat_container = QFrame()
        chat_container.setObjectName("chatPanel")
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(20, 20, 20, 20)
        chat_layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        header_text = QVBoxLayout()
        header_text.setSpacing(4)

        self.lbl_chat_title = QLabel("Coding Assistant")
        self.lbl_chat_title.setObjectName("panelTitle")
        header_text.addWidget(self.lbl_chat_title)

        self.lbl_chat_subtitle = QLabel("Ask for refactors, explanations, debugging help, or architecture guidance.")
        self.lbl_chat_subtitle.setObjectName("mutedLabel")
        self.lbl_chat_subtitle.setWordWrap(True)
        header_text.addWidget(self.lbl_chat_subtitle)
        header_row.addLayout(header_text, 1)

        self.lbl_model_status = QLabel("")
        self.lbl_model_status.setObjectName("statusChip")
        self.lbl_model_status.setAlignment(Qt.AlignCenter)
        header_row.addWidget(self.lbl_model_status, 0, Qt.AlignTop)
        chat_layout.addLayout(header_row)

        info_row = QHBoxLayout()
        info_row.setSpacing(10)

        self.lbl_workspace_status = QLabel("")
        self.lbl_workspace_status.setObjectName("statusCard")
        self.lbl_workspace_status.setWordWrap(True)
        info_row.addWidget(self.lbl_workspace_status, 1)

        self.lbl_session_status = QLabel("")
        self.lbl_session_status.setObjectName("statusCard")
        self.lbl_session_status.setWordWrap(True)
        info_row.addWidget(self.lbl_session_status, 1)
        chat_layout.addLayout(info_row)

        # Conversation History Area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 10))
        self.chat_display.setPlaceholderText("Conversation appears here after you start a chat.")
        self.chat_display.setHtml(
            "<h3>Welcome to aunty.ai</h3>"
            "<p>Open a project, start a session, and describe the coding task you want help with.</p>"
        )
        chat_layout.addWidget(self.chat_display)

        # Attachments Status Label
        self.lbl_attachments = QLabel("")
        self.lbl_attachments.setObjectName("infoBar")
        chat_layout.addWidget(self.lbl_attachments)

        options_row = QHBoxLayout()
        options_row.setSpacing(16)

        # Workspace context toggle checkbox
        self.chk_include_context = QCheckBox("Include workspace context")
        self.chk_include_context.setToolTip("Adds the loaded project codebase to the prompt when needed.")
        options_row.addWidget(self.chk_include_context)

        # Voice toggle checkbox
        self.chk_voice = QCheckBox("Enable voice responses")
        self.chk_voice.stateChanged.connect(self._on_voice_toggle)
        options_row.addWidget(self.chk_voice)
        options_row.addStretch(1)
        chat_layout.addLayout(options_row)

        # Input Area Controls
        input_controls_layout = QHBoxLayout()
        input_controls_layout.setSpacing(12)

        self.input_text = QTextEdit()
        self.input_text.setMinimumHeight(96)
        self.input_text.setMaximumHeight(140)
        self.input_text.setPlaceholderText("Ask aunty.ai to refactor, write, or explain code...")
        input_controls_layout.addWidget(self.input_text)

        action_btn_layout = QVBoxLayout()
        action_btn_layout.setSpacing(10)

        self.btn_attach_image = QPushButton("Attach Image")
        self.btn_attach_image.clicked.connect(self.attach_image)
        action_btn_layout.addWidget(self.btn_attach_image)

        self.btn_send = QPushButton("Send")
        self.btn_send.clicked.connect(self.send_message)
        self.btn_send.setObjectName("primaryButton")
        action_btn_layout.addWidget(self.btn_send)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.stop_response)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setObjectName("dangerButton")
        action_btn_layout.addWidget(self.btn_stop)
        action_btn_layout.addStretch(1)

        input_controls_layout.addLayout(action_btn_layout)
        chat_layout.addLayout(input_controls_layout)

        splitter.addWidget(chat_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

    def _apply_dark_theme(self):
        """Applies a modern dark stylesheet matching the repository badges theme."""
        dark_stylesheet = """
            QMainWindow, QWidget {
                background-color: #0B1120;
                color: #F3F4F6;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            #appRoot {
                background-color: #0B1120;
            }
            #sidebarPanel, #chatPanel {
                background-color: #111827;
                border: 1px solid #1F2937;
                border-radius: 18px;
            }
            #brandTitle {
                font-size: 24px;
                font-weight: 700;
                color: #F8FAFC;
            }
            #panelTitle {
                font-size: 20px;
                font-weight: 700;
                color: #F8FAFC;
            }
            #mutedLabel {
                color: #94A3B8;
                font-size: 12px;
            }
            #hintLabel {
                color: #64748B;
                font-size: 11px;
            }
            #chipInfo, #statusChip {
                background-color: #172554;
                color: #BFDBFE;
                border: 1px solid #1D4ED8;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
            }
            #statusCard, #infoBar {
                background-color: #0F172A;
                color: #CBD5E1;
                border: 1px solid #1E293B;
                border-radius: 12px;
                padding: 10px 12px;
                font-size: 12px;
            }
            QTextEdit, QLineEdit, QListWidget {
                background-color: #1F2937;
                color: #F9FAFB;
                border: 1px solid #374151;
                border-radius: 12px;
                padding: 8px;
                selection-background-color: #2563EB;
            }
            QTextEdit:focus, QLineEdit:focus, QListWidget:focus, QComboBox:focus {
                border: 1px solid #3B82F6;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: #1D4ED8;
                color: #EFF6FF;
            }
            QPushButton {
                background-color: #0EA5E9;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 10px;
                padding: 10px 14px;
            }
            QPushButton:hover {
                background-color: #0284C7;
            }
            QPushButton#primaryButton {
                background-color: #2563EB;
            }
            QPushButton#primaryButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton#dangerButton {
                background-color: #DC2626;
            }
            QPushButton#dangerButton:hover {
                background-color: #B91C1C;
            }
            QCheckBox {
                color: #CBD5E1;
            }
            QComboBox {
                background-color: #1F2937;
                color: #F9FAFB;
                border: 1px solid #374151;
                border-radius: 10px;
                padding: 8px 10px;
            }
            QMenu {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #1E293B;
            }
            QMenu::item:selected {
                background-color: #1D4ED8;
            }
            QSplitter::handle {
                background-color: #374151;
                width: 6px;
            }
        """
        self.setStyleSheet(dark_stylesheet)

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(f"<b>{text}</b>")
        return label

    def _refresh_model_status(self):
        current_model = self.model_selector.currentData()
        model_info = AVAILABLE_MODELS.get(current_model, {})
        model_name = model_info.get("name", "Unknown Model")
        provider = model_info.get("provider", "openrouter").title()
        self.lbl_provider_badge.setText(f"Provider: {provider}")
        self.lbl_model_status.setText(f"Active Model: {model_name}")

    def _refresh_workspace_display(self):
        if self.workspace.root_dir:
            directory = str(self.workspace.root_dir)
            folder_name = os.path.basename(directory) or directory
            self.lbl_workspace_path.setText(folder_name)
            self.lbl_workspace_status.setText(f"Workspace loaded: {folder_name}")
        else:
            self.lbl_workspace_path.setText("No project folder loaded yet.")
            self.lbl_workspace_status.setText("Workspace not loaded. Open a project folder to ground the assistant in your codebase.")

    def _refresh_session_status(self):
        if self.current_session_id:
            self.lbl_session_status.setText(f"Active session: {self.current_session_id[:8]}")
        else:
            self.lbl_session_status.setText("No active session. Create a new chat to begin.")

    def _update_attachment_label(self):
        if self.attached_images:
            self.lbl_attachments.setText(f"{len(self.attached_images)} image attachment(s) ready to send")
        else:
            self.lbl_attachments.setText("No attachments added")

    def _select_session_in_list(self, session_id: str):
        for index in range(self.session_list_widget.count()):
            item = self.session_list_widget.item(index)
            if item.data(Qt.UserRole) == session_id:
                self.session_list_widget.setCurrentItem(item)
                break

    def _on_api_key_changed(self, text: str):
        self.config.set("api_key", text.strip())

    def _on_model_changed(self, index: int):
        """Handle model selection change."""
        model_id = self.model_selector.itemData(index)
        if model_id:
            self.config.set("model", model_id)
            provider = AVAILABLE_MODELS.get(model_id, {}).get("provider", "openrouter")
            self.config.set("provider", provider)
            self._refresh_model_status()

    def load_sessions(self):
        self.session_list_widget.clear()
        sessions = self.storage.get_sessions()
        for sess in sessions:
            item = QListWidgetItem(sess["title"])
            item.setData(Qt.UserRole, sess["id"])
            self.session_list_widget.addItem(item)

        if not sessions:
            self.create_new_session()
            return

        if self.current_session_id:
            self._select_session_in_list(self.current_session_id)

        self._refresh_session_status()

    def _on_session_context_menu(self, position):
        """Handle right-click context menu on session list."""
        item = self.session_list_widget.itemAt(position)
        if not item:
            return

        menu = QMenu(self)
        delete_action = menu.addAction("🗑️ Delete Chat")
        
        action = menu.exec(self.session_list_widget.mapToGlobal(position))
        
        if action == delete_action:
            session_id = item.data(Qt.UserRole)
            reply = QMessageBox.question(
                self, 
                "Delete Chat?", 
                f"Are you sure you want to delete '{item.text()}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.storage.delete_session(session_id)
                self.load_sessions()
                # Clear chat display if deleted session was selected
                if self.current_session_id == session_id:
                    self.current_session_id = None
                    self.chat_display.clear()

    def _delete_selected_session(self):
        """Delete the currently selected session."""
        current_item = self.session_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a chat to delete.")
            return

        session_id = current_item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self,
            "Delete Chat?",
            f"Are you sure you want to delete '{current_item.text()}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.storage.delete_session(session_id)
            self.load_sessions()
            # Clear chat display if deleted session was selected
            if self.current_session_id == session_id:
                self.current_session_id = None
                self.chat_display.clear()

    def create_new_session(self):
        session_id = str(uuid.uuid4())
        title = f"Session {session_id[:6]}"
        ws_path = str(self.workspace.root_dir) if self.workspace.root_dir else None

        self.storage.create_session(session_id, title, ws_path)
        self.current_session_id = session_id
        self.chat_display.clear()
        self.load_sessions()
        self._select_session_in_list(session_id)
        self._refresh_session_status()

    def select_workspace(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if directory:
            self.workspace.set_root(directory)
            self._refresh_workspace_display()

    def attach_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.attached_images.append(file_path)
            self._update_attachment_label()

    def _on_session_selected(self, item: QListWidgetItem):
        session_id = item.data(Qt.UserRole)
        self.current_session_id = session_id
        self._refresh_session_status()
        self.reload_chat_history()

    def reload_chat_history(self):
        self.chat_display.clear()
        messages = self.storage.get_messages(self.current_session_id)
        for msg in messages:
            role = "User" if msg["role"] == "user" else "0x Alpha"
            self.chat_display.append(f"<b>[{role}]</b>:\n{msg['content']}\n")

    def send_message(self):
        # Ensure a session exists
        if not self.current_session_id:
            QMessageBox.warning(self, "No Chat Session", "Please create a new chat first by clicking '+ New Chat'")
            return

        current_model = self.config.get("model", STEALTH_MODEL_ID)
        provider = AVAILABLE_MODELS.get(current_model, {}).get("provider", "openrouter")

        # Validate required credentials
        if provider == "openrouter":
            api_key = self.config.get("api_key")
            if not api_key:
                QMessageBox.warning(self, "API Key Missing", "Please enter an OpenRouter API key to continue.")
                return
        elif provider == "ollama":
            # Ollama doesn't require API key but needs to be running
            pass

        text = self.input_text.toPlainText().strip()
        if not text and not self.attached_images:
            return

        # Prepare messages array
        history = self.storage.get_messages(self.current_session_id)
        api_messages = []

        # System message
        api_messages.append({
            "role": "system",
            "content": "You are an expert software engineering assistant optimized for long-horizon multi-step coding tasks."
        })

        # Inject whole workspace context into prompt if checkbox checked
        if self.chk_include_context.isChecked() and self.workspace.root_dir:
            workspace_context = self.workspace.build_context_prompt()
            if workspace_context:
                api_messages.append({
                    "role": "user",
                    "content": f"Workspace Context:\n{workspace_context}"
                })

        # Append existing history
        for msg in history:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        # Create appropriate client based on provider
        if provider == "openrouter":
            client = OpenRouterClient(
                api_key=self.config.get("api_key"),
                base_url=self.config.get("api_base"),
                model=current_model
            )
        elif provider == "ollama":
            client = OllamaClient(
                base_url=self.config.get("ollama_base"),
                model=current_model.replace("-local", "")  # Strip -local suffix for actual model name
            )
        else:
            QMessageBox.critical(self, "Unknown Provider", f"Provider {provider} not supported.")
            return

        # Format user's current message with multimodal support
        user_msg_payload = client.format_multimodal_message("user", text, self.attached_images)
        api_messages.append(user_msg_payload)

        # Save user message to database
        self.storage.add_message(self.current_session_id, "user", text, self.attached_images)
        self.chat_display.append(f"<b>[You]</b>:\n{text}\n")

        # Clear inputs
        self.input_text.clear()
        self.attached_images = []
        self._update_attachment_label()

        # Prepare UI for Streaming Response
        model_name = AVAILABLE_MODELS.get(current_model, {}).get("name", "Assistant")
        self.chat_display.append(f"<b>[{model_name}]</b>:\n")
        self.btn_send.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.current_response_text = ""

        # Run completion streaming on separate worker thread
        self.worker = CompletionWorker(client, api_messages)
        self.worker.chunk_received.connect(self._handle_chunk)
        self.worker.error_signal.connect(self._handle_error)
        self.worker.finished_signal.connect(self._handle_finished)
        self.worker.start()

    def stop_response(self):
        """Stop the current response stream."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.btn_send.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.chat_display.append("\n\n[Response Stopped by User]")
            # Save partial response to storage
            full_text = self.current_response_text.strip()
            if full_text:
                self.storage.add_message(self.current_session_id, "assistant", f"{full_text}\n\n[Stopped]")
            self.current_response_text = ""

    def _on_voice_toggle(self):
        """Toggle voice on/off."""
        self.voice_enabled = self.chk_voice.isChecked()

    @Slot(str)
    def _handle_chunk(self, chunk: str):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.chat_display.setTextCursor(cursor)
        # Accumulate response for TTS
        self.current_response_text += chunk

    @Slot(str)
    def _handle_error(self, error_msg: str):
        QMessageBox.critical(self, "Model Error", f"Failed to get response: {error_msg}")
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)

    @Slot()
    @Slot()
    def _handle_finished(self):
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        full_text = self.current_response_text.strip()
        if full_text:
            self.storage.add_message(self.current_session_id, "assistant", full_text)
        
        # Speak the response if voice is enabled
        if self.voice_enabled and self.current_response_text.strip():
            # Limit response for TTS (to avoid long delays)
            text_to_speak = self.current_response_text[:1000]  # First 1000 chars
            self.speech_worker = SpeechWorker(text_to_speak)
            self.speech_worker.finished_signal.connect(self._on_speech_finished)
            self.speech_worker.error_signal.connect(self._on_speech_error)
            self.speech_worker.start()
        
        self.current_response_text = ""

    def _on_speech_finished(self):
        """Called when TTS finishes speaking."""
        pass

    def _on_speech_error(self, error: str):
        """Handle TTS errors."""
        print(f"Voice error: {error}")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
