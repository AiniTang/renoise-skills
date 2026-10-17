# style-catalog · 风格目录片示例（YouWare · 四种商用风格，54s）

组件：`src/cinematic/catalog/`（目录片模板）、`variety/`（综艺花字）、`sticker/`（贴纸风）、`iso/`（等轴 2.5D）；第四格复用 `examples/youware-ladder/YouWareChain.tsx`。规则见 `references/style-pack-05.md`。

用法：把本目录复制到工程 `src/lab/`（`MorphDemo`/`Reel` 里的 `../youware-ladder/YouWareChain` 改成你放 YouWareChain 的位置），在 `Root.tsx` 用 `LabFonts` 包一层注册：`Variety` `Stickers` `Iso` `Morph`（各 330 帧）和 `StyleReel`（`REEL_LEN`）。

步骤：
1. 素材放 `public/`：`clips/finance-deck.mp4`（YouWare 官方演示录屏）、`site/capability-*.png` `site/agent-*.png` `site/hero-team.png`（官网图）、`brand/mark.svg` `brand/lockup.svg`（品牌 2.0）。
2. 字体：`fonts.py fetch bricolage-grotesque figtree zcool-qingke mochiy-pop-one hepta-slab manrope noto-serif-sc noto-sans-sc caveat geist-mono --to <工程>`，文案定稿后 `fonts.py subset <工程> --text-file copy.txt`。
3. **先把四个样片渲成视频**：`npx remotion render src/index.ts Variety public/samples/variety.mp4 --muted`（Stickers / Iso / Morph 同理），目录片读 `video:` 播放；Three.js 样片不能直接放进缩放窗口（见 style-pack-05 的坑）。
4. `npx remotion render src/index.ts StyleReel out/reel-raw.mp4 --muted` + `… out/mix.wav --codec=wav --config=remotion.audio.config.ts` → `rn finish out/reel-raw.mp4 -o out/reel.mp4 --audio out/mix.wav` → `rn qa out/reel.mp4`、`rn cuts out/reel.mp4 --sheet out/audit/cuts.jpg`。


## 十五种商用风格（Reel15，175s）

新增样片：`HandDemo`（逐帧手绘）`LineDemo`（一笔画）`CollageDemo`（拼贴）`FlatDemo`（扁平插画）`BauhausDemo`（包豪斯）`LiquidDemo`（液态）`GlassDemo`（弥散玻璃）`SoftDemo`（3D 软萌针阵）`FuiDemo`（赛博 HUD）`PixelDemo`（像素）`SynthwaveDemo`（合成波），各 330 帧；`markPath.ts` 是 YouWare 标志路径（含四边 `MARK_SIDES`）。规则见 `references/style-pack-06.md`。

1. 额外字体：`fonts.py fetch unbounded anton dm-serif-display fredoka --to <工程>`；信息卡文案定稿后重新 `fonts.py subset`。
2. 全部 15 个样片先渲成 `public/samples/<name>.mp4`（`--muted`），再给片尾墙做代理：`ffmpeg -i samples/x.mp4 -an -vf scale=640:360 -crf 20 -g 6 samples/wall/x.mp4`（`Reel15` 自动读 `samples/wall/`）。
3. 配乐：`tools/` 放进工程根目录，`python3 tools/build_audio.py <曲库曲.mp3> --need 138` → `public/music/base.wav`（重复 N 小节，保证第 13 格前还在主段）、`ending.wav`（收尾重音前 2 小节 + 重音 + 尾音）、`retro-hud/chip/synth.wav` 和 `public/sfx/chip-*.wav`；把输出的 `ending_len` / `hit_offset_in_ending` 填进 `Reel15.tsx` 的 `END_LEN` / `HIT_OFFSET`（重音落在片尾标语升起那一帧）。
4. 注册 `StyleReel15`（`REEL15_LEN`），`npx remotion render … --timeout=120000`（画面 `--muted`，混音另渲 WAV）→ `rn finish --audio` → `rn qa` / `rn cuts`。
