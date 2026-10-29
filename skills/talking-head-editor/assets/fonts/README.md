# Skill 用的字体

全部是 SIL Open Font License 1.1 授权，可以免费商用。字体文件不随仓库分发：`fonts.json` 记着每款字体在发布方的下载地址、大小和 sha256，第一次渲染时 `scripts/fonts.py` 下载到 `~/.cache/koubo/fonts/`，核对通过才用，授权原文（在 `licenses/`）一起复制过去。不要修改或裁剪字体文件，改了就要按 OFL 换掉保留字体名。

| 文件 | 字体 | 在 Skill 里的角色 |
|---|---|---|
| SourceHanSansCN-Medium.otf | 思源黑体 Medium | 高级感口播字幕、说明小字 |
| SourceHanSansCN-Bold.otf | 思源黑体 Bold | 重点句字幕 |
| SourceHanSansCN-Heavy.otf | 思源黑体 Heavy | 关键词大字（横向压窄到 82%，做出窄长标题黑的感觉） |
| SourceHanSerifCN-Heavy.otf / Bold.otf | 思源宋体 | 金句、杂志感标题 |
| MaShanZheng-Regular.ttf | 马善政毛笔楷书 | 书法大字点缀 |
| ZhiMangXing-Regular.ttf | 志莽行书 | 手写批注（「划重点」「第一个坑」） |
| DouyinSansBold.ttf | 抖音美好体 | 综艺感字幕和标题 |
| ZCOOLQingKeHuangYou-Regular.ttf | 站酷庆科黄油体 | 综艺感关键词大字 |
| ZCOOLKuaiLe-Regular.ttf | 站酷快乐体 | 综艺感花字 |
| SmileySans-Oblique.ttf | 得意黑 | 综艺感标题 |
| Anton-Regular.ttf | Anton | 英文大字、章节号、数字 |
| Oswald-SemiBold.ttf / Bold.ttf | Oswald | 英文小标、拼音标注 |
| InstrumentSerif-Regular.ttf / Italic.ttf | Instrument Serif | 英文衬线副标（斜体最常用） |
| BodoniModa-Black.ttf / BoldItalic.ttf | Bodoni Moda | 杂志感英文大字 |
| DMSerifDisplay-Regular.ttf / Italic.ttf | DM Serif Display | 英文金句 |
| CormorantGaramond-SemiBold.ttf / MediumItalic.ttf | Cormorant Garamond | 优雅细衬线点缀 |
| GreatVibes-Regular.ttf | Great Vibes | 英文花体点缀 |
| MrsSaintDelafield-Regular.ttf | Mrs Saint Delafield | 签名感英文点缀 |
| BebasNeue-Regular.ttf | Bebas Neue | 英文窄体（全大写） |
| Montserrat-SemiBold.ttf / ExtraBold.ttf | Montserrat | 综艺感英文 |

不能打包、用户可以自己安装的字体：优设标题黑、站酷高端黑、阿里妈妈东方大楷、MiSans、阿里巴巴普惠体、庞门正道标题体。它们写着免费商用，但授权不允许再分发。用户装好后写进 timeline 的 `fonts` 就能用。

抖音美好体、站酷快乐体只收了 6763 个常用字，遇到生僻字会缺字，渲染时会回退到思源黑体。
