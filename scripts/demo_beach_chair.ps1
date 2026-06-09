#requires -Version 7
# Build a beach chair (cadeira de praia) via the BlenderAgent MCP HTTP endpoints.
# Frame = wood (brown), fabric = orange canvas, on a sand-colored ground plane.

$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:9877"

function Post {
    param([string]$Path, [hashtable]$Body = @{})
    $json = $Body | ConvertTo-Json -Depth 10 -Compress
    $r = curl.exe -s -X POST "$base$Path" -H "Content-Type: application/json" -d $json
    $obj = $r | ConvertFrom-Json
    if (-not $obj.ok) {
        Write-Host "FAIL $Path -> $r" -ForegroundColor Red
        throw "POST $Path failed: $($obj.message)"
    }
    return $obj
}

function MakeMaterial {
    param([string]$Name, [double[]]$Rgb, [double]$Roughness = 0.6)
    Post "/material/create" @{name=$Name; useNodes=$true} | Out-Null
    Post "/shader_node/set_input_value" @{
        materialName = $Name
        nodeName     = "Principled BSDF"
        socketName   = "Base Color"
        value        = @($Rgb[0], $Rgb[1], $Rgb[2], 1.0)
    } | Out-Null
    Post "/shader_node/set_input_value" @{
        materialName = $Name
        nodeName     = "Principled BSDF"
        socketName   = "Roughness"
        value        = $Roughness
    } | Out-Null
}

function SetMat { param([string]$Obj, [string]$Mat)
    Post "/material/assign_to_object" @{objectName=$Obj; materialName=$Mat} | Out-Null
}

# ---------------------------------------------------------------------------
# Clean slate
# ---------------------------------------------------------------------------
Write-Host "=== Clean slate ===" -ForegroundColor Cyan
Post "/file/new" @{empty=$true} | Out-Null

# ---------------------------------------------------------------------------
# World (sky)
# ---------------------------------------------------------------------------
Write-Host "=== World ===" -ForegroundColor Cyan
Post "/world/create" @{name="Sky"} | Out-Null
Post "/world/assign_to_scene" @{worldName="Sky"} | Out-Null
Post "/shader_node/set_input_value" @{
    worldName="Sky"; nodeName="Background"; socketName="Color"
    value=@(0.45, 0.70, 0.95, 1.0)
} | Out-Null
Post "/shader_node/set_input_value" @{
    worldName="Sky"; nodeName="Background"; socketName="Strength"
    value=1.2
} | Out-Null

# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------
Write-Host "=== Materials ===" -ForegroundColor Cyan
MakeMaterial "Wood"   @(0.55, 0.30, 0.12) 0.7   # warm brown
MakeMaterial "Canvas" @(0.95, 0.30, 0.10) 0.85  # bright orange
MakeMaterial "Sand"   @(0.92, 0.82, 0.58) 1.0   # pale sand

# ---------------------------------------------------------------------------
# Ground plane (sand)
# ---------------------------------------------------------------------------
Write-Host "=== Ground ===" -ForegroundColor Cyan
Post "/object/create" @{type="PLANE"; name="Sand"; size=8.0; location=@(0,0,0)} | Out-Null
SetMat "Sand" "Sand"

# ---------------------------------------------------------------------------
# Frame (Wood)
# Chair dimensions: 0.6m wide (X), 0.55m deep (Y), seat at z=0.40, back to z=0.95
# ---------------------------------------------------------------------------
Write-Host "=== Wooden frame ===" -ForegroundColor Cyan

# 4 legs — vertical cylinders, 0.40m tall, radius 0.018
$legs = @(
    @{ name="LegFL"; x=-0.27; y=-0.22 }
    @{ name="LegFR"; x= 0.27; y=-0.22 }
    @{ name="LegBL"; x=-0.27; y= 0.22 }
    @{ name="LegBR"; x= 0.27; y= 0.22 }
)
foreach ($l in $legs) {
    Post "/object/create" @{
        type="CYLINDER"; name=$l.name; size=0.036
        location=@($l.x, $l.y, 0.20)
        scale=@(1, 1, 0.20)   # cylinder default height 2 -> 0.40m
    } | Out-Null
    SetMat $l.name "Wood"
}

