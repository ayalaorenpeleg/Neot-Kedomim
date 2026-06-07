$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add('http://localhost:3000/')
$listener.Start()
Write-Host "Server running at http://localhost:3000/"
while ($true) {
    $ctx   = $listener.GetContext()
    $local = $ctx.Request.Url.LocalPath.TrimStart('/')
    if ($local -eq '' -or $local -eq '/') { $local = 'Neot_Kedumim_GIS_Desktop.html' }
    $file  = Join-Path 'C:\Ayala Projects\Neot Kdomim' $local
    if (Test-Path $file) {
        $ext = [System.IO.Path]::GetExtension($file).ToLower()
        $mime = switch ($ext) {
            '.html' { 'text/html; charset=utf-8' }
            '.js'   { 'application/javascript' }
            '.css'  { 'text/css' }
            '.png'  { 'image/png' }
            '.json' { 'application/json' }
            default { 'application/octet-stream' }
        }
        $bytes = [System.IO.File]::ReadAllBytes($file)
        $ctx.Response.ContentType   = $mime
        $ctx.Response.ContentLength64 = $bytes.Length
        $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
        $ctx.Response.StatusCode = 404
    }
    $ctx.Response.OutputStream.Close()
}
