# Create numbered image files from existing JPG assets
$sourceDir = "public\assets"
$jpgFiles = @(
    @{src="01freedom.jpg"; dest="01.png"},
    @{src="02power_lukso.jpg"; dest="02.png"},
    @{src="03power_lukso.jpg"; dest="03.png"},
    @{src="04power_lukso.jpg"; dest="04.png"},
    @{src="05power_lukso.jpg"; dest="05.png"},
    @{src="06freedom_lukso.jpg"; dest="06.png"},
    @{src="07power_lukso.jpg"; dest="07.png"},
    @{src="08freedom_lukso.jpg"; dest="08.png"},
    @{src="09freedom_lukso.jpg"; dest="09.png"},
    @{src="10power_lukso.jpg"; dest="10.png"},
    @{src="11freedom_lukso.jpg"; dest="11.png"},
    @{src="12freedom_lukso.jpg"; dest="12.png"}
)

Write-Host "🎨 Creating numbered background images..."

foreach ($file in $jpgFiles) {
    $sourcePath = Join-Path $sourceDir $file.src
    $destPath = Join-Path $sourceDir $file.dest
    
    if (Test-Path $sourcePath) {
        Copy-Item $sourcePath $destPath -Force
        Write-Host "✅ Created $($file.dest) from $($file.src)"
    } else {
        Write-Host "⚠️ Source file not found: $($file.src)"
    }
}

Write-Host "🎉 Background images ready for Upix game!"