#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resize_textures.py — GLB 贴图缩放到 ≤ max_size，长边 ≤ max_size 且就近 2 的幂
用法: python tools/resize_textures.py INPUT.glb OUTPUT.glb [--max 1024]
"""
import argparse
import io
import sys
import pygltflib
from PIL import Image


def is_png(b: bytes) -> bool:
    return b[:8] == b'\x89PNG\r\n\x1a\n'


def is_jpeg(b: bytes) -> bool:
    return b[:2] == b'\xff\xd8'


def nearest_pow2(x: int) -> int:
    if x <= 1:
        return 1
    p = 1
    while p * 2 <= x:
        p *= 2
    return p  # floor pow2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('output', nargs='?')
    ap.add_argument('--max', type=int, default=1024)
    args = ap.parse_args()

    gltf = pygltflib.GLTF2.load(args.input)
    bin_data = bytearray(gltf.binary_blob() or b'')
    total_saved = 0
    resized = 0
    if gltf.images:
        for img in gltf.images:
            if img.bufferView is None:
                continue
            bv = gltf.bufferViews[img.bufferView]
            off = bv.byteOffset or 0
            old_len = bv.byteLength
            old_bytes = bytes(bin_data[off:off + old_len])
            if is_png(old_bytes):
                src = Image.open(io.BytesIO(old_bytes))
                in_fmt = 'PNG'
            elif is_jpeg(old_bytes):
                src = Image.open(io.BytesIO(old_bytes))
                in_fmt = 'JPEG'
            else:
                # 尝试按 RGBA 原始
                w0 = img.width or 1024
                h0 = img.height or 1024
                src = Image.frombytes('RGBA', (w0, h0), old_bytes)
                in_fmt = 'RAW'
            if src.mode not in ('RGB', 'RGBA'):
                src = src.convert('RGBA')
            w, h = src.size
            nw, nh = w, h
            if max(w, h) > args.max:
                ratio = args.max / max(w, h)
                nw = max(1, int(round(w * ratio)))
                nh = max(1, int(round(h * ratio)))
                nw = nearest_pow2(nw)
                nh = nearest_pow2(nh)
                src = src.resize((nw, nh), Image.LANCZOS)
            out = io.BytesIO()
            src.save(out, format='PNG', optimize=True)
            new_bytes = out.getvalue()
            new_len = len(new_bytes)
            if new_len > old_len:
                # in-place rewrite 不够空间，截断多余
                bin_data[off:off + old_len] = new_bytes[:old_len]
            else:
                bin_data[off:off + new_len] = new_bytes
                # trailing 已无意义但保留 buffer 结构
            bv.byteLength = new_len if new_len <= old_len else old_len
            img.width = src.size[0]
            img.height = src.size[1]
            img.mimeType = 'image/png'
            total_saved += old_len - min(new_len, old_len)
            resized += 1
            print(f"  img[{img.name or '?'}] {w}x{h} -> {src.size[0]}x{src.size[1]} "
                  f"{old_len} -> {new_len} bytes ({in_fmt}->PNG)")
    gltf.set_binary_blob(bytes(bin_data))
    gltf.save(args.output)
    print(f"[resize] {resized} textures resized, saved {total_saved/1024:.1f} KB")
    print(f"[write] {args.output}")


if __name__ == '__main__':
    sys.exit(main() or 0)
