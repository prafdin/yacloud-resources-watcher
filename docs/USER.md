# User Guide

## Getting Started

### 1. Find Your Bot

1. Open Telegram
2. Search for your bot username (e.g., `@my_cloud_watcher_bot`)
3. Click "Start" or send `/start`

### 2. First Message

The bot will welcome you and show available commands:

```
👋 Welcome to Yandex Cloud Resources Watcher!

I'll send you daily reports about your cloud resources.

Commands:
/resources - Get current resource list
/status - Check bot status
/help - Show this help message
```

## Commands

### /start

**Purpose:** Start the bot and see welcome message

**Usage:** Send `/start`

**Response:** Welcome message with command list

### /resources

**Purpose:** Get current list of all your Yandex Cloud resources

**Usage:** Send `/resources`

**Response:** Detailed report of all resources in your cloud folder

**Example Response:**
```
📊 Yandex Cloud Resources Report

🖥️ Compute Instances (3):
  • vm-1: RUNNING (CPU: 2, RAM: 4GB, IP: 51.250.1.1)
  • vm-2: STOPPED
  • vm-3: RUNNING (CPU: 4, RAM: 8GB, IP: 51.250.1.2)

🗄️ Databases (2):
  • postgres-cluster: RUNNING (v15, s2.micro)
  • mysql-cluster: STOPPED

📦 Storage Buckets (2):
  • my-bucket-1
  • my-bucket-2

🌐 Networks (1):
  • default-network

🔒 Security Groups (3):
  • default-security-group (5 rules)
  • web-security-group (8 rules)
  • db-security-group (4 rules)

⚖️ Load Balancers (1):
  • my-load-balancer: ACTIVE (51.250.2.1:80)

📦 Container Registries (1):
  • my-registry

⚡ Serverless Functions (2):
  • my-function-1: ACTIVE (python311, 128MB)
  • my-function-2: ACTIVE (nodejs18, 256MB)

📦 Serverless Containers (1):
  • my-container: ACTIVE (1 CPU, 128MB)

🌍 DNS Zones (1):
  • example.com (public)

🚪 API Gateways (1):
  • my-api-gateway: ACTIVE (b1g...apigw.yandexcloud.net)

Total: 17 resources (12 running/active, 2 stopped, 3 other)

Reply OK to acknowledge
```

### /status

**Purpose:** Check bot status and next scheduled report time

**Usage:** Send `/status`

**Response:**
```
🤖 Bot Status

✅ Bot is running
📅 Next report: 2024-01-15 21:00:00 (Europe/Moscow)
📊 Pending notifications: 0
📜 Total reports sent: 42
🕐 Uptime: 5 days, 3 hours
```

### /help

**Purpose:** Show list of available commands

**Usage:** Send `/help`

**Response:**
```
📚 Available Commands

/start - Welcome message and setup
/resources - Get current resource list
/status - Check bot and scheduler status
/help - Show this help message

📅 Daily Reports
I send resource reports every day at 21:00 (Europe/Moscow).
If you don't reply "OK" within 2 hours, I'll remind you.

🔒 Access Control
Only authorized users can interact with this bot.
```

## Daily Reports

### What to Expect

- **When:** Every day at 21:00 (configurable by administrator)
- **What:** Complete list of all resources in your Yandex Cloud folder
- **Format:** Organized by resource type with status and details

### Report Content

The report includes:

1. **Compute Instances (VMs)**
   - Name and status (RUNNING, STOPPED, etc.)
   - CPU cores and RAM
   - IP addresses (if running)

2. **Managed Databases**
   - PostgreSQL, MySQL, MongoDB, ClickHouse clusters
   - Status and configuration

3. **Object Storage**
   - List of buckets

4. **VPC Resources**
   - Networks, subnets, security groups
   - Rule counts for security groups

5. **Load Balancers**
   - Status and listener addresses

6. **Container Services**
   - Container registries
   - Serverless functions and containers

7. **DNS and API Gateway**
   - DNS zones
   - API gateways

8. **Summary**
   - Total resource count
   - Count by status (running, stopped, etc.)

### Acknowledging Reports

**Why acknowledge?**
- Confirms you've reviewed the resource list
- Stops reminder messages
- Creates audit trail

