# -*- coding: utf-8 -*-
"""
实习僧（shixiseng）动态字体解密

原理
----
页面把数字和部分汉字替换成私有区字符（U+E000–U+F8FF），再用一个每次请求
都重新生成的 woff 字体去渲染。字体里的 cmap 把 0xE005 这类编码指向真正的
字形，而**字形名就是真实字符**：

    U+E137 -> 字形名 "uni34" -> "4"
    U+E02B -> 字形名 "uni4E94" -> "五"
    U+E243 -> 字形名 "uni70"  -> "p"

所以主路径是查表，不需要 OCR。只有当天字形名被改成 glyph001 这种无意义
名字时，才退到渲染 + ddddocr 识别。

用法
----
    dec = ShixisengDecoder.from_html(page_html)      # 自动从 HTML 里找字体
    dec = ShixisengDecoder.from_browser(tab)         # 从 DrissionPage 标签页找
    clean = dec.decode("&#xe6af;&#xe9a3;&#xf755;/天")  # -> "150/天"

单独自测（不启动浏览器，直接打站点）：
    python font_decoder.py --selftest
"""

import base64
import html as html_lib
import io
import os
import re
import tempfile

from fontTools.ttLib import TTFont


# --------------------------------------------------------------------------
# 一、从页面里找到字体
# --------------------------------------------------------------------------

# 形如：@font-face { font-family: myFont; src: url(/interns/iconfonts/file?rand=0.62); }
_RE_FONTFACE = re.compile(
    r"font-family\s*:\s*['\"]?myFont['\"]?\s*;[^}]{0,300}?url\(\s*['\"]?([^'\")]+)['\"]?\s*\)",
    re.S | re.I,
)


def extract_font_src(page_html):
    """从页面 HTML 里取出 myFont 的 src（可能是相对地址、绝对地址或 data:base64）。"""
    text = html_lib.unescape(page_html or "")
    m = _RE_FONTFACE.search(text)
    if not m:
        return None
    src = m.group(1).strip()
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("/"):
        return "https://www.shixiseng.com" + src
    return src


# --------------------------------------------------------------------------
# 二、把字体变成「假字 -> 真字」的字典
# --------------------------------------------------------------------------

def _glyph_name_to_char(name):
    """字形名 uni34 -> '4'；uni4E94 -> '五'；不是这种格式就返回 None。"""
    if not name or not name.startswith("uni"):
        return None
    hexpart = name[3:]
    if not hexpart or len(hexpart) > 6:
        return None
    try:
        code = int(hexpart, 16)
    except ValueError:
        return None
    if code < 0x20 or 0xE000 <= code <= 0xF8FF or code > 0x10FFFF:
        return None
    try:
        return chr(code)
    except ValueError:
        return None


def _pua_map_from_names(font):
    mapping = {}
    for code, gname in font.getBestCmap().items():
        if 0xE000 <= code <= 0xF8FF:
            real = _glyph_name_to_char(gname)
            if real:
                mapping[chr(code)] = real
    return mapping


def _render_glyph_png(font_bytes, char, size=64):
    """把字体里某个字符渲染成白底黑字的 PNG 字节，供 OCR 用。"""
    from PIL import Image, ImageDraw, ImageFont

    # PIL 只能读真实文件，先把字体落到临时文件；woff/woff2 先转成 ttf
    tmpdir = tempfile.mkdtemp(prefix="sxfont_")
    raw_path = os.path.join(tmpdir, "f.bin")
    with open(raw_path, "wb") as f:
        f.write(font_bytes)
    ttf_path = os.path.join(tmpdir, "f.ttf")
    ttf = TTFont(raw_path)
    if ttf.flavor in ("woff", "woff2"):
        ttf.flavor = None
    ttf.save(ttf_path)

    pil_font = ImageFont.truetype(ttf_path, size)
    img = Image.new("L", (size + 20, size + 20), 255)
    ImageDraw.Draw(img).text((10, 5), char, font=pil_font, fill=0)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _pua_map_from_ocr(font_bytes, font, log=print):
    """兜底：逐字渲染 + ddddocr 识别数字。只认 0-9，认不出的留空。"""
    try:
        import ddddocr
    except ImportError:
        log("⚠️ 未安装 ddddocr，无法走 OCR 兜底")
        return {}

    ocr = ddddocr.DdddOcr(show_ad=False)
    try:
        ocr.set_ranges("0123456789")
    except Exception:
        pass

    mapping = {}
    for code in font.getBestCmap():
        if not (0xE000 <= code <= 0xF8FF):
            continue
        try:
            png = _render_glyph_png(font_bytes, chr(code))
            res = (ocr.classification(png) or "").strip()
        except Exception:
            continue
        if len(res) == 1 and res.isdigit():
            mapping[chr(code)] = res
    return mapping


# --------------------------------------------------------------------------
# 三、对外入口
# --------------------------------------------------------------------------

