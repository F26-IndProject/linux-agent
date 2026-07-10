# LISA Linux Agent

The LISA Linux Agent simulates realistic user behaviour on Ubuntu 22.04 desktop machines as part of the LISA cyber-range platform.

---

## Prerequisites

Before proceeding, ensure the following are in place:

- LISA Server is set up and running
- Network connectivity to the LISA Server
- Ubuntu 22.04 desktop with a graphical session
- Python 3.10+
- Agent email account already created on the LISA Server — [Adding a new email account on LISA Server](https://github.com/F26-IndProject/mailserver#part-5-adding-a-new-email-account)
- VS Code installed

Important! Follow all steps below in the order they are presented
---

## 1. Install Necessary Tools

```bash
sudo apt install -y git libnss3-tools xdotool
```

---

## 2. DNS and SSL Configuration

### DNS Configuration

Edit the hosts file and add the DNS info for your LISA Server:

```bash
sudo nano /etc/hosts
```

Add the following line:

```
<LISA_SERVER_IP>  mail.lisa.local  lisa.local
```

For example:

```
192.168.100.10  mail.lisa.local  lisa.local
```

Reference: [Linux DNS Setup](https://github.com/F26-IndProject/mailserver#part-1-configuring-local-dns-records)

### SSL Configuration

Python imaplib, smtplib, requests uses the system trust store

Add the LISA Server certificate to the system trust store of your Linux agent.

On the server, start a temporary HTTP server to host the certs created from the mailserver setup:

```bash
python3 -m http.server 9999 --directory /etc/ssl/mail
```

On the Linux agent, download and install the certificate:

```bash
wget http://<LISA_SERVER_IP>:9999/mail.lisa.local.crt
sudo cp mail.lisa.local.crt /usr/local/share/ca-certificates/mail.lisa.local.crt
sudo update-ca-certificates
```

Reference: [Distributing server certs to agents](https://github.com/F26-IndProject/mailserver#distribute-the-certificate-to-agents)

---

## 3. Set Up Agent Email Account on the LISA Server

You need to set up the agent's email account on the LISA Server before configuring Thunderbird.

Follow this guide: [Adding a new email account on LISA Server](https://github.com/F26-IndProject/mailserver#part-5-adding-a-new-email-account)

---

## 4. Configure Thunderbird Email Client

Open Thunderbird and configure the email account of the agent using manual configuration.

Use the following settings to configure Thunderbird on the agent machine:
Make sure to click on manual configuration.

**Incoming mail (IMAP):**

| Setting        | Value               |
|----------------|---------------------|
| Protocol       | IMAP                |
| Hostname       | mail.lisa.local     |
| Port           | 993                 |
| Connection Sec | SSL/TLS             |
| Authentication | Normal Password     |
| Username       | Agent_Name          |

**Outgoing mail (SMTP):**

| Setting        | Value               |
|----------------|---------------------|
| Hostname       | mail.lisa.local     |
| Port           | 587                 |
| Connection Sec | STARTTLS            |
| Authentication | Normal Password     |
| Username       | Agent_Name          |

Then click on Done, Add security exception Window pops up, confirm security exception.
though we added the mail server certs to trust store, Thunderbird uses it's own trust store.

close thunderbird before the next step

Also add the server certificate to Thunderbird's trust store (Very Important):

```bash
certutil -A -n "mail.lisa.local" -t "CT,," -i mail.lisa.local.crt -d ~/.thunderbird/*.default-release
```

Reference: [Thunderbird configuration guide](https://github.com/F26-IndProject/mailserver#thunderbird-ubuntu)

---

## 5. Configure Auto-Login and X11

The agent requires a logged-in graphical session. The `xdotool` utility used for email sending only works on X11 — Ubuntu 22.04 defaults to Wayland so this step is mandatory.

Both settings are configured in the same file:

```bash
sudo nano /etc/gdm3/custom.conf
```

Under `[daemon]`, set:

```
AutomaticLoginEnable=true
AutomaticLogin=your_username
WaylandEnable=false
```

Keyring

Auto-login bypasses the login screen so the keyring does not get unlocked automatically. You must set the keyring password to empty so it unlocks without prompting.

⚠️ Stored passwords will become unencrypted. This is acceptable for a cyber-range agent machine.

Open Passwords and Keys (Seahorse) → right-click on Login → Change Password → enter your current password → leave the new password blank → click Continue.

Save and reboot:

```bash
sudo reboot
```

Verify X11 is active:

```bash
echo $XDG_SESSION_TYPE
```

Expected output: `x11`

Verify xdotool is working:

```bash
xdotool getactivewindow
```

This should return a window ID number. If it errors, X11 is not set up correctly.

---

> ⚠️ **Make sure steps 1 to 5 are completed and verified before proceeding.**

---

## 6. Clone and Run the Agent

### Clone the Repository

```bash
git clone https://github.com/F26-IndProject/linux-agent.git
cd linux-agent
```

### Configure the Environment File

Edit the `.env` file:

```bash
nano .env
```

```
SERVER_IP=your_server_IP
SERVER_PORT=8000
DB_HOST=your_server_IP
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_PORT=5432
# EMAIL CONFIGS
MAIL_SERVER=mail.lisa.local
MAIL_IMAP_PORT=993
MAIL_SMTP_PORT=587
MAIL_USER=agent_email@domain
MAIL_PASSWORD=agent_mail_password
```

### Run the Installation Script

> ⚠️ **Important:** Do not run this script with `sudo` or as the root user. Run it as the regular user who will be using the agent.

```bash
chmod +x install.sh && ./install.sh
```

The script will ask for your password when needed and will:

- Install all system and Python dependencies
- Compile the agent and log writer binaries
- Set up the agent as an RDP target
- Register and start the agent as a systemd user service

---

## Verifying the Setup

```bash
# Check service status
systemctl --user status lisa-agent

# View live logs
journalctl --user -u lisa-agent -f
```

To view live logs:

```bash
journalctl --user -u lisa-agent -f
```

For parent process verification:

```bash
ps -eo pid,ppid,comm --forest | grep -E "gnome-terminal|firefox|thunderbird|soffice|code|eog|evince|okular|shotwell|mupdf|oosplash|ssh|document-viewer|evince|atril|xreader|qpdfview"
```

Then verify the parent of a specific process:

```bash
ps -o pid,ppid,comm -p <PPID>
```

For verifying the PPID of log writer:

```bash
lsof ~/linux-agent/logs/agent.log
```

Then:

```bash
ps -o pid,ppid,comm -p <PID_FROM_LSOF>
```
repeate the command until you see the parent process concerning log writer

Parent for all processes started by the agent will be the systemd
