[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "C:\Users\letgo\Documents\인재전쟁",
    [string]$SessionId = "019f4be2-94a4-71b2-a106-c1da42bd642a"
)

$ErrorActionPreference = "Stop"
$workspace = Join-Path $WorkspaceRoot "final-workspaces\musinsa"
$submissionStage = Join-Path $WorkspaceRoot "temp-musinsa-submission-stage"
$extractRoot = Join-Path $WorkspaceRoot "temp-musinsa-zip-extracted"
$zipPath = Join-Path $WorkspaceRoot "final-deliverables\musinsa-submission.zip"
$questionnaire = Join-Path $WorkspaceRoot "final-questionnaires\musinsa.json"
$formAnswers = Join-Path $WorkspaceRoot "final-questionnaires\musinsa-form.md"
$repo = Join-Path $WorkspaceRoot "github\musinsa-repo"
$harness = Join-Path $WorkspaceRoot "plugin-harness"
$validation = Join-Path $workspace "validation"
$targetLog = Join-Path $workspace "logs\root-session-$SessionId.jsonl"
$sessionRoot = Join-Path $HOME ".codex\sessions"

function Assert-UnderRoot([string]$Path, [string]$Root) {
    $fullPath = [IO.Path]::GetFullPath($Path)
    $fullRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    if (-not $fullPath.StartsWith($fullRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe path outside root: $fullPath"
    }
}

function Reset-Directory([string]$Path, [string]$Root) {
    Assert-UnderRoot $Path $Root
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Path | Out-Null
}

function Invoke-Checked([scriptblock]$Command, [string]$FailureMessage) {
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage (exit $LASTEXITCODE)"
    }
}

$sourceCandidates = @(
    Get-ChildItem -LiteralPath $sessionRoot -Recurse -File -Filter "*$SessionId.jsonl" |
        Sort-Object LastWriteTime -Descending
)
if ($sourceCandidates.Count -ne 1) {
    throw "Expected exactly one source session for $SessionId; found $($sourceCandidates.Count)."
}
$sourceLog = $sourceCandidates[0].FullName

# The script is intentionally for post-thread use. Refuse a file that is still growing.
$lengthBefore = (Get-Item -LiteralPath $sourceLog).Length
Start-Sleep -Seconds 3
$lengthAfter = (Get-Item -LiteralPath $sourceLog).Length
if ($lengthBefore -ne $lengthAfter) {
    throw "Source session is still changing. Run finalize-musinsa.ps1 after the thread fully ends."
}

[IO.File]::Copy($sourceLog, $targetLog, $true)
$sourceHash = (Get-FileHash -LiteralPath $sourceLog -Algorithm SHA256).Hash.ToLower()
$copyHash = (Get-FileHash -LiteralPath $targetLog -Algorithm SHA256).Hash.ToLower()
if ($sourceHash -ne $copyHash) {
    throw "Raw log SHA-256 mismatch after byte-for-byte copy."
}

$secretPattern = '(?<![A-Za-z0-9_-])(sk-(proj|svcacct)-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|Bearer\s+[A-Za-z0-9._-]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)'
& rg --pcre2 -l -i $secretPattern (Join-Path $workspace "logs") | Out-Null
if ($LASTEXITCODE -eq 0) {
    throw "Potential secret found in raw logs. Inspect locally; do not edit the raw JSONL."
}
if ($LASTEXITCODE -ne 1) {
    throw "Secret scan failed with exit $LASTEXITCODE."
}

Get-ChildItem -LiteralPath (Join-Path $workspace "src") -Recurse -Directory -Filter "__pycache__" |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }
Get-ChildItem -LiteralPath (Join-Path $workspace "src") -Recurse -File -Filter "*.pyc" |
    Remove-Item -Force

Reset-Directory $submissionStage $WorkspaceRoot
Copy-Item -LiteralPath (Join-Path $workspace "src") -Destination (Join-Path $submissionStage "src") -Recurse
Copy-Item -LiteralPath (Join-Path $workspace "README.md") -Destination (Join-Path $submissionStage "README.md")
Copy-Item -LiteralPath (Join-Path $workspace "logs") -Destination (Join-Path $submissionStage "logs") -Recurse

Push-Location $harness
try {
    Invoke-Checked { python -X utf8 -m axwar_harness validate --submission $submissionStage --report (Join-Path $validation "finalize-harness-validate.json") } "Submission validation failed"
    Invoke-Checked { python -X utf8 -m axwar_harness validate-questionnaire --questionnaire $questionnaire --submission $submissionStage --report (Join-Path $validation "finalize-questionnaire-validation.json") } "Questionnaire validation failed"
    Invoke-Checked { python -X utf8 -m axwar_harness package --submission $submissionStage --output $zipPath --report (Join-Path $validation "finalize-package-report.json") } "Packaging failed"
    Invoke-Checked { python -X utf8 -m axwar_harness verify-zip --zip $zipPath --source $submissionStage --report (Join-Path $validation "finalize-verify-zip.json") } "ZIP verification failed"
}
finally {
    Pop-Location
}

