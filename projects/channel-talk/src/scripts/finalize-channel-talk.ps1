param(
    [Parameter(Mandatory = $true)][string]$TranscriptPath,
    [string]$SubmissionRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [Parameter(Mandatory = $true)][string]$HarnessRoot,
    [Parameter(Mandatory = $true)][string]$OutputZip,
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"
$transcript = (Resolve-Path -LiteralPath $TranscriptPath).Path
$submission = (Resolve-Path -LiteralPath $SubmissionRoot).Path
$harness = (Resolve-Path -LiteralPath $HarnessRoot).Path
if ([IO.Path]::GetExtension($transcript) -ne ".jsonl") { throw "Transcript must be JSONL." }

# Exclusive access proves the writer has released the transcript. Running sessions must fail here.
$probe = [IO.File]::Open($transcript, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::None)
$probe.Dispose()

$logs = Join-Path $submission "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$destination = Join-Path $logs "codex-current-task-raw.jsonl"
[IO.File]::Copy($transcript, $destination, $true)
$sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $transcript).Hash.ToLowerInvariant()
$copyHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash.ToLowerInvariant()
if ($sourceHash -ne $copyHash) { throw "Raw transcript hash mismatch." }

$secretPattern = '(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|Bearer\s+[A-Za-z0-9._-]{20,})'
if (Select-String -LiteralPath $destination -Pattern $secretPattern -Quiet) { throw "Secret-like value found in transcript; do not edit the log. Resolve outside this script." }
$cache = Get-ChildItem -Recurse -Force (Join-Path $submission "src") | Where-Object { $_.Name -eq "__pycache__" -or $_.Extension -in @(".pyc", ".pyo") }
if ($cache) { throw "Cache files must be removed before final packaging." }

$packageReport = [IO.Path]::ChangeExtension($OutputZip, ".package.json")
$verifyReport = [IO.Path]::ChangeExtension($OutputZip, ".verify.json")
Push-Location $harness
try {
    & $PythonCommand -m axwar_harness package --submission $submission --output $OutputZip --report $packageReport
    if ($LASTEXITCODE -ne 0) { throw "Packaging failed." }
    & $PythonCommand -m axwar_harness verify-zip --zip $OutputZip --source $submission --report $verifyReport
    if ($LASTEXITCODE -ne 0) { throw "ZIP verification failed." }
}
finally { Pop-Location }

$result = [ordered]@{
    status = "FINALIZED_AFTER_SESSION_END"
    transcript = $transcript
    transcript_sha256 = $sourceHash
    transcript_bytes = (Get-Item -LiteralPath $transcript).Length
    zip = (Resolve-Path -LiteralPath $OutputZip).Path
    zip_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $OutputZip).Hash.ToLowerInvariant()
    zip_bytes = (Get-Item -LiteralPath $OutputZip).Length
}
$result | ConvertTo-Json -Depth 3
