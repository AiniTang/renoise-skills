"""画布基础回归：python3 -m unittest discover -s evals -p 'test_*.py'。

会用 FFmpeg 生成小素材，验证粗剪到时间线的画布传递、圆形裁切和素材卡的真实输出。
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from kvlib import canvas_for_source, canvas_size, pip_clip, pip_params, probe, style_preset, unit
from render import prep_broll
from check_media import check
from PIL import Image


class CanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='koubo_canvas_', dir=ROOT / 'evals')
        cls.work = Path(cls.tmp.name)
        cls.src = cls.work / 'source.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        'color=red:s=320x180:r=30:d=0.5,drawbox=x=0:y=0:w=32:h=180:color=blue:t=fill',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.5', '-c:v', 'libx264', '-c:a', 'aac', str(cls.src)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def cli(self, name, *args):
        subprocess.run([sys.executable, str(ROOT / 'scripts' / (name + '.py')), *map(str, args)],
                       check=True, capture_output=True)

    def test_portrait_scale_and_presets(self):
        for w, h in ((1080, 1920), (540, 960), (720, 1280)):
            self.assertEqual(unit(w, h), w / 1080)
        st = style_preset({})
        self.assertEqual(st['sub']['base']['y'], 0.80)
        self.assertEqual(pip_params({}, st)['d'], 0.30)

    def test_canvas_validation(self):
        for bad in ('0x1080', '1921x1080', '-2x1080', '1920:1080'):
            with self.assertRaises(ValueError):
                canvas_size(bad)
        self.assertEqual(canvas_for_source(self.src)['w'], 1920)
        self.assertEqual(canvas_for_source(self.src, '1080x1920')['h'], 1920)

    def test_pip_inside_frame(self):
        for W, H in ((1920, 1080), (960, 540), (2560, 1080)):
            st = style_preset({'canvas': dict(w=W, h=H)})
            for pos in (None, 'top_left', 'top_right', 'bottom_left', 'bottom_right', 'center'):
                p = pip_params(dict(pos=pos), st)
                r = W * p['d'] / 2 + p['border'] * unit(W, H)
                self.assertGreaterEqual(W * p['x'] - r, 0)
                self.assertLessEqual(W * p['x'] + r, W)
                self.assertGreaterEqual(H * p['y'] - r, 0)
                self.assertLessEqual(H * p['y'] + r, H)

    def test_orientation_warning_only_for_requested_mismatch(self):
        for cv in (None, (1920, 1080)):
            issues = check(self.src, 'broll', cv)['issues']
            self.assertFalse(any('方向' in x for x in issues))
        self.assertTrue(any('方向' in x for x in check(self.src, 'broll', (1080, 1920))['issues']))

    def test_real_pip_crop_all_directions(self):
        for W, H in ((320, 180), (180, 320), (180, 180)):
            for crop in (None, dict(x=-0.2, y=1.2, s=2)):
                out = self.work / f'pip{W}_{H}_{crop is None}.mov'
                pip_clip(self.src, 0, 0.1, W, H, 30, 80, crop, 2, '#FFFFFF', out)
                info = probe(out)
                self.assertEqual((info['w'], info['h']), (84, 84))
                self.assertTrue(info['alpha'])

    def test_tall_card_and_video_stay_in_landscape(self):
        src = self.work / 'tall.png'
        Image.new('RGB', (200, 1000), 'blue').save(src)
        W, H = 960, 540
        st = style_preset({'canvas': dict(w=W, h=H)})
        for i, (path, fit) in enumerate(((src, 'contain'), (src, 'card'), (self.src, 'card'), (src, 'tilt'))):
            _, w, h, _, _ = prep_broll(i, dict(src=str(path), fit=fit, tilt='pair', srcs=[str(src)] * 3, t0=0, t1=0.1), W, H, 30, st, self.work, True)
            pad = 2 * st['card']['shadow'] if fit == 'card' and path == src else 0
            self.assertLessEqual(w - pad, W * 0.62 + 1)
            self.assertLessEqual(h - pad, H * 0.72 + 1)

    def test_background_and_graphic_canvas_flags(self):
        bg, graphic = self.work / 'bg.png', self.work / 'graphic.mov'
        self.cli('backgrounds', 'grid', '--canvas', '640x360', '-o', bg)
        self.assertEqual(Image.open(bg).size, (640, 360))
        self.cli('make_graphic', '{"type":"number","value":3,"dur":0.1}', '--canvas', '640x360', '-o', graphic)
        info = probe(graphic)
        self.assertEqual((info['w'], info['h']), (640, 360))

    def test_pipeline_infers_and_preserves_canvas(self):
        tr = self.work / 'transcript.json'
        tr.write_text(json.dumps(dict(files=[dict(src='source.mp4', islands=[dict(t0=0.08, t1=0.3, text='测试横屏画布', chars=[])])])), encoding='utf-8')
        edl = self.work / 'edl.json'
        self.cli('auto_edl', tr, '-o', edl)
        self.assertEqual(json.loads(edl.read_text(encoding='utf-8'))['canvas'], dict(w=1920, h=1080, fps=30))
        # 小画布保持横屏，用左边的蓝条验证粗剪没有裁掉两侧。
        out = self.work / 'cut_result'
        self.cli('rough_cut', edl, '-t', tr, '--canvas', '640x360', '-o', out)
        self.cli('init_timeline', out)
        tl = json.loads((out / 'timeline.json').read_text(encoding='utf-8'))
        self.assertEqual(tl['canvas'], dict(w=640, h=360, fps=30))
        image = out / 'frame.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(out / 'aroll.mp4'), '-frames:v', '1', str(image)], check=True)
        r, _, b = Image.open(image).convert('RGB').getpixel((10, 180))
        self.assertGreater(b, r + 100)
        self.cli('init_timeline', out, '--canvas', '1080x1920')
        self.assertEqual(json.loads((out / 'timeline.json').read_text(encoding='utf-8'))['canvas']['w'], 1080)


if __name__ == '__main__':
    unittest.main()
