#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片批量转换为AVIF格式工具
支持多线程处理，遍历所有子目录
"""

import os
import sys
import time
import subprocess
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

# 支持的图片格式
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp'}

class ImageConverter:
    def __init__(self, root_dir: str, max_workers: int = 8, force_lossless: bool = False):
        self.root_dir = Path(root_dir)
        self.max_workers = max_workers
        self.force_lossless = force_lossless  # 是否强制全部无损
        self.converted_files: List[Tuple[Path, Path]] = []
        self.failed_files: List[Tuple[Path, str]] = []
        
        # 检查 avifenc 是否可用
        if not shutil.which('avifenc'):
            print("错误: 未找到 avifenc 命令")
            sys.exit(1)
        
    def find_images(self) -> List[Path]:
        """遍历目录查找所有支持的图片文件"""
        images = []
        for root, dirs, files in os.walk(self.root_dir):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in SUPPORTED_FORMATS:
                    images.append(file_path)
        return images
    
    def convert_image(self, image_path: Path) -> Tuple[bool, Path, Path, str]:
        """
        使用 avifenc 转换单个图片为AVIF格式
        返回: (成功标志, 原始路径, 新路径, 错误信息)
        """
        try:
            # 生成输出文件路径
            output_path = image_path.with_suffix('.avif')
            
            # 如果目标文件已存在，跳过
            if output_path.exists():
                return False, image_path, output_path, "目标文件已存在"
            
            # 根据设置选择编码模式
            if self.force_lossless:
                # 强制无损模式：所有格式都使用无损编码
                cmd = [
                    'avifenc',
                    '--lossless',
                    '--speed', '6',
                    '--jobs', '1',
                    str(image_path),
                    str(output_path)
                ]
            else:
                # 智能模式：根据源文件格式选择
                # JPG/WebP: 已经是有损格式，使用有损模式（高质量）
                # PNG/BMP/TIFF: 无损格式，使用无损模式
                ext = image_path.suffix.lower()
                is_lossy_source = ext in {'.jpg', '.jpeg', '.webp'}
                
                if is_lossy_source:
                    # 有损模式：适合JPG等已经有损的格式
                    # --min 0 --max 63: 质量范围（接近无损）
                    # -y 444: 色度子采样（最高质量）
                    cmd = [
                        'avifenc',
                        '--min', '0',
                        '--max', '63',
                        '-y', '444',
                        '--speed', '6',
                        '--jobs', '1',
                        str(image_path),
                        str(output_path)
                    ]
                else:
                    # 无损模式：适合PNG等无损格式
                    cmd = [
                        'avifenc',
                        '--lossless',
                        '--speed', '6',
                        '--jobs', '1',
                        str(image_path),
                        str(output_path)
                    ]
            
            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                return True, image_path, output_path, ""
            else:
                error_msg = result.stderr.strip() or "转换失败"
                return False, image_path, None, error_msg
        
        except subprocess.TimeoutExpired:
            return False, image_path, None, "转换超时"
        except Exception as e:
            return False, image_path, None, str(e)
    
    def convert_all(self):
        """使用多线程转换所有图片"""
        images = self.find_images()
        
        if not images:
            print("未找到任何支持的图片文件")
            return
        
        print(f"找到 {len(images)} 个图片文件")
        print(f"使用 {self.max_workers} 个线程进行转换...")
        print("JPG/WebP: 高质量有损模式 | PNG/BMP/TIFF: 无损模式\n")
        
        # 使用线程池处理
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.convert_image, img): img for img in images}
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                success, original, new_path, error = future.result()
                
                # 计算进度和预估时间
                elapsed = time.time() - start_time
                avg_time = elapsed / completed
                remaining = (len(images) - completed) * avg_time
                
                if success:
                    self.converted_files.append((original, new_path))
                    # 显示文件大小对比
                    original_size = original.stat().st_size / 1024 / 1024
                    new_size = new_path.stat().st_size / 1024 / 1024
                    ratio = (new_size / original_size * 100) if original_size > 0 else 0
                    print(f"[{completed}/{len(images)}] ✓ {original.name} ({original_size:.2f}MB -> {new_size:.2f}MB, {ratio:.1f}%) | 剩余约 {int(remaining)}秒")
                else:
                    self.failed_files.append((original, error))
                    if error != "目标文件已存在":
                        print(f"[{completed}/{len(images)}] ✗ {original.name} - 失败: {error}")
                    else:
                        print(f"[{completed}/{len(images)}] - {original.name} - 跳过: {error}")
        
        # 显示统计信息
        total_time = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"转换完成! 总耗时: {int(total_time)}秒 ({total_time/60:.1f}分钟)")
        print(f"成功: {len(self.converted_files)} 个文件")
        print(f"失败/跳过: {len(self.failed_files)} 个文件")
        if self.converted_files:
            print(f"平均速度: {total_time/len(self.converted_files):.2f}秒/张")
            
            # 计算总体压缩率
            total_original = sum(f[0].stat().st_size for f in self.converted_files)
            total_new = sum(f[1].stat().st_size for f in self.converted_files)
            ratio = (total_new / total_original * 100) if total_original > 0 else 0
            print(f"总体大小: {total_original/1024/1024:.2f}MB -> {total_new/1024/1024:.2f}MB ({ratio:.1f}%)")
        print(f"{'='*60}\n")
    
    def delete_originals(self):
        """删除原始文件"""
        if not self.converted_files:
            print("没有需要删除的文件")
            return
        
        print(f"\n准备删除 {len(self.converted_files)} 个原始文件...")
        deleted = 0
        failed = 0
        
        for original, _ in self.converted_files:
            try:
                original.unlink()
                deleted += 1
                print(f"✓ 已删除: {original}")
            except Exception as e:
                failed += 1
                print(f"✗ 删除失败: {original} - {e}")
        
        print(f"\n删除完成: 成功 {deleted} 个, 失败 {failed} 个")


def main():
    print("="*60)
    print("图片批量转换为AVIF格式工具")
    print("智能选择编码模式：JPG有损 | PNG无损")
    print("="*60)
    
    # 获取目标目录
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = input("\n请输入目标目录路径 (留空使用当前目录): ").strip()
        if not target_dir:
            target_dir = "."
    
    # 验证目录
    if not os.path.isdir(target_dir):
        print(f"错误: 目录不存在 - {target_dir}")
        sys.exit(1)
    
    # 获取线程数
    try:
        max_workers = int(input("请输入线程数 (留空使用默认值8): ").strip() or "8")
        if max_workers < 1:
            max_workers = 8
    except ValueError:
        max_workers = 8
    
    print()
    
    # 创建转换器并执行转换
    converter = ImageConverter(target_dir, max_workers)
    converter.convert_all()
    
    # 询问是否删除原始文件
    if converter.converted_files:
        while True:
            response = input("\n是否删除原始文件? (y/n): ").strip().lower()
            if response in ('y', 'yes', '是'):
                converter.delete_originals()
                break
            elif response in ('n', 'no', '否'):
                print("保留原始文件")
                break
            else:
                print("请输入 y 或 n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(0)
