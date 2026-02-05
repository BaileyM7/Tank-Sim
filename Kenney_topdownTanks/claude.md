# Kenney Top-Down Tanks — Asset Reference

CC0 licensed asset pack by Kenney Vleugels (kenney.nl). All assets are top-down perspective for 2D tank/shooter games.

---

## Directory Structure

```
Kenney_topdownTanks/
├── PNG/
│   ├── Bullets/      (24 files) — projectiles
│   ├── Environment/  (5 files)  — ground tiles, trees
│   ├── Obstacles/    (11 files) — barrels, sandbags, oil
│   ├── Smoke/        (24 files) — smoke/explosion puff frames
│   └── Tanks/        (22 files) — tank bodies, gun barrels, tracks
├── Spritesheet/
│   ├── sheet_tanks.png          — combined spritesheet
│   └── sheet_tanks.xml          — sprite coordinates & sizes
├── Vector/
│   ├── vector_tanks.svg
│   └── vector_tanks.swf
├── license.txt
├── preview.png
└── sample.png
```

---

## Tank Composition

A complete tank is assembled from **3 separate sprites layered together**:

```
Layer 3 (top):    Barrel/Gun    — narrow cannon, extends from turret center
Layer 2 (middle): Tank Body     — colored chassis with turret mount circle
Layer 1 (bottom): Tracks        — tread marks left on the ground
```

- The **tank body** has dark grey/brown track treads visible on its left and right sides and a circular turret mount in the center.
- The **barrel** is a narrow vertical rectangle that anchors at the turret mount and extends upward. It can rotate independently of the body.
- **Tracks** are decorative tread marks (grey horizontal stripes) rendered beneath the tank.

### Available Tank Colors

| Color | Body | Barrel | Body Outline | Barrel Outline |
|-------|------|--------|-------------|----------------|
| Beige | `tankBeige.png` | `barrelBeige.png` | `tankBeige_outline.png` | `barrelBeige_outline.png` |
| Black | `tankBlack.png` | `barrelBlack.png` | `tankBlack_outline.png` | `barrelBlack_outline.png` |
| Blue  | `tankBlue.png`  | `barrelBlue.png`  | `tankBlue_outline.png`  | `barrelBlue_outline.png`  |
| Green | `tankGreen.png` | `barrelGreen.png` | `tankGreen_outline.png` | `barrelGreen_outline.png` |
| Red   | `tankRed.png`   | `barrelRed.png`   | `tankRed_outline.png`   | `barrelRed_outline.png`   |

All tank files are in `PNG/Tanks/`.

### Tracks (also in PNG/Tanks/)

| File | Size |
|------|------|
| `tracksLarge.png` | 82 x 104 |
| `tracksSmall.png` | 74 x 104 |

---

## Bullets

Located in `PNG/Bullets/`. Each of the 6 base colors has 4 variants:

| Variant | Pattern | Description |
|---------|---------|-------------|
| Solid | `bullet[Color].png` | Single-color projectile |
| Silver-tipped | `bullet[Color]Silver.png` | Two-tone with silver casing/tip |
| Solid outline | `bullet[Color]_outline.png` | Outlined single-color |
| Silver-tipped outline | `bullet[Color]Silver_outline.png` | Outlined two-tone |

### Bullet Colors

Beige, Blue, Green, Red, Silver, Yellow

**Note**: Tanks only come in 5 colors (Beige, Black, Blue, Green, Red). Bullets add Silver and Yellow but lack Black. Bullet colors don't map 1:1 to tank colors.

### Full Bullet File List

| Color | Solid | Silver-tipped | Solid Outline | Silver Outline |
|-------|-------|---------------|---------------|----------------|
| Beige | `bulletBeige.png` | `bulletBeigeSilver.png` | `bulletBeige_outline.png` | `bulletBeigeSilver_outline.png` |
| Blue | `bulletBlue.png` | `bulletBlueSilver.png` | `bulletBlue_outline.png` | `bulletBlueSilver_outline.png` |
| Green | `bulletGreen.png` | `bulletGreenSilver.png` | `bulletGreen_outline.png` | `bulletGreenSilver_outline.png` |
| Red | `bulletRed.png` | `bulletRedSilver.png` | `bulletRed_outline.png` | `bulletRedSilver_outline.png` |
| Silver | `bulletSilver.png` | `bulletSilverSilver.png` | `bulletSilver_outline.png` | `bulletSilverSilver_outline.png` |
| Yellow | `bulletYellow.png` | `bulletYellowSilver.png` | `bulletYellow_outline.png` | `bulletYellowSilver_outline.png` |

---

## Smoke / Explosion Effects

Located in `PNG/Smoke/`. 4 colors, 6 frames each (0-5).

**Pattern**: `smoke[Color][0-5].png`

### Smoke Colors and Suggested Use

| Color | Files | Suggested Use |
|-------|-------|---------------|
| Grey | `smokeGrey0.png` - `smokeGrey5.png` | Neutral smoke, engine exhaust |
| Orange | `smokeOrange0.png` - `smokeOrange5.png` | Fire, explosions |
| White | `smokeWhite0.png` - `smokeWhite5.png` | Steam, muzzle flash |
| Yellow | `smokeYellow0.png` - `smokeYellow5.png` | Chemical, flash effects |

### Frame Details

The 6 frames are **varied cloud shapes**, not a strict dissipation sequence. They include:
- Solid puffy clouds (frames 0, 2, 3, 5)
- Ring/donut shapes with hollow centers (frames 1, 4)

These can be used as a sequential animation OR picked randomly for visual variety.

---

