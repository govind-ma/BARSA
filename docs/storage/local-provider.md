# Local Storage Provider & Directory Structure

## 1. Default Data Directory Locations

BARSA resolves the data directory using platform standards:

- **Windows:** `%LOCALAPPDATA%\Barsa\data` (e.g. `C:\Users\<user>\AppData\Local\Barsa\data`)
- **macOS:** `~/Library/Application Support/Barsa`
- **Linux:** `~/.local/share/barsa`

### Overriding the Data Directory

Set the `BARSA_DATA_DIR` environment variable:

```powershell
$env:BARSA_DATA_DIR = "D:\MyBarsaData"
```

Or configure it in `.env`:
```ini
BARSA_DATA_DIR=D:/MyBarsaData
```

---

## 2. Directory Layout

```text
Barsa/
└── data/
    ├── barsa.db          # Main SQLite database
    ├── barsa.db-wal      # Write-Ahead Log
    ├── barsa.db-shm      # Shared memory index
    ├── artifacts/        # Content-addressed binary blob store
    │   ├── 97/
    │   │   └── 97e615af4c9fe... (SHA-256 named files)
    │   └── e3/
    │       └── e3b0c44298fc1...
    ├── exports/          # Generated package exports
    └── backups/          # Compressed database snapshots (.tar.gz)
```
