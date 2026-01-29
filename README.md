# Tracer Active Directory Bridge

A lightweight Python service that bridges Active Directory with the Tracer system. It runs as a scheduled task on a Windows server, queries AD for user and group information upon request from Tracer, and sends the data back.

## Overview

```
┌─────────────────┐         ┌──────────────────────────┐         ┌─────────────────┐
│  Tracer System  │ ◄─────► │  TracerActivedirBridge   │ ◄─────► │ Active Directory│
│     (API)       │   HTTP  │     (This Service)       │   AD    │     Server      │
└─────────────────┘         └──────────────────────────┘         └─────────────────┘
```

## Features

- **User Information Lookup**: Retrieves AD user attributes including:
  - Email address
  - Display name
  - Description
  - Job title

- **Group Membership Queries**: Fetches all members of specified AD groups

- **Scheduled Execution**: Runs automatically via Windows Task Scheduler (hourly by default)

- **API-Driven**: Responds to requests from Tracer system - only fetches data that Tracer needs

## Requirements

- Python 3.11+
- Windows Server with Active Directory access
- Network access to Tracer API endpoint

## Dependencies

```
requests
pyad
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kaunofakultetas/tracer-activedir-bridge.git
   cd TracerActivedirBridge
   ```

2. **Install dependencies:**
   ```bash
   pip install requests pyad
   ```

3. **Configure the service:**
   ```bash
   copy config.json.sample config.json
   ```
   
   Edit `config.json` with your settings:
   ```json
   {
       "tracer": {
           "tracerActivedirBridgeUrl": "http://your-tracer-server:800/api/bridge/activedir",
           "tracerActivedirBridgeApi": "YOUR_API_KEY_HERE"
       },
       "activedir": {
           "domain": "corp.example.com",
           "baseDn": "DC=corp,DC=example,DC=com",
           "groupPaths": {
               "default": "OU=Groups,OU=Organization",
               "IT-*": "OU=IT,OU=Departments",
               "HR-*": "OU=HR,OU=Departments"
           }
       }
   }
   ```

4. **Import the scheduled task (optional):**
   
   First, edit `TracerActivedirBridge.xml` and update the `<WorkingDirectory>` path to match your installation location.

   **Task Scheduler GUI**
   1. Open Task Scheduler → Action → Import Task
   2. Select `TracerActivedirBridge.xml`
   3. In the General tab, select **"Run whether user is logged on or not"**
   4. Enter your domain credentials when prompted
   
   The account must have AD read permissions.

## Configuration

### Tracer Settings

| Setting | Description |
|---------|-------------|
| `tracer.tracerActivedirBridgeUrl` | Tracer API endpoint for AD bridge communication |
| `tracer.tracerActivedirBridgeApi` | API key for authenticating with Tracer |

### Active Directory Settings

| Setting | Description |
|---------|-------------|
| `activedir.domain` | Your AD domain (e.g., `corp.example.com`) |
| `activedir.baseDn` | Base DN for AD queries. If omitted, auto-generated from `domain` |
| `activedir.groupPaths` | Object mapping group names/patterns to their OU paths |

### Group Path Matching

The `groupPaths` configuration supports flexible mapping of AD groups to their OU locations:

```json
{
    "groupPaths": {
        "default": "OU=Groups,OU=Organization",
        "IT-*": "OU=IT,OU=Departments",
        "HR-*": "OU=HR,OU=Departments",
        "Finance-Team": "OU=Finance,OU=Departments"
    }
}
```

**Matching rules (in order of priority):**
1. **Exact match** - If a group name matches a key exactly, that path is used
2. **Wildcard match** - Patterns using `*`, `?`, `[seq]` are supported (Unix shell-style)
3. **Default fallback** - The `default` key is used if no other match is found

**Example resolutions:**

| Group Name | Matched Pattern | Resolved OU Path |
|------------|-----------------|------------------|
| `Finance-Team` | Exact match | `OU=Finance,OU=Departments` |
| `IT-Support` | `IT-*` | `OU=IT,OU=Departments` |
| `IT-Admins` | `IT-*` | `OU=IT,OU=Departments` |
| `HR-Managers` | `HR-*` | `OU=HR,OU=Departments` |
| `Sales-Team` | `default` | `OU=Groups,OU=Organization` |

**Full DN generated:** `CN={GroupName},{OU Path},{Base DN}`

Example: `CN=IT-Support,OU=IT,OU=Departments,DC=corp,DC=example,DC=com`

## Usage

### Manual Execution

```bash
python TracerActivedirBridge.py
```

### Scheduled Task

The included `TracerActivedirBridge.xml` configures a Windows scheduled task with:
- **Interval**: Runs every hour
- **Execution timeout**: 30 minutes
- **Restart on failure**: 3 retries with 1-minute intervals
- **Run level**: Highest available privileges

## How It Works

```
1. GET  → Tracer API     : Fetch pending AD queries (user info, group members)
2. Query → Active Directory : Execute AD queries for requested data
3. POST → Tracer API     : Send collected AD data back to Tracer
```

### Data Flow

1. **Service starts** and sends GET request to Tracer API
2. **Tracer responds** with lists of:
   - `aduserinfo`: User CNs to look up
   - `adgroupmembers`: Group names to enumerate
3. **Service queries AD** for each requested item
4. **Results sent** back to Tracer via POST request

### Example Tracer Request

```json
{
    "aduserinfo": ["john.doe", "jane.smith"],
    "adgroupmembers": ["IT-Department", "Managers"]
}
```

### Example Response to Tracer

```json
{
    "aduserinfo": {
        "john.doe": {
            "Email": "john.doe@company.com",
            "NameSurname": "John Doe",
            "Description": "IT Administrator",
            "JobTitle": "System Administrator"
        }
    },
    "adgroupmembers": {
        "IT-Department": ["john.doe", "jane.smith", "bob.wilson"]
    }
}
```

## File Structure

```
TracerActivedirBridge/
├── TracerActivedirBridge.py    # Main service script
├── TracerActivedirBridge.xml   # Windows Task Scheduler template
├── config.json                 # Configuration (gitignored)
├── config.json.sample          # Configuration template
└── README.md                   # This file
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: pyad` | Install with `pip install pyad` |
| Connection refused to Tracer | Verify `tracerActivedirBridgeUrl` and network connectivity |
| AD user not found | Ensure the CN exists in Active Directory |
| Permission denied | Run with domain account that has AD read access |

