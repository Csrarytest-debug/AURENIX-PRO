param(
  [Parameter(Mandatory=$true)][string]$File
)
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($env:AURENIX_CODESIGN_PFX_BASE64) -or
    [string]::IsNullOrWhiteSpace($env:AURENIX_CODESIGN_PFX_PASSWORD)) {
  throw 'Trusted code-signing certificate secrets are missing. Refusing unsigned release.'
}
if (-not (Test-Path -LiteralPath $File -PathType Leaf)) { throw "Signing target missing: $File" }
$kits = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
$signtool = Get-ChildItem -LiteralPath $kits -Filter signtool.exe -File -Recurse -ErrorAction SilentlyContinue |
  Where-Object { $_.DirectoryName -match '[\\/]x64$' } |
  Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $signtool) { throw 'Windows SDK signtool.exe (x64) not found.' }
$pfx = Join-Path $env:RUNNER_TEMP ('aurenix-codesign-' + [guid]::NewGuid().ToString('N') + '.pfx')
try {
  [IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($env:AURENIX_CODESIGN_PFX_BASE64))
  $cert = [Security.Cryptography.X509Certificates.X509Certificate2]::new(
    $pfx, $env:AURENIX_CODESIGN_PFX_PASSWORD,
    [Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet)
  if (-not $cert.HasPrivateKey) { throw 'PFX has no private signing key.' }
  if ($cert.NotBefore -gt [DateTime]::UtcNow -or $cert.NotAfter -lt [DateTime]::UtcNow) {
    throw 'Code-signing certificate is not currently valid.'
  }
  $eku = $cert.Extensions | Where-Object { $_.Oid.Value -eq '2.5.29.37' } | Select-Object -First 1
  if (-not $eku -or -not (@($eku.EnhancedKeyUsages | ForEach-Object { $_.Value }) -contains '1.3.6.1.5.5.7.3.3')) {
    throw 'Certificate is not explicitly authorized for code signing.'
  }
  & $signtool sign /f $pfx /p $env:AURENIX_CODESIGN_PFX_PASSWORD /fd SHA256 /tr 'http://timestamp.digicert.com' /td SHA256 $File
  if ($LASTEXITCODE -ne 0) { throw 'Authenticode signing or trusted timestamp failed.' }
  & $signtool verify /pa /v $File
  if ($LASTEXITCODE -ne 0) { throw 'Authenticode chain verification failed.' }
  $signature = Get-AuthenticodeSignature -LiteralPath $File
  if ($signature.Status -ne 'Valid' -or -not $signature.SignerCertificate) {
    throw "Signature verification failed: $($signature.Status)"
  }
  if ($signature.SignerCertificate.Thumbprint -ne $cert.Thumbprint) {
    throw 'Unexpected certificate signer. Refusing release.'
  }
  if (-not $signature.TimeStamperCertificate) { throw 'Trusted timestamp missing.' }
  Write-Host ("SIGNED and VERIFIED: " + [IO.Path]::GetFileName($File))
} finally {
  if ($cert) { $cert.Dispose() }
  if (Test-Path -LiteralPath $pfx) { Remove-Item -LiteralPath $pfx -Force }
}
