<#
.SYNOPSIS
    Sets up virtual environment and continuously runs the Python program located at ./src/main.py, restarting it upon exit.

.DESCRIPTION
    This script:
    1. Finds a compatible Python version (3.9 through 3.13)
    2. Creates a virtual environment (.venv) if it doesn't exist
    3. Installs dependencies from requirements.txt if needed
    4. Enters an infinite loop where it starts the specified Python program
    If the program exits, the script waits for 2 seconds and then restarts it.
    The loop can be interrupted by pressing Ctrl+C, which triggers the catch block to display a stop message and error details.

.NOTES
    - Requires Python 3.9 through 3.13. Python 3.14 is not currently supported by pygame 2.6.1.
    - Intended for streaming or testing scenarios where automatic restarts are useful.
    - Automatically manages virtual environment and dependencies.

.EXAMPLE
    PS> .\run.ps1
#>

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvPath = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts/python.exe"

function Test-CompatiblePython {
    param([Parameter(Mandatory = $true)][string]$PythonPath)

    if (-not (Test-Path $PythonPath -PathType Leaf)) {
        return $false
    }

    $isCompatible = & $PythonPath -c "import sys; print(int((3, 9) <= sys.version_info[:2] <= (3, 13)))" 2>$null
    return $LASTEXITCODE -eq 0 -and $isCompatible -eq "1"
}

function Find-CompatiblePython {
    $launcher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($launcher) {
        foreach ($version in @("3.13", "3.12", "3.11", "3.10", "3.9")) {
            $pythonPath = & $launcher.Source "-$version" -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $pythonPath) {
                $pythonPath = ($pythonPath | Select-Object -Last 1).Trim()
                if (Test-CompatiblePython $pythonPath) {
                    return $pythonPath
                }
            }
        }
    }

    $python = Get-Command "python" -ErrorAction SilentlyContinue
    if ($python -and (Test-CompatiblePython $python.Source)) {
        return $python.Source
    }

    return $null
}

# Function to check if dependencies are installed
function Test-DependenciesInstalled {
    $requirementsPath = "./requirements.txt"
    if (-not (Test-Path $requirementsPath)) {
        Write-Host "requirements.txt not found, skipping dependency check"
        return $true
    }

    try {
        $requirements = Get-Content $requirementsPath | Where-Object { $_ -match "^[^#]" -and $_.Trim() -ne "" }
        foreach ($requirement in $requirements) {
            $packageName = ($requirement -split "==")[0].Trim()
            $result = & $venvPython -m pip show $packageName 2>$null
            if (-not $result) {
                return $false
            }
        }
        return $true
    }
    catch {
        return $false
    }
}

Push-Location $projectRoot
try {
    if (-not (Test-CompatiblePython $venvPython)) {
        $pythonPath = Find-CompatiblePython
        if (-not $pythonPath) {
            throw "No compatible Python installation was found. Install 64-bit Python 3.13 from https://www.python.org/downloads/ and run this script again. Python 3.14 is not currently supported by pygame 2.6.1."
        }

        # A virtual environment is disposable and cannot switch to a different base interpreter.
        if (Test-Path $venvPath) {
            Write-Host "The existing virtual environment uses an unsupported Python version. Recreating it..."
            Remove-Item -LiteralPath $venvPath -Recurse -Force
        }

        $pythonVersion = & $pythonPath --version
        Write-Host "Using $pythonVersion at $pythonPath"
        Write-Host "Creating virtual environment..."
        & $pythonPath -m venv $venvPath
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtual environment"
        }
        Write-Host "Virtual environment created successfully."
    }

    # Check if dependencies need to be installed
    if (-not (Test-DependenciesInstalled)) {
        Write-Host "Installing dependencies..."
        & $venvPython -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install dependencies"
        }
        Write-Host "Dependencies installed successfully."
    } else {
        Write-Host "Dependencies already installed."
    }

    # Run the application
    while ($true) {
        Write-Host "Starting program..."
        & $venvPython "./src/main.py"
        $exitCode = $LASTEXITCODE

        if ($exitCode -eq 0) {
            Write-Host "Program was closed by user. Exiting..."
            break
        } else {
            Write-Host "Program exited with error code $exitCode. Restarting in 2 seconds... Press Ctrl+C to stop."
            Start-Sleep -Seconds 2
        }
    }
}
catch {
    Write-Host "Stopped by user or error occurred."
    Write-Host "Error details:"
    Write-Host $_  # This shows the error that was caught
}
finally {
    Pop-Location
}
