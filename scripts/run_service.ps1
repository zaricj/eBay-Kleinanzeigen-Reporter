$srcEbayReporterDir = "D:\GitHub\eBay-Kleinanzeigen-Reporter"
$containerName = "elated_mclaren" # Your container name

Write-Output "Running host service for ebay kleinanzeigen scrapper"
Set-Location $srcEbayReporterDir
Write-Output "Switched path to '$srcEbayReporterDir'"

# 1. Start the WebUI with NiceGUI in a separate background window
Write-Output "Starting WebUI with NiceGUI..."
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList ".\ui.py" -WorkingDirectory $srcEbayReporterDir

# 2. Check if Docker Desktop engine process is active
Write-Output "Checking if Docker Desktop is running..."
$dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue

if (-not $dockerProcess) {
    Write-Output "Docker is not running. Launching Docker Desktop..."
    Start-Process -FilePath "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    
    Write-Output "Waiting for Docker daemon to become responsive..."
    while ($true) {
        docker info > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Output "Docker daemon is successfully initialized and ready!"
            break
        }
        Start-Sleep -Seconds 2
    }
} else {
    Write-Output "Docker is already running."
}

# 3. Handle Container Lifecycle (Reuse existing vs Create new)
Write-Output "Checking container status for '$containerName'..."

# Using {{.Names}} with an 's' prevents the formatter template crash
$containerExists = docker ps -a --filter "name=^${containerName}$" --format "{{.Names}}"

if ($containerExists) {
    # Check if it is actively running right now
    $containerRunning = docker ps --filter "name=^${containerName}$" --format "{{.Names}}"
    
    if ($containerRunning) {
        Write-Output "Container '$containerName' is already running. Attaching logs..."
        docker logs -f $containerName
    } else {
        Write-Output "Container '$containerName' exists but is stopped. Waking it up..."
        docker start $containerName
        docker logs -f $containerName
    }
} else {
    # If it genuinely does not exist, run it using your image name
    Write-Output "Container '$containerName' not found. Creating and running for the first time..."
    docker run --name $containerName -p 8000:8000 ebay-kleinanzeigen-api
}