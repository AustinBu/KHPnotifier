import requests

class DiscordNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send(self, message):
        if not self.webhook_url:
            print(f"DEBUG: No Webhook URL. Message would have been: {message}")
            return
            
        payload = {"content": message}
        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send Discord notification: {e}")

    def alert_status_change(self, is_maintenance):
        # Customizable messages
        if is_maintenance:
            msg = "🚨 KHP is down."
        else:
            msg = "✅ KHP is up."
        self.send(msg)