## Obstacles

Located in `PNG/Obstacles/`.

### Barrel Obstacles (not gun barrels)

Cylindrical containers viewable from top-down or side perspective.

| Color | Top-down | Side | Side Damaged |
|-------|----------|------|-------------|
| Green | `barrelGreen_up.png` | `barrelGreen_side.png` | `barrelGreen_side_damaged.png` |
| Grey | `barrelGrey_up.png` | `barrelGrey_side.png` | `barrelGrey_sde_rust.png` * |
| Red | `barrelRed_up.png` | `barrelRed_side.png` | — |

\* **Typo in original pack**: `barrelGrey_sde_rust.png` uses "sde" instead of "side". This is the original filename from Kenney — do not rename.

### Other Obstacles

| File | Description |
|------|-------------|
| `sandbagBeige.png` | Light-colored sandbag barrier |
| `sandbagBrown.png` | Dark-colored sandbag barrier |
| `oil.png` | Dark circular oil spill/puddle |

---

## Environment

Located in `PNG/Environment/`.

### Ground Tiles (128 x 128, tileable)

| File | Description |
|------|-------------|
| `grass.png` | Bright green grass |
| `dirt.png` | Brown earth |
| `sand.png` | Light beige sand |

### Trees

| File | Size | Description |
|------|------|-------------|
| `treeLarge.png` | 98 x 107 | Large green tree canopy |
| `treeSmall.png` | 87 x 87 | Small green tree/bush |

---

## Size Reference (from sheet_tanks.xml)

All dimensions in pixels (width x height).

### Tanks

| Asset | Regular | Outline |
|-------|---------|---------|
| Tank body | 75 x 70 | 83 x 78 |
| Gun barrel | 16 x 50 | 24 x 58 |
| Tracks (large) | 82 x 104 | — |
| Tracks (small) | 74 x 104 | — |

### Bullets

| Variant | Size |
|---------|------|
| Solid / Silver-tipped | 12 x 26 |
| Outline variants | 20 x 34 |

### Obstacles

| Asset | Size |
|-------|------|
| Barrel (top-down / `_up`) | 48 x 48 |
| Barrel (side view) | 44 x 62 |
| Sandbag | 66 x 44 |
| Oil spill | 96 x 96 |

### Environment

| Asset | Size |
|-------|------|
| Ground tiles (dirt, grass, sand) | 128 x 128 |
| Tree large | 98 x 107 |
| Tree small | 87 x 87 |

### Smoke Frames (approximate, varies per frame)

| Dimension | Range |
|-----------|-------|
| Width | 79 - 100 |
| Height | 79 - 107 |

---

## Naming Convention Patterns

```
Tank bodies:      tank[Color].png              tank[Color]_outline.png
Gun barrels:      barrel[Color].png            barrel[Color]_outline.png
Bullets:          bullet[Color].png            bullet[Color]_outline.png
                  bullet[Color]Silver.png      bullet[Color]Silver_outline.png
Smoke:            smoke[Color][0-5].png
Obstacle barrels: barrel[Color]_up.png         barrel[Color]_side.png
                  barrel[Color]_side_damaged.png
Sandbags:         sandbag[Color].png
Tracks:           tracks[Large|Small].png
```

### Outline Variant Rule

Every tank body, gun barrel, and bullet has a `_outline` counterpart. The outline version is **~8px larger** in each dimension and adds a visible border. Use for selection highlights or UI emphasis.

---

## Color Availability Matrix

| Color  | Tank Body | Gun Barrel | Bullet | Smoke | Obstacle Barrel | Sandbag |
|--------|-----------|------------|--------|-------|-----------------|---------|
| Beige  | Y | Y | Y | — | — | Y |
| Black  | Y | Y | — | — | — | — |
| Blue   | Y | Y | Y | — | — | — |
| Brown  | — | — | — | — | — | Y |
| Green  | Y | Y | Y | — | Y | — |
| Grey   | — | — | — | Y | Y | — |
| Orange | — | — | — | Y | — | — |
| Red    | Y | Y | Y | — | Y | — |
| Silver | — | — | Y | — | — | — |
| White  | — | — | — | Y | — | — |
| Yellow | — | — | Y | Y | — | — |

---

## Spritesheet

`Spritesheet/sheet_tanks.png` contains all sprites packed into a single image. `Spritesheet/sheet_tanks.xml` maps each sprite name to its `x, y, width, height` coordinates within the sheet. The XML references `imagePath="sheet.png"` (the spritesheet image).

---

## Quick Reference by Use-Case

**"I need a complete tank"**
→ Pick a color. Load `tank[Color].png` + `barrel[Color].png` + `tracksLarge.png` (or `tracksSmall.png`). Layer: tracks, body, barrel.

**"I need matching bullets for a tank"**
→ Use `bullet[Color].png` matching the tank color. Black tanks have no matching bullet — use Silver or any neutral color.

**"I need an explosion effect"**
→ Use `smokeOrange[0-5].png` frames. For muzzle flash, use `smokeWhite` or `smokeYellow`.

**"I need destructible obstacles"**
→ Use `barrel[Color]_side.png` and swap to `barrel[Color]_side_damaged.png` when hit. Green and Grey have damaged variants; Red does not.

**"I need ground terrain"**
→ Tile `grass.png`, `dirt.png`, and/or `sand.png` (all 128x128). Add `treeLarge.png` and `treeSmall.png` for decoration.

**"I need to highlight a selected unit"**
→ Swap regular sprites for their `_outline` counterparts (e.g., `tankBlue.png` → `tankBlue_outline.png`).