Reset-Directory $extractRoot $WorkspaceRoot
Expand-Archive -LiteralPath $zipPath -DestinationPath $extractRoot
$sourceFiles = Get-ChildItem -LiteralPath $submissionStage -Recurse -File
$extractedFiles = Get-ChildItem -LiteralPath $extractRoot -Recurse -File
if ($sourceFiles.Count -ne $extractedFiles.Count) {
    throw "Extracted file count does not match source."
}
foreach ($sourceFile in $sourceFiles) {
    $relative = $sourceFile.FullName.Substring($submissionStage.Length + 1)
    $extracted = Join-Path $extractRoot $relative
    if (-not (Test-Path -LiteralPath $extracted)) {
        throw "Missing extracted file: $relative"
    }
    $a = (Get-FileHash -LiteralPath $sourceFile.FullName -Algorithm SHA256).Hash
    $b = (Get-FileHash -LiteralPath $extracted -Algorithm SHA256).Hash
    if ($a -ne $b) {
        throw "Extracted hash mismatch: $relative"
    }
}

$zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLower()
$finalization = [ordered]@{
    session_id = $SessionId
    source_log = $sourceLog
    source_bytes = $lengthAfter
    source_sha256 = $sourceHash
    copied_log = $targetLog
    copied_sha256 = $copyHash
    zip_path = $zipPath
    zip_sha256 = $zipHash
    finalized_at = (Get-Date).ToString("o")
}
$finalization | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 (Join-Path $validation "finalized-session-log.json")

if (-not (Test-Path -LiteralPath (Join-Path $repo ".git"))) {
    throw "Git repository is missing: $repo"
}
if (git -C $repo status --porcelain) {
    throw "Git repository must be clean before finalization."
}

Invoke-Checked { git -C $repo fetch origin --prune } "git fetch failed"
Invoke-Checked { git -C $repo switch project/musinsa } "Cannot switch project branch"
Invoke-Checked { git -C $repo pull --ff-only origin project/musinsa } "Project branch is not fast-forwardable"

$project = Join-Path $repo "projects\musinsa"
foreach ($name in @("src", "logs", "validation")) {
    $target = Join-Path $project $name
    Assert-UnderRoot $target $repo
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
}
Copy-Item -LiteralPath (Join-Path $workspace "src") -Destination (Join-Path $project "src") -Recurse
Copy-Item -LiteralPath (Join-Path $workspace "logs") -Destination (Join-Path $project "logs") -Recurse
Copy-Item -LiteralPath (Join-Path $workspace "validation") -Destination (Join-Path $project "validation") -Recurse
Copy-Item -LiteralPath (Join-Path $workspace "README.md") -Destination (Join-Path $project "README.md") -Force
Copy-Item -LiteralPath $questionnaire -Destination (Join-Path $project "questionnaire.json") -Force
Copy-Item -LiteralPath $formAnswers -Destination (Join-Path $project "form-answers.md") -Force
Copy-Item -LiteralPath (Join-Path $workspace "evidence-report.md") -Destination (Join-Path $project "evidence-report.md") -Force
Copy-Item -LiteralPath (Join-Path $workspace "finalize-musinsa.ps1") -Destination (Join-Path $project "finalize-musinsa.ps1") -Force
Copy-Item -LiteralPath $zipPath -Destination (Join-Path $project "submission.zip") -Force

$sumLines = Get-ChildItem -LiteralPath $project -Recurse -File |
    Where-Object Name -ne "SHA256SUMS.txt" |
    Sort-Object FullName |
    ForEach-Object {
        $relative = $_.FullName.Substring($project.Length + 1).Replace('\', '/')
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower()
        "$hash  $relative"
    }
$sumLines | Set-Content -Encoding utf8 (Join-Path $project "SHA256SUMS.txt")

Invoke-Checked { git -C $repo add -- projects/musinsa } "git add project failed"
git -C $repo diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "Project branch already contains the finalized artifacts."
} elseif ($LASTEXITCODE -eq 1) {
    Invoke-Checked { git -C $repo commit -m "fix(musinsa): finalize complete session log and package" } "Project commit failed"
    Invoke-Checked { git -C $repo push origin project/musinsa } "Project push failed"
} else {
    throw "Unable to inspect staged project changes."
}

Invoke-Checked { git -C $repo switch main } "Cannot switch main"
Invoke-Checked { git -C $repo pull --ff-only origin main } "Main branch is not fast-forwardable"
$mainReadme = Join-Path $repo "README.md"
$lines = Get-Content -LiteralPath $mainReadme -Encoding utf8
$updated = foreach ($line in $lines) {
    if ($line -match '^\| 무신사 \|') {
        [regex]::Replace($line, '`[0-9a-f]{64}`', ('`' + $zipHash + '`'), 1)
    } else {
        $line
    }
}
$updated | Set-Content -LiteralPath $mainReadme -Encoding utf8
Invoke-Checked { git -C $repo add -- README.md } "git add README failed"
git -C $repo diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "Main README already contains ZIP SHA-256 $zipHash."
} elseif ($LASTEXITCODE -eq 1) {
    Invoke-Checked { git -C $repo commit -m "docs: refresh MUSINSA finalized package hash" } "Main README commit failed"
    Invoke-Checked { git -C $repo push origin main } "Main push failed"
} else {
    throw "Unable to inspect staged README changes."
}

Write-Host "Finalized Musinsa submission. ZIP SHA-256: $zipHash"