class ShixisengDecoder:
    """拿到字体后，把页面文本里的私有区字符还原成真字符。"""

    def __init__(self, mapping, mode="glyphname"):
        self.mapping = mapping or {}
        self.mode = mode

    # ---- 构造 ----
    @classmethod
    def from_font_bytes(cls, font_bytes, allow_ocr=True, log=print):
        font = TTFont(io.BytesIO(font_bytes), lazy=True)
        mapping = _pua_map_from_names(font)
        mode = "glyphname"
        if len(mapping) < 20 and allow_ocr:
            log("⚠️ 字形名不可用（只解出 %d 个），改用 OCR 兜底" % len(mapping))
            mapping = _pua_map_from_ocr(font_bytes, font, log=log)
            mode = "ocr"
        return cls(mapping, mode)

    @classmethod
    def from_html(cls, page_html, log=print, **kw):
        src = extract_font_src(page_html)
        if not src:
            log("⚠️ 页面里没找到 myFont 的 @font-face")
            return cls({}, "empty")
        return cls.from_font_bytes(fetch_font(src), log=log, **kw)

    @classmethod
    def from_browser(cls, tab, log=print, **kw):
        """在 DrissionPage 标签页里构造；优先读 DOM 里的样式，取不到再用页面内 fetch。"""
        page_html = tab.html
        src = extract_font_src(page_html)
        if not src:
            log("⚠️ DOM 里没找到 myFont 的 @font-face")
            return cls({}, "empty")
        if src.startswith("data:"):
            return cls.from_font_bytes(_b64_from_data_uri(src), log=log, **kw)
        try:
            # DrissionPage 4.x：tab.cookies() 返回 Cookies 对象，要再调 .as_dict()
            try:
                cookies = tab.cookies().as_dict()
            except Exception:
                cookies = None
            data = fetch_font(src, cookies=cookies)
        except Exception:
            data = _fetch_font_in_browser(tab, src)
        return cls.from_font_bytes(data, log=log, **kw)

    # ---- 使用 ----
    def decode(self, text):
        if not text or not self.mapping:
            return text
        return "".join(self.mapping.get(ch, ch) for ch in text)

    def __len__(self):
        return len(self.mapping)


# --------------------------------------------------------------------------
# 四、下载字体
# --------------------------------------------------------------------------

def _b64_from_data_uri(uri):
    head, _, payload = uri.partition(",")
    if "base64" in head:
        return base64.b64decode(payload)
    from urllib.parse import unquote_to_bytes
    return unquote_to_bytes(payload)


def fetch_font(url, cookies=None, user_agent=None, timeout=15):
    """用 requests 直接下载字体；trust_env=False 是为了绕开系统代理。"""
    if url.startswith("data:"):
        return _b64_from_data_uri(url)
    import requests
    ua = user_agent or ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    s = requests.Session()
    s.trust_env = False
    headers = {"User-Agent": ua, "Referer": "https://www.shixiseng.com/"}
    r = s.get(url, headers=headers, cookies=cookies or {}, timeout=timeout)
    r.raise_for_status()
    return r.content


def _fetch_font_in_browser(tab, url):
    """最后手段：在页面里用同步 XHR 取字体，再用 btoa 转回来。

    写成 IIFE 单表达式，配 as_expr=True —— DrissionPage 的 run_js 对
    多语句脚本的返回值处理不一致，包成表达式最稳。
    """
    import json
    js = ("(function(){var x=new XMLHttpRequest();"
          "x.open('GET',%s,false);"
          "x.overrideMimeType('text/plain; charset=x-user-defined');"
          "x.send(null);"
          "var t=x.responseText,s='';"
          "for(var i=0;i<t.length;i++){s+=String.fromCharCode(t.charCodeAt(i)&0xff);}"
          "return btoa(s);})()" % json.dumps(url))
    b64 = tab.run_js(js, as_expr=True)
    if not b64:
        raise RuntimeError("页面内取字体失败：%s" % url)
    return base64.b64decode(b64)


# --------------------------------------------------------------------------
# 五、自测：直接打一次实习僧列表页，验证解密链路
# --------------------------------------------------------------------------

def _selftest():
    import requests

    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    s = requests.Session()
    s.trust_env = False
    url = ("https://www.shixiseng.com/interns?keyword=Python"
           "&city=%E5%85%A8%E5%9B%BD&type=intern&page=1")
    r = s.get(url, headers={"User-Agent": ua}, timeout=20)
    page = html_lib.unescape(r.text)
    print("页面 %d 字节，PUA 字符 %d 个" %
          (len(page), sum(1 for c in page if 0xE000 <= ord(c) <= 0xF8FF)))

    dec = ShixisengDecoder.from_html(r.text)
    print("字典 %d 条，模式 %s" % (len(dec), dec.mode))

    titles = re.findall(r'class="title ellipsis font"[^>]*>(.*?)</a>', page, re.S)
    days = re.findall(r'class="day font"[^>]*>(.*?)</span>', page, re.S)
    print("-" * 56)
    for t, d in list(zip(titles, days))[:5]:
        print("标题:", dec.decode(t.strip()))
        print("薪资:", dec.decode(d.strip()))
    return dec


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
