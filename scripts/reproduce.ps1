param(
    [switch]$RunEvaluation
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = [System.IO.Path]::GetFullPath((Join-Path $repoRoot '..\.venv\Scripts\python.exe'))
if (-not (Test-Path $python)) {
    $pythonCommand = Get-Command python -ErrorAction Stop
    $python = $pythonCommand.Source
}

Set-Location $repoRoot
if ($RunEvaluation) {
    Write-Output 'Running a reduced one-seed exploratory evaluation; larger runs exceed the 15-minute budget and this is not confirmatory.'
    & $python -m ai_engine.evaluation.run_all --seeds 1 --output-dir docs/evaluation/reproduction_run
}
else {
    Write-Output 'Regenerating Markdown tables and figures from docs/evaluation/results.csv; no new evaluation data is generated.'
    & $python -m ai_engine.evaluation.run_all --refresh-reports --output-dir docs/evaluation
}

if ($LASTEXITCODE -ne 0) {
    throw "Evaluation command failed with exit code $LASTEXITCODE."
}
