# svg-compare · 模型输出对比片（YouWare × GPT-6 Sol vs GPT-6.1 Sol，12 秒）

两个模型对同一提示词给出的**动画 SVG**，原样、逐帧确定地并排播放，套 YouWare 的设计元素（输入框、模型菜单、结果窗口），结尾钩子引到 youware.com。规则与坑见 `references/svg-compare.md`。Remotion id `PelicanCompare`。

用法：
1. 以任意 promo-video 工程为底（需要 `src/cinematic/{motion.ts,sfx.tsx,type/,spring.ts}` 和 public/sfx、public/brand、DM Sans / Hepta Slab / Manrope 字体）。把 `src/` 放进 `src/pel/`，`op/` 放进 `src/op/`，`tools/` 放到工程根目录。
2. 两个 SVG 放 `public/svg/`，改 `tools/prep_svgs.py` 里的文件名与前缀，运行它 → 生成 `src/pel/svgs.ts`（命名隔离、`<use>` 展开、缩放包裹组、CSS 动画改为暂停 + 负延迟）。
3. `python3 tools/build_music.py` → `public/music/bgm.wav`（曲库曲从首个强拍开始，第 4 小节接到原曲收尾和弦前一小节，和弦落在第 5 小节）。
4. 改 `Film.tsx` 顶部的 MODEL_A / MODEL_B / EFFORT / PROMPT 和 `Menu.tsx` 的 MENU_ROWS（照最新的 YouWare 模型菜单截图）。
5. 注册 `PelicanCompare`（360 帧，外包 LabFonts），`render --scale=2 --timeout=180000 --muted` + WAV 混音 → `rn finish --audio` → `rn qa` / `rn cuts`。
6. `ScarfTest` / `RaysTest` 是校验用组合：换了 SVG 或 viewBox 做法后跑一遍，像素差应为 0。
