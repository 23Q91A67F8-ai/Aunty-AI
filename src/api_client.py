import base64
import requests
from typing import List, Dict, Any, Generator, Optional
from PySide6.QtCore import QThread, Signal


class APIClient:
    """Base class for API communication."""

    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @staticmethod
    def encode_image(image_path: str) -> str:
        """Converts an image file to a base64 encoded string."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def format_multimodal_message(self, role: str, text: str, image_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """Constructs a payload supporting text and multimodal attachments (images)."""
        if not image_paths:
            return {"role": role, "content": text}

        content_list = [{"type": "text", "text": text}]
        for path in image_paths:
            b64_img = self.encode_image(path)
            # Infer basic MIME type
            ext = path.split(".")[-1].lower()
            mime = "image/png" if ext == "png" else "image/jpeg"
            
            content_list.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{b64_img}"
                }
            })

        return {"role": role, "content": content_list}

    def stream_completion(self, messages: List[Dict[str, Any]], temperature: float = 0.2) -> Generator[str, None, None]:
        """Override in subclass."""
        raise NotImplementedError


class OpenRouterClient(APIClient):
    """Handles communication with models via OpenRouter API."""

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1", model: str = "0x-alpha"):
        super().__init__(api_key, base_url, model)

    def stream_completion(self, messages: List[Dict[str, Any]], temperature: float = 0.2) -> Generator[str, None, None]:
        """Sends a streaming inference request to OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/0x-alpha-agent/0x-alpha",
            "X-Title": "aunty.ai - Your Personal Coding Assistant",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": temperature
        }

        url = f"{self.base_url}/chat/completions"
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)

        if response.status_code != 200:
            raise Exception(f"API Error ({response.status_code}): {response.text}")

        for line in response.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                data_str = line_str[6:].strip()
                if data_str == "[DONE]":
                    break
                import json
                try:
                    data_json = json.loads(data_str)
                    delta = data_json["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except json.JSONDecodeError:
                    continue


class OllamaClient(APIClient):
    """Handles communication with local Ollama models."""

    def __init__(self, base_url: str = "http://localhost:11434/api", model: str = "llama2"):
        super().__init__("", base_url, model)

    def stream_completion(self, messages: List[Dict[str, Any]], temperature: float = 0.2) -> Generator[str, None, None]:
        """Sends a streaming inference request to local Ollama."""
        # Convert messages to Ollama format
        system_message = ""
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append(msg["content"])
        
        prompt = "\n".join(user_messages)
        if system_message:
            prompt = f"{system_message}\n\n{prompt}"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "temperature": temperature
        }

        url = f"{self.base_url}/generate"
        try:
            response = requests.post(url, json=payload, stream=True, timeout=120)
            
            if response.status_code != 200:
                raise Exception(f"Ollama Error ({response.status_code}): {response.text}")

            import json
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    data_json = json.loads(line.decode("utf-8"))
                    if "response" in data_json:
                        yield data_json["response"]
                except json.JSONDecodeError:
                    continue
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to Ollama. Make sure Ollama is running on localhost:11434")


class CompletionWorker(QThread):
    """Qt Worker thread to execute stream API requests asynchronously without freezing the UI."""
    chunk_received = Signal(str)
    finished_signal = Signal()
    error_signal = Signal(str)

    def __init__(self, client: APIClient, messages: List[Dict[str, Any]]):
        super().__init__()
        self.client = client
        self.messages = messages
        self._stop_requested = False

    def stop(self):
        """Request the worker to stop processing."""
        self._stop_requested = True

    def run(self):
        try:
            for chunk in self.client.stream_completion(self.messages):
                if self._stop_requested:
                    break
                self.chunk_received.emit(chunk)
            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))
