$osInfo = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion"
$osInfo.ProductName            # OS name (e.g., "Windows 10 Pro")
$osInfo.ReleaseId               # Release version (e.g., "2004" for Windows 10)
$osInfo.CurrentBuild            # Build number
$osInfo.CurrentVersion          # Version number