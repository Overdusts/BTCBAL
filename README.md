# Bitcoin Transaction Monitor

A lightweight Python script that monitors Bitcoin addresses and sends real-time Discord notifications for all transactions. Perfect for tracking payments, monitoring wallets, or keeping tabs on blockchain activity.

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-success)](https://github.com/yourusername/btc-transaction-monitor)

## Features

- 🔔 **Real-time notifications** - Get Discord alerts within 60 seconds of new transactions
- 💰 **Automatic USD conversion** - Shows both BTC and USD values using live prices
- 📊 **Detailed transaction info** - Amount, fees, confirmations, addresses, timestamps
- ✅ **Confirmation tracking** - Separate notifications for unconfirmed and confirmed transactions
- 🎨 **Color-coded embeds** - Green for incoming, red for outgoing, orange for unconfirmed
- 🧪 **Test mode** - Verify configuration before running 24/7
- 🔄 **Auto-recovery** - Continues monitoring even if API calls fail
- 📝 **Clean logging** - Console output for monitoring and debugging

## Screenshots

### Incoming Transaction (Confirmed)
![Incoming Transaction](https://via.placeholder.com/600x400?text=Discord+Notification+Example)

### Outgoing Transaction (Unconfirmed)
![Outgoing Transaction](https://via.placeholder.com/600x400?text=Discord+Notification+Example)

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)
- A Discord webhook URL

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/btc-transaction-monitor.git
cd btc-transaction-monitor
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure the script**

Edit `btc_monitor.py` and update these variables:

```python
BTC_ADDRESS = "your_bitcoin_address_here"
DISCORD_WEBHOOK = "your_discord_webhook_url_here"
CHECK_INTERVAL = 60  # Seconds between checks (default: 60)
```

### Getting a Discord Webhook

1. Open Discord and go to Server Settings → Integrations
2. Click "Create Webhook" or "View Webhooks"
3. Choose a channel and click "New Webhook"
4. Copy the webhook URL
5. Paste it into the `DISCORD_WEBHOOK` variable

## Usage

### Test Mode (Recommended First!)

Before running the monitor 24/7, test it to see your last 3 transactions:

```bash
python btc_monitor.py --test
```

This will:
- Display your current balance
- Show details of your last 3 transactions
- Ask if you want to send them to Discord as test notifications
- Let you verify everything works correctly

### Running the Monitor

#### Option 1: Direct Execution
```bash
python btc_monitor.py
```
*Note: This stops when you close the terminal*

#### Option 2: Background Process (Linux/Mac)
```bash
nohup python btc_monitor.py > monitor.log 2>&1 &

# View logs
tail -f monitor.log

# Stop the monitor
pkill -f btc_monitor.py
```

#### Option 3: Using Screen (Recommended for VPS)
```bash
# Start new screen session
screen -S btc_monitor

# Run the script
python btc_monitor.py

# Detach from screen: Press Ctrl+A then D
# Reattach later: screen -r btc_monitor
# Kill session: screen -X -S btc_monitor quit
```

#### Option 4: Systemd Service (Linux - Auto-start on boot)

Create `/etc/systemd/system/btc-monitor.service`:

```ini
[Unit]
Description=Bitcoin Transaction Monitor
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/btc-transaction-monitor
ExecStart=/usr/bin/python3 /path/to/btc-transaction-monitor/btc_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable btc-monitor
sudo systemctl start btc-monitor

# Check status
sudo systemctl status btc-monitor

# View logs
sudo journalctl -u btc-monitor -f
```

## Configuration

### Check Interval

Adjust how often the script checks for new transactions:

```python
CHECK_INTERVAL = 30   # Check every 30 seconds (more frequent)
CHECK_INTERVAL = 60   # Check every 1 minute (default, recommended)
CHECK_INTERVAL = 120  # Check every 2 minutes
CHECK_INTERVAL = 300  # Check every 5 minutes (less API calls)
```

### Notification Customization

The script sends notifications with the following information:
- Transaction type (incoming/outgoing)
- Amount in BTC and USD
- Number of confirmations
- Transaction hash with explorer link
- From/To addresses (up to 3)
- Current wallet balance
- Transaction timestamp
- Network fees

You can modify the `send_discord_notif()` function to customize the embed format.

## How It Works

1. **Initialization**: Script loads existing transactions to avoid duplicate notifications
2. **Monitoring Loop**: Every 60 seconds (configurable), the script:
   - Fetches recent transactions from mempool.space API
   - Checks for new transactions
   - Determines if incoming or outgoing
   - Calculates amounts and fees
   - Gets current BTC price
   - Sends Discord notification
3. **Confirmation Updates**: When unconfirmed transactions get confirmed, sends a second notification
4. **Error Handling**: Continues running even if API calls fail temporarily

## API Information

This script uses free public APIs:

- **mempool.space** - Bitcoin blockchain data (no API key required)
- **CoinGecko** - BTC price data (falls back to Coinpaprika)

Both APIs are free with generous rate limits suitable for monitoring a single address.

## Troubleshooting

### No notifications appearing

- Verify Discord webhook URL is correct
- Test webhook manually:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
  -d '{"content":"Test message"}' YOUR_WEBHOOK_URL
  ```
- Check firewall isn't blocking outbound HTTPS connections

### Script crashes or stops

- Check logs for error messages
- Ensure Python 3.7+ is installed: `python --version`
- Reinstall dependencies: `pip install -r requirements.txt`
- Run in test mode to verify configuration

### Missing transactions

- Transactions are detected within CHECK_INTERVAL (default 60 seconds)
- Verify the Bitcoin address is correct
- Try running in test mode to see if API is accessible

### High API usage warnings

- Increase CHECK_INTERVAL to 120 or 300 seconds
- The free APIs used have generous limits for single address monitoring

## Resource Usage

- **CPU**: <1% on average
- **Memory**: ~50MB
- **Network**: ~1KB per check (minimal bandwidth)
- **Disk**: Negligible (logs only if enabled)

## Security Considerations

- **Webhook URL**: Keep your Discord webhook URL private
- **Read-only**: This script only reads blockchain data, cannot send transactions
- **No private keys**: Never requires or stores wallet private keys
- **Open source**: All code is visible and auditable

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/yourusername/btc-transaction-monitor.git
cd btc-transaction-monitor
pip install -r requirements.txt

# Run tests (if available)
python -m pytest tests/
```

## Roadmap

- [ ] Multi-address monitoring
- [ ] Email notifications
- [ ] Telegram bot integration
- [ ] Web dashboard
- [ ] Transaction filtering (minimum amount)
- [ ] Database storage for transaction history
- [ ] Webhook notification retry logic

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [mempool.space](https://mempool.space) - Excellent Bitcoin blockchain explorer and API
- [CoinGecko](https://coingecko.com) - Cryptocurrency price data
- [Discord](https://discord.com) - Webhook notifications platform

## Support

If you find this project useful, consider:

- ⭐ Starring the repository
- 🐛 Reporting bugs via [Issues](https://github.com/yourusername/btc-transaction-monitor/issues)
- 💡 Suggesting features
- 📖 Improving documentation

## Disclaimer

This software is provided "as is", without warranty of any kind. Use at your own risk. Always verify transaction details on official blockchain explorers. This tool is for monitoring purposes only and does not provide financial advice.

## Contact

- GitHub: [@overdusts](https://github.com/overdusts)

---

