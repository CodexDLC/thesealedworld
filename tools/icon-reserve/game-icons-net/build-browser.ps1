param(
    [string]$IconRoot = "transparent",
    [string]$Output = "browser.html"
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootPath = Join-Path $scriptRoot $IconRoot
$outputPath = Join-Path $scriptRoot $Output

if (-not (Test-Path -LiteralPath $rootPath)) {
    throw "Icon root not found: $rootPath"
}

function HtmlEncode([string]$value) {
    return [System.Net.WebUtility]::HtmlEncode($value)
}

$icons = Get-ChildItem -LiteralPath $rootPath -Recurse -File -Filter "*.svg" |
    Sort-Object DirectoryName, Name |
    ForEach-Object {
        $relative = [System.IO.Path]::GetRelativePath($scriptRoot, $_.FullName).Replace("\", "/")
        $author = [System.IO.Path]::GetRelativePath($rootPath, $_.DirectoryName).Split([char[]]@("/", "\"))[0]
        [PSCustomObject]@{
            Author = $author
            Name = $_.BaseName
            FileName = $_.Name
            RelativePath = $relative
        }
    }

$groups = $icons | Group-Object Author | Sort-Object Name
$total = $icons.Count
$generatedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$html = New-Object System.Collections.Generic.List[string]
$html.Add("<!doctype html>")
$html.Add("<html lang=""en"">")
$html.Add("<head>")
$html.Add("  <meta charset=""utf-8"">")
$html.Add("  <meta name=""viewport"" content=""width=device-width, initial-scale=1"">")
$html.Add("  <title>Game-icons.net Browser</title>")
$html.Add("  <style>")
$html.Add("    :root { color-scheme: dark; --bg: #08090a; --panel: #101316; --line: #253036; --text: #d7c8a4; --muted: #85765b; --accent: #ffaa00; --cyan: #00ffc8; --icon-filter: invert(76%) sepia(91%) saturate(999%) hue-rotate(358deg) brightness(101%) contrast(104%); }")
$html.Add("    * { box-sizing: border-box; }")
$html.Add("    body { margin: 0; background: var(--bg); color: var(--text); font-family: Segoe UI, Arial, sans-serif; }")
$html.Add("    header { position: sticky; top: 0; z-index: 3; padding: 14px 18px; background: rgba(8, 9, 10, .94); border-bottom: 1px solid var(--line); backdrop-filter: blur(8px); }")
$html.Add("    h1 { margin: 0 0 10px; font-size: 17px; font-weight: 600; letter-spacing: .04em; color: var(--accent); }")
$html.Add("    .toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }")
$html.Add("    input { width: min(520px, 100%); padding: 9px 11px; background: #070808; color: var(--text); border: 1px solid #3a463f; border-radius: 4px; outline: none; }")
$html.Add("    input:focus { border-color: rgba(0, 255, 200, .55); box-shadow: 0 0 0 2px rgba(0, 255, 200, .08); }")
$html.Add("    select { padding: 9px 10px; background: #070808; color: var(--text); border: 1px solid #3a463f; border-radius: 4px; outline: none; }")
$html.Add("    .meta { color: var(--muted); font-size: 12px; }")
$html.Add("    main { padding: 14px 18px 30px; }")
$html.Add("    details { margin: 0 0 10px; border: 1px solid var(--line); background: var(--panel); border-radius: 4px; }")
$html.Add("    summary { cursor: pointer; padding: 10px 12px; color: var(--accent); font-size: 14px; user-select: none; }")
$html.Add("    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(132px, 1fr)); gap: 9px; padding: 0 10px 12px; }")
$html.Add("    figure { margin: 0; min-width: 0; padding: 10px 7px 8px; background: #070808; border: 1px solid rgba(0, 255, 200, .13); border-radius: 3px; }")
$html.Add("    .thumb { display: flex; align-items: center; justify-content: center; height: 64px; margin-bottom: 7px; }")
$html.Add("    img { width: 50px; height: 50px; object-fit: contain; image-rendering: auto; filter: var(--icon-filter); }")
$html.Add("    figcaption { overflow-wrap: anywhere; color: var(--text); font-size: 10px; line-height: 1.25; text-align: center; }")
$html.Add("    .path { display: block; margin-top: 3px; color: var(--muted); font-size: 9px; }")
$html.Add("    .hidden { display: none; }")
$html.Add("  </style>")
$html.Add("</head>")
$html.Add("<body>")
$html.Add("  <header>")
$html.Add("    <h1>Game-icons.net SVG Browser</h1>")
$html.Add("    <div class=""toolbar"">")
$html.Add("      <input id=""search"" type=""search"" placeholder=""Search file, author, path: card, tool, sword, warning..."">")
$html.Add("      <select id=""tone"" aria-label=""Icon preview color"">")
$html.Add("        <option value=""gold"" selected>gold</option>")
$html.Add("        <option value=""parchment"">parchment</option>")
$html.Add("        <option value=""cyan"">cyan</option>")
$html.Add("        <option value=""white"">white</option>")
$html.Add("      </select>")
$html.Add("      <span class=""meta"">$total SVG files generated $generatedAt</span>")
$html.Add("    </div>")
$html.Add("  </header>")
$html.Add("  <main id=""icons"">")

foreach ($group in $groups) {
    $author = HtmlEncode($group.Name)
    $count = $group.Count
    $html.Add("    <details data-group=""$author"">")
    $html.Add("      <summary>$author ($count)</summary>")
    $html.Add("      <div class=""grid"">")

    foreach ($icon in $group.Group) {
        $name = HtmlEncode($icon.Name)
        $fileName = HtmlEncode($icon.FileName)
        $relativePath = HtmlEncode($icon.RelativePath)
        $searchText = HtmlEncode("$($icon.Author) $($icon.Name) $($icon.FileName) $($icon.RelativePath)")
        $html.Add("        <figure data-search=""$searchText"">")
        $html.Add("          <div class=""thumb""><img loading=""lazy"" src=""$relativePath"" alt=""""></div>")
        $html.Add("          <figcaption title=""$fileName"">$name<span class=""path"">$relativePath</span></figcaption>")
        $html.Add("        </figure>")
    }

    $html.Add("      </div>")
    $html.Add("    </details>")
}

$html.Add("  </main>")
$html.Add("  <script>")
$html.Add("    const input = document.getElementById('search');")
$html.Add("    const tone = document.getElementById('tone');")
$html.Add("    const details = [...document.querySelectorAll('details')];")
$html.Add("    const filters = {")
$html.Add("      gold: 'invert(76%) sepia(91%) saturate(999%) hue-rotate(358deg) brightness(101%) contrast(104%)',")
$html.Add("      parchment: 'invert(83%) sepia(17%) saturate(512%) hue-rotate(356deg) brightness(92%) contrast(86%)',")
$html.Add("      cyan: 'invert(86%) sepia(88%) saturate(1207%) hue-rotate(98deg) brightness(105%) contrast(104%)',")
$html.Add("      white: 'none'")
$html.Add("    };")
$html.Add("    tone.addEventListener('change', () => document.documentElement.style.setProperty('--icon-filter', filters[tone.value] || filters.gold));")
$html.Add("    input.addEventListener('input', () => {")
$html.Add("      const q = input.value.trim().toLowerCase();")
$html.Add("      for (const group of details) {")
$html.Add("        let visible = 0;")
$html.Add("        for (const fig of group.querySelectorAll('figure')) {")
$html.Add("          const match = !q || fig.dataset.search.toLowerCase().includes(q);")
$html.Add("          fig.classList.toggle('hidden', !match);")
$html.Add("          if (match) visible++;")
$html.Add("        }")
$html.Add("        group.classList.toggle('hidden', visible === 0);")
$html.Add("        if (q && visible > 0) group.open = true;")
$html.Add("      }")
$html.Add("    });")
$html.Add("  </script>")
$html.Add("</body>")
$html.Add("</html>")

Set-Content -LiteralPath $outputPath -Value $html -Encoding UTF8
Write-Output "Generated $outputPath with $total SVG files."