**How to acknowledge:**
1. Receive daily report
2. Review the resource list
3. Reply with `OK` (case-insensitive)
4. Bot confirms: `✅ Acknowledged`

**Example:**
```
[Bot sends report]
📊 Yandex Cloud Resources Report
...

[You reply]
OK

[Bot confirms]
✅ Acknowledged
```

## Reminders

### How Reminders Work

1. Bot sends daily report at configured time (e.g., 21:00)
2. If you don't reply "OK" within 2 hours (configurable):
   - Bot sends reminder message
   - Reminder references original report
3. Reply "OK" to acknowledge

### Reminder Message

```
⏰ Reminder: Please acknowledge the previous resource report by replying OK
```

### Stopping Reminders

Simply reply "OK" to any report or reminder to stop further reminders for that day.

## Resource Statuses

### Compute Instances

- **RUNNING** - VM is active and running
- **STOPPED** - VM is stopped but still exists
- **STARTING** - VM is starting up
- **STOPPING** - VM is shutting down
- **ERROR** - VM has an error

### Managed Databases

- **RUNNING** - Cluster is active
- **STOPPED** - Cluster is stopped
- **CREATING** - Cluster is being created
- **UPDATING** - Cluster is being updated
- **DELETING** - Cluster is being deleted

### Load Balancers

- **ACTIVE** - Load balancer is active
- **INACTIVE** - Load balancer is inactive
- **CREATING** - Load balancer is being created
- **DELETING** - Load balancer is being deleted

### Serverless Functions/Containers

- **ACTIVE** - Function/container is active
- **CREATING** - Being created
- **DELETING** - Being deleted

## Common Questions

### Q: Why am I not receiving reports?

**A:** Possible reasons:
- Bot is not running (contact administrator)
- Your user ID is not configured (contact administrator)
- Telegram notifications are disabled (check Telegram settings)

### Q: Can I change the report time?

**A:** No, report time is configured by the administrator. Contact them to request a change.

### Q: What if I accidentally reply something other than OK?

**A:** Just reply "OK" to acknowledge. Other messages are ignored.

### Q: Can other people use this bot?

**A:** No, the bot is configured to respond only to one authorized user. This is for security.

### Q: Why are some resources missing from the report?

**A:** Possible reasons:
- Resources are in a different folder
- Service Account doesn't have access to those resources
- Resource type is not monitored (contact administrator)

### Q: What does "Reply OK to acknowledge" mean?

**A:** It's optional. Reply "OK" if you want to:
- Confirm you've seen the report
- Stop reminder messages
- Create an audit trail

### Q: Can I get reports more frequently?

**A:** No, the bot is designed for daily reports. For more frequent monitoring, consider Yandex Cloud monitoring tools.

### Q: What if I have multiple folders?

**A:** The bot monitors only one folder (configured by administrator). For multiple folders, you need separate bot instances.

## Troubleshooting

### Bot Doesn't Respond

**Possible causes:**
- Bot is offline
- Your user ID is not authorized
- Network issues

**Solutions:**
1. Wait a few minutes and try again
2. Check if bot is online (ask administrator)
3. Verify you're using the correct bot

### Report Shows No Resources

**Possible causes:**
- Folder is empty
- Service Account doesn't have access
- Configuration error

**Solutions:**
1. Verify folder has resources in Yandex Cloud console
2. Contact administrator to check Service Account permissions
3. Check logs (administrator access required)

### Reminder Keeps Coming

**Possible causes:**
- You didn't reply "OK"
- Reply was not recognized

**Solutions:**
1. Reply exactly "OK" (case-insensitive)
2. Don't include extra text
3. Wait for confirmation message

## Tips

### Best Practices

1. **Review reports daily** - Stay aware of your cloud resources
2. **Acknowledge reports** - Stops reminders and creates audit trail
3. **Check for unexpected resources** - Report unauthorized resources to administrator
4. **Monitor costs** - Use reports to track resource usage

### Understanding Costs

- **RUNNING** resources typically incur costs
- **STOPPED** resources may still incur storage costs
- Review reports to identify unused resources
- Contact administrator to delete unused resources

### Security

- Don't share bot access with others
- Report any suspicious activity to administrator
- Keep your Telegram account secure
- Use strong password and 2FA for Telegram

## Contact

For issues or questions:
1. Check this guide first
2. Try `/help` command in bot
3. Contact your bot administrator
