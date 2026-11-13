# Generates original, simple paw artwork for Android's monochrome small icon.
Add-Type -AssemblyName System.Drawing
$canvas = [System.Drawing.Bitmap]::new(96, 96)
$graphics = [System.Drawing.Graphics]::FromImage($canvas)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.Clear([System.Drawing.Color]::Transparent)
$white = [System.Drawing.Brushes]::White
$graphics.FillEllipse($white, 14, 30, 17, 23)
$graphics.FillEllipse($white, 30, 15, 17, 25)
$graphics.FillEllipse($white, 51, 15, 17, 25)
$graphics.FillEllipse($white, 67, 30, 17, 23)
$pad = [System.Drawing.Drawing2D.GraphicsPath]::new()
$pad.AddBezier(48, 43, 36, 43, 32, 54, 24, 64)
$pad.AddBezier(24, 64, 13, 81, 33, 84, 48, 77)
$pad.AddBezier(48, 77, 63, 84, 83, 81, 72, 64)
$pad.AddBezier(72, 64, 64, 54, 60, 43, 48, 43)
$pad.CloseFigure()
$graphics.FillPath($white, $pad)
$target = Join-Path $PSScriptRoot '..\mobile\assets\notification-icon.png'
$canvas.Save($target, [System.Drawing.Imaging.ImageFormat]::Png)
$pad.Dispose()
$graphics.Dispose()
$canvas.Dispose()
