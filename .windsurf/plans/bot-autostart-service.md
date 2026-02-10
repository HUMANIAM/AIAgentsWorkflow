# Bot Auto-Start Service Setup

Create a systemd user service to automatically start the Telegram bot when the machine boots up and send a startup notification message.

## Implementation Plan

1. **Create systemd user service file**
   - Service will run as user `ibrahim` (not root)
   - Auto-restart on failure
   - Start after network is ready
   - Working directory: project root
   - Use virtual environment python

2. **Modify startup message**
   - Change current message from "🤖 Telegram bot started - listening for team questions"
   - To: "🤖 I am back to life ibrahim"

3. **Enable and start the service**
   - Enable for automatic boot startup
   - Start immediately for testing

## Files to Create/Modify

### 1. Systemd Service File
`~/.config/systemd/user/steward-bot.service`

```ini
[Unit]
Description=Steward AI Zorba Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=ibrahim
Group=ibrahim
WorkingDirectory=/media/ibrahim/data/Apps_ideas/AISWTeam/AIAgentsWorkflow/steward_ai_zorba_bot
Environment=PATH=/media/ibrahim/data/Apps_ideas/AISWTeam/AIAgentsWorkflow/steward_ai_zorba_bot/.venv/bin
ExecStart=/media/ibrahim/data/Apps_ideas/AISWTeam/AIAgentsWorkflow/steward_ai_zorba_bot/.venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

### 2. Modify startup message
In `steward_ai_zorba_bot/apps/telegram/app.py` line 132:
```python
await send_msg(self.app.bot, user_id, "🤖 I am back to life ibrahim")
```

## Commands to Execute

```bash
# Create systemd user service directory
mkdir -p ~/.config/systemd/user

# Create service file
cat > ~/.config/systemd/user/steward-bot.service << 'EOF'
[Unit]
Description=Steward AI Zorba Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=ibrahim
Group=ibrahim
WorkingDirectory=/media/ibrahim/data/Apps_ideas/AISWTeam/AIAgentsWorkflow/steward_ai_zorba_bot
Environment=PATH=/media/ibrahim/data/Apps_ideas/AISWTeam/AIAgentsWorkflow/steward_ai_zorba_bot/.venv/bin
ExecStart=/media/ibrahim/data/Apps_ideas/AISWTeam/AIAgentsWorkflow/steward_ai_zorba_bot/.venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

# Reload systemd, enable and start
systemctl --user daemon-reload
systemctl --user enable steward-bot.service
systemctl --user start steward-bot.service

# Verify status
systemctl --user status steward-bot.service
```

## Testing

1. Stop current manual bot process
2. Start service
3. Check if bot sends "I am back to life ibrahim" message
4. Reboot machine to verify auto-start

## Benefits

- Bot starts automatically on boot
- Auto-restart if it crashes
- Logs captured in systemd journal
- Runs as non-root user (secure)
- Custom startup message as requested