# 2 side rails — horizontal cylinders along Y, at seat height
$rails = @(
    @{ name="RailL"; x=-0.27 }
    @{ name="RailR"; x= 0.27 }
)
foreach ($r in $rails) {
    Post "/object/create" @{
        type="CYLINDER"; name=$r.name; size=0.030
        location=@($r.x, 0.0, 0.40)
        rotation=@(1.5708, 0, 0)   # 90deg X -> cylinder axis now along Y
        scale=@(1, 1, 0.25)        # 0.50m long
    } | Out-Null
    SetMat $r.name "Wood"
}

# 2 armrests — flat cubes on top of the side rails
$arms = @(
    @{ name="ArmL"; x=-0.27 }
    @{ name="ArmR"; x= 0.27 }
)
foreach ($a in $arms) {
    Post "/object/create" @{
        type="CUBE"; name=$a.name; size=1.0
        location=@($a.x, 0.0, 0.45)
        scale=@(0.03, 0.30, 0.015)
    } | Out-Null
    SetMat $a.name "Wood"
}

# 2 back posts — vertical cylinders extending from back legs upward
$posts = @(
    @{ name="PostL"; x=-0.27 }
    @{ name="PostR"; x= 0.27 }
)
foreach ($p in $posts) {
    Post "/object/create" @{
        type="CYLINDER"; name=$p.name; size=0.036
        location=@($p.x, 0.22, 0.70)
        scale=@(1, 1, 0.30)   # 0.60m tall, top at z=1.0
    } | Out-Null
    SetMat $p.name "Wood"
}

# Top crossbar of the back — horizontal cylinder along X
Post "/object/create" @{
    type="CYLINDER"; name="CrossTop"; size=0.030
    location=@(0, 0.22, 1.00)
    rotation=@(0, 1.5708, 0)   # 90deg Y -> cylinder axis along X
    scale=@(1, 1, 0.30)        # 0.60m wide
} | Out-Null
SetMat "CrossTop" "Wood"

# Front crossbar between front legs
Post "/object/create" @{
    type="CYLINDER"; name="CrossFront"; size=0.030
    location=@(0, -0.22, 0.05)
    rotation=@(0, 1.5708, 0)
    scale=@(1, 1, 0.27)
} | Out-Null
SetMat "CrossFront" "Wood"

# ---------------------------------------------------------------------------
# Fabric (Canvas)
# ---------------------------------------------------------------------------
Write-Host "=== Canvas fabric ===" -ForegroundColor Cyan

# Seat — horizontal plate spanning between the rails, sitting on top of them
Post "/object/create" @{
    type="CUBE"; name="Seat"; size=1.0
    location=@(0, 0, 0.455)
    scale=@(0.26, 0.24, 0.015)
} | Out-Null
SetMat "Seat" "Canvas"

# Back — tilted plate leaning slightly back, between the two back posts
# rotation_x = 1.40 rad (~80 deg) gives mostly vertical with small lean
Post "/object/create" @{
    type="CUBE"; name="Back"; size=1.0
    location=@(0, 0.245, 0.73)
    rotation=@(1.40, 0, 0)
    scale=@(0.26, 0.26, 0.012)
} | Out-Null
SetMat "Back" "Canvas"

# ---------------------------------------------------------------------------
# Lighting
# ---------------------------------------------------------------------------
Write-Host "=== Lighting ===" -ForegroundColor Cyan
Post "/light/create" @{
    type="SUN"; name="Sun"
    location=@(2, -2, 4); rotation=@(0.7, 0.3, -0.5)
} | Out-Null

# ---------------------------------------------------------------------------
# Camera — 3/4 view from front-left
# ---------------------------------------------------------------------------
Write-Host "=== Camera ===" -ForegroundColor Cyan
Post "/camera/create" @{
    name="Cam"
    location=@(1.5, -1.5, 0.85)
    rotation=@(1.25, 0, 0.78)
} | Out-Null
Post "/camera/set_active" @{cameraName="Cam"} | Out-Null

Write-Host "`n=== Beach chair built ===" -ForegroundColor Green
$objs = (curl.exe -s -X POST "$base/object/list" -H "Content-Type: application/json" -d "{}" | ConvertFrom-Json).data
Write-Host "Total objects in scene: $($objs.objectCount)"
$objs.objects | Format-Table name, type
