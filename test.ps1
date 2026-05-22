$ComputerList = Get-Content "C:\Temp\Servers.txt" 
$OutputFolder = "C:\Temp\InventoryData"
if (!(Test-Path $OutputFolder)) { New-Item -ItemType Directory -Path $OutputFolder }

$ThrottleLimit = 50 
$TotalComputers = $ComputerList.Count
$Counter = [System.Collections.Concurrent.ConcurrentDictionary[string,int]]::new()
$Counter.TryAdd("Processed", 0)

$ComputerList | ForEach-Object -Parallel {
    $Computer = $_
    $OutDir = "C:\Temp\InventoryData"
    
    Write-Host "Connecting to $Computer..." -ForegroundColor Cyan
    
    try {
        # 1. Get Services with Error Handling
        $Services = Get-CimInstance -ComputerName $Computer -ClassName Win32_Service -ErrorAction Stop | 
            Where-Object { $_.Name -notmatch 'svchost|System|TrustedInstaller' } |
            Select-Object @{N='Host';E={$Computer}}, Name, DisplayName, StartMode, State
        
        $Services | Export-Csv -Path "$OutDir\$Computer`_Services.csv" -NoTypeInformation

        # 2. Get Processes with Error Handling
        $Processes = Get-CimInstance -ComputerName $Computer -ClassName Win32_Process -ErrorAction Stop | 
            Where-Object { $_.Name -notmatch 'svchost|Idle|System' } |
            Select-Object @{N='Host';E={$Computer}}, Name, ProcessId, CommandLine
            
        $Processes | Export-Csv -Path "$OutDir\$Computer`_Processes.csv" -NoTypeInformation
        
    } catch {
        Write-Warning "Failed to connect to $Computer : $($_.Exception.Message)"
        "$Computer : Failed - $($_.Exception.Message)" | Out-File "$OutDir\ErrorLog.txt" -Append
    }
} -ThrottleLimit $ThrottleLimit